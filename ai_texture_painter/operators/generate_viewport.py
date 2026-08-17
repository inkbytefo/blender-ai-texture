# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Paint from Viewport Operator.

3D Viewport'tan ekran görüntüsü ve seçili yüzey maskesini yakalar,
AI modeline bağlam-duyarlı (Photoshop generative fill benzeri) istek gönderir
ve üretilen 2D perspektifli çıktıyı doğrudan 3D modelin UV dokusuna geri projekte eder.
"""

from typing import Optional, List
import threading
import numpy as np
import bpy

from ..blender.image_adapter import BlenderImageAdapter
from ..blender.viewport_adapter import BlenderViewportAdapter
from ..blender.projection_baker import ProjectionBaker
from ..texture.image_manager import ImageManager
from ..texture.resolution import ResolutionManager
from ..ai.registry import get_active_provider
from ..ai.request import AIRequest
from ..ai.response import AIResponse
from ..ai.capabilities import AIOperation
from ..ai.cache import GenerationCache
from ..core.state import get_state_manager, StateStatus
from ..core.logging import get_logger

logger = get_logger("operators.generate_viewport")


class AITEXTURE_OT_align_view(bpy.types.Operator):
    """3D Görünüm açısını standart ortografik eksenlere (Ön, Sağ, Üst vb.) hizalar."""

    bl_idname = "ai_texture.align_view"
    bl_label = "Align View"
    bl_description = "3D Viewport açısını belirtilen yöne kilitle"
    bl_options = {'REGISTER', 'UNDO'}

    view_direction: bpy.props.EnumProperty(
        name="Direction",
        items=[
            ('RIGHT', "Right", "Sağdan Bak (3)"),
            ('LEFT', "Left", "Soldan Bak (Ctrl+3)"),
            ('FRONT', "Front", "Önden Bak (1)"),
            ('BACK', "Back", "Arkadan Bak (Ctrl+1)"),
            ('TOP', "Top", "Üstten Bak (7)"),
            ('BOTTOM', "Bottom", "Alttan Bak (Ctrl+7)"),
            ('CAMERA', "Camera", "Kamera Açısı (0)"),
        ],
        default='RIGHT',
    )

    def execute(self, context: bpy.types.Context):
        area, region, _ = BlenderViewportAdapter.get_3d_viewport_region(context)
        if not area:
            self.report({'WARNING'}, "3D Viewport bulunamadı!")
            return {'CANCELLED'}

        with context.temp_override(area=area, region=region):
            if self.view_direction == 'CAMERA':
                bpy.ops.view3d.view_camera()
            else:
                bpy.ops.view3d.view_axis(type=self.view_direction)

        return {'FINISHED'}


class AITEXTURE_OT_paint_from_view(bpy.types.Operator):
    """3D Viewport açısından AI ile yüzey boyama ve UV projeksiyonu yapar."""

    bl_idname = "ai_texture.paint_from_view"
    bl_label = "Paint from Viewport"
    bl_description = "3D Viewport'taki mevcut açıdan AI ile doku üret ve modele projekte et"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        state = get_state_manager().state
        if state.status == StateStatus.GENERATING:
            return False
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            return False
        return BlenderImageAdapter.get_active_image(context) is not None

    def execute(self, context: bpy.types.Context):
        props = context.scene.ai_texture
        obj = context.active_object
        base_image = BlenderImageAdapter.get_active_image(context)

        if not base_image or not obj:
            self.report({'ERROR'}, "Aktif bir 3D Mesh nesnesi ve texture bulunamadı!")
            return {'CANCELLED'}

        # 1. 3D Viewport Ekran Görüntüsünü Al
        viewport_img = BlenderViewportAdapter.capture_viewport_image(context)
        if viewport_img is None:
            self.report({'ERROR'}, "3D Viewport görüntüsü yakalanamadı!")
            return {'CANCELLED'}

        vh, vw = viewport_img.shape[:2]

        # 2. Seçili Yüzeylerin Ekran Maskesini Çıkar
        screen_mask, face_cnt = BlenderViewportAdapter.capture_screen_selection_mask(
            context, obj, width=vw, height=vh, cull_backfaces=True
        )

        mask_desc = f"3D Viewport ({face_cnt} Yüzey)" if face_cnt > 0 else "3D Viewport (Tüm Model)"

        # 3. Orijinal Dokuyu Yedekle
        original_pixels = ImageManager.backup_original(base_image)

        # 4. Operasyon ve Prompt
        op_map = {
            'FILL': AIOperation.FILL,
            'REMOVE': AIOperation.REMOVE,
            'GENERATE': AIOperation.GENERATE,
        }
        operation = op_map.get(props.operation, AIOperation.FILL)

        prompt_text = props.prompt.strip()
        if not prompt_text:
            if operation == AIOperation.REMOVE:
                prompt_text = "seamless clean surface texture, remove detail, blend naturally with surroundings"
            elif operation == AIOperation.FILL:
                prompt_text = "detailed realistic surface material, matching lighting and perspective of the 3D model"
            else:
                self.report({'WARNING'}, "Lütfen ne üretmek istediğinizi Prompt alanına yazın!")
                return {'CANCELLED'}

        # 5. Maskeli Alanı 1:1 Kare Olarak Kırp (Distorsiyonsuz En-Boy Oranı)
        raw_bbox = ResolutionManager.get_mask_bounding_box(screen_mask, padding=32)
        bbox = ResolutionManager.get_square_bounding_box(raw_bbox, vw, vh)
        cropped_viewport = ResolutionManager.crop_region(viewport_img, bbox)
        cropped_mask = ResolutionManager.crop_region(screen_mask, bbox)
        crop_h, crop_w = cropped_viewport.shape[:2]

        if crop_h <= 0 or crop_w <= 0:
            cropped_viewport = viewport_img.copy()
            cropped_mask = screen_mask.copy()
            crop_h, crop_w = vh, vw
            bbox = (0, 0, vw, vh)

        # 6. AI İstek Boyutuna Ölçekle (Kare 1024x1024 / 512x512)
        req_w, req_h = ResolutionManager.find_best_generation_size(crop_w, crop_h)
        source_scaled = ResolutionManager.resize_image(cropped_viewport, req_w, req_h)
        mask_scaled = ResolutionManager.resize_image(cropped_mask, req_w, req_h)

        ref_images = []
        if props.reference_image:
            ref_arr = BlenderImageAdapter.image_to_numpy(props.reference_image)
            ref_images.append(ref_arr)

        request = AIRequest(
            operation=operation,
            prompt=prompt_text,
            negative_prompt=props.negative_prompt.strip(),
            width=req_w,
            height=req_h,
            source_image=source_scaled,
            mask=mask_scaled,
            reference_images=ref_images,
            seed=props.seed if not props.random_seed else -1,
            variation_count=props.variation_count,
            strength=props.strength,
        )

        errors = request.validate()
        if errors:
            self.report({'WARNING'}, "; ".join(errors))
            return {'CANCELLED'}

        provider = get_active_provider()
        state_mgr = get_state_manager()
        req_hash = request.to_hash()
        base_img_name = base_image.name
        feather_rad = props.feather_radius

        def _apply_response(response: AIResponse):
            """AI çıktısını 3D modelin UV dokusuna projekte edip önizlemeye açar."""
            target_image = bpy.data.images.get(base_img_name)
            target_obj = bpy.data.objects.get(obj.name)
            if not target_image or not target_obj:
                state_mgr.set_error("Hedef görsel veya nesne kayboldu!", "TARGET_LOST")
                return

            composited_variations: List[np.ndarray] = []
            for gen_img in response.images:
                # Doğrudan AI çıktısının tam çözünürlüğünü ve kare bounding box'ını kullanarak UV'ye projekte et
                baked_tex, _ = ProjectionBaker.project_view_to_uv(
                    context=context,
                    obj=target_obj,
                    generated_viewport_img=gen_img,
                    screen_mask=screen_mask,
                    screen_bbox=bbox,
                    original_texture=original_pixels,
                    feather_radius=feather_rad,
                )
                composited_variations.append(baked_tex)

            state_mgr.update(
                variations=composited_variations,
                selected_variation=0,
            )
            state_mgr.finish_generation()

            preview_img = ImageManager.create_or_update_preview(target_image, composited_variations[0])

            # 3D Viewport ve Image Editor alanlarını tazele
            for window in getattr(getattr(bpy.context, "window_manager", None), "windows", []):
                for area in getattr(window.screen, "areas", []):
                    if area.type == 'IMAGE_EDITOR' and area.spaces.active:
                        area.spaces.active.image = preview_img

            from ..blender.material_adapter import BlenderMaterialAdapter
            BlenderMaterialAdapter.force_viewport_redraw()

            logger.info("3D Paint from View preview ready", provider=provider.display_name)

        # 7. Önbellek Kontrolü
        cached_resp = GenerationCache.get(req_hash)
        if cached_resp is not None:
            logger.info("Loaded 3D Viewport generation from cache")
            state_mgr.start_generation(prompt=request.prompt, operation=props.operation, provider="Cache")
            _apply_response(cached_resp)
            self.report({'INFO'}, f"3D Önizleme önbellekten yüklendi! [{mask_desc}]")
            return {'FINISHED'}

        # 8. Asenkron İşçi
        state_mgr.start_generation(
            prompt=request.prompt,
            operation=props.operation,
            provider=provider.display_name,
        )
        state_mgr.update(progress=0.1, progress_message=f"{provider.display_name} ile 3D boyama yapılıyor... ({mask_desc})")

        bg_result: dict = {"response": None, "done": False, "error": None}

        def _bg_worker():
            try:
                resp = provider.generate(request)
                if resp and resp.success:
                    GenerationCache.put(req_hash, resp)
                bg_result["response"] = resp
            except Exception as ex:
                bg_result["error"] = str(ex)
            finally:
                bg_result["done"] = True

        thread = threading.Thread(target=_bg_worker, daemon=True)
        thread.start()

        def _timer_callback() -> Optional[float]:
            wm = getattr(bpy.context, "window_manager", None)
            if not bg_result["done"]:
                cur_prog = state_mgr.state.progress
                if cur_prog < 0.85:
                    new_prog = min(0.85, cur_prog + 0.1)
                    state_mgr.update(progress=new_prog, progress_message=f"3D AI üretimi sürüyor... (%{int(new_prog * 100)})")
                    if wm:
                        wm.ai_texture_progress = new_prog
                for area in bpy.context.screen.areas if bpy.context.screen else []:
                    area.tag_redraw()
                return 0.25

            if wm:
                wm.ai_texture_progress = 1.0

            if bg_result["error"]:
                state_mgr.set_error(bg_result["error"], "ASYNC_ERROR")
                logger.error("Async worker failed in 3D paint", error=bg_result["error"])
                return None

            response: AIResponse = bg_result["response"]
            if not response or not response.success or not response.images:
                err_msg = response.error_message if response else "AI yanıt döndürmedi."
                state_mgr.set_error(err_msg, response.error_code if response else "EMPTY_RESPONSE")
                return None

            _apply_response(response)
            return None

        bpy.app.timers.register(_timer_callback, first_interval=0.1)

        self.report({'INFO'}, f"3D Viewport AI isteği başlatıldı -> {provider.display_name}")
        return {'FINISHED'}
