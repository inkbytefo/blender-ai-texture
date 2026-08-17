# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
AI generation operatörü.

UV seçimi maskesi, inpaint/fill, önbellek (cache), referans görsel
ve asenkron threading mekanizmalarını yönetir.
"""

from typing import List, Optional
import threading
import numpy as np
import bpy

from ..blender.image_adapter import BlenderImageAdapter
from ..blender.selection_group import SelectionGroupResolver
from ..texture.mask import MaskProcessor
from ..texture.composite import TextureCompositor
from ..texture.resolution import ResolutionManager
from ..texture.image_manager import ImageManager
from ..texture.island_packer import IslandPacker
from ..ai.registry import get_active_provider
from ..ai.request import AIRequest
from ..ai.response import AIResponse
from ..ai.capabilities import AIOperation
from ..ai.cache import GenerationCache
from ..core.state import get_state_manager, StateStatus
from ..core.logging import get_logger

logger = get_logger("operators.generate")


class AITEXTURE_OT_generate(bpy.types.Operator):
    """AI ile texture generation veya inpaint/fill işlemini başlatır."""

    bl_idname = "ai_texture.generate"
    bl_label = "AI Generate"
    bl_description = "Seçili yüzeyler, prompt ve maske kullanarak AI ile doku üret, doldur veya sil"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        state = get_state_manager().state
        if state.status == StateStatus.GENERATING:
            return False
        return BlenderImageAdapter.get_active_image(context) is not None

    def execute(self, context: bpy.types.Context):
        props = context.scene.ai_texture
        base_image = BlenderImageAdapter.get_active_image(context)

        if not base_image:
            self.report({'ERROR'}, "İşlem yapılacak aktif bir texture bulunamadı!")
            return {'CANCELLED'}

        # 1. Aktif AI Provider'ı al
        provider = get_active_provider()

        # 2. Orijinal görseli NumPy olarak oku ve yedekle
        original_pixels = ImageManager.backup_original(base_image)
        h, w = original_pixels.shape[:2]

        # 3. Operasyon türünü eşle
        op_map = {
            'FILL': AIOperation.FILL,
            'REMOVE': AIOperation.REMOVE,
            'GENERATE': AIOperation.GENERATE,
        }
        operation = op_map.get(props.operation, AIOperation.FILL)

        # 4. 3D Selection Group ve UV Island Analizi
        active_obj = getattr(context, "active_object", None)
        selection_group = None
        packing_manifest = None
        is_packed_mode = False

        if active_obj and active_obj.type == 'MESH':
            selection_group = SelectionGroupResolver.resolve_from_mesh(active_obj)

        pad_val = getattr(props, "context_padding", 32) if operation != AIOperation.GENERATE else 0

        # Eğer birden fazla UV adacığı varsa veya 3D seçim mevcutsa Island Packing kullan
        if selection_group and selection_group.island_count > 1:
            is_packed_mode = True
            mask_desc = f"3D Selection Group ({selection_group.island_count} UV Islands, {selection_group.total_faces} Faces)"
            req_w, req_h = ResolutionManager.find_best_generation_size(1024, 1024)
            source_scaled, mask_scaled, packing_manifest = IslandPacker.pack_islands(
                base_image=original_pixels,
                islands=selection_group.islands,
                target_canvas_size=(req_w, req_h),
                padding=pad_val,
                bleed_pixels=2,
            )
            mask = None  # Packed mode handles masking per island
            cropped_original = source_scaled
            cropped_mask = mask_scaled
            crop_w, crop_h = req_w, req_h
            bbox = (0, 0, w, h)
        else:
            # 4b. Klasik Akıllı Maske (UV Selection > Custom Mask > Full)
            mask, mask_desc = MaskProcessor.get_mask_from_context(context, base_image)

            if mask is None:
                if operation in {AIOperation.FILL, AIOperation.REMOVE}:
                    self.report(
                        {'WARNING'},
                        "Fill/Remove için lütfen Edit Mode'da bir yüzey seçin veya bir maske çizin!"
                    )
                    # Yedek merkez maske
                    logger.info("No selection found, generating fallback center circular mask")
                    y_grid, x_grid = np.ogrid[:h, :w]
                    cy, cx = h / 2, w / 2
                    radius = min(h, w) / 4
                    mask = ((x_grid - cx) ** 2 + (y_grid - cy) ** 2 <= radius ** 2).astype(np.float32)
                else:
                    mask = np.ones((h, w), dtype=np.float32)

            # Maskeli alanın bounding box'ını bul ve kırp (Photoshop Context Padding)
            bbox = ResolutionManager.get_mask_bounding_box(mask, padding=pad_val)
            cropped_original = ResolutionManager.crop_region(original_pixels, bbox)
            cropped_mask = ResolutionManager.crop_region(mask, bbox)
            crop_h, crop_w = cropped_original.shape[:2]

            if crop_h <= 0 or crop_w <= 0:
                cropped_original = original_pixels.copy()
                cropped_mask = mask.copy()
                crop_h, crop_w = h, w
                bbox = (0, 0, w, h)

            req_w, req_h = ResolutionManager.find_best_generation_size(crop_w, crop_h)
            source_scaled = ResolutionManager.resize_image(cropped_original, req_w, req_h)
            mask_scaled = ResolutionManager.resize_image(cropped_mask, req_w, req_h)

        # 5. Prompt optimizasyonu (Fill/Remove için boş bırakıldıysa otomatik tanımla)
        prompt_text = props.prompt.strip()
        if not prompt_text:
            if operation == AIOperation.REMOVE:
                prompt_text = "seamless clean texture background fill, remove foreground detail, blend naturally"
            elif operation == AIOperation.FILL:
                prompt_text = "seamless detailed texture fill, matching surrounding surface material"
            elif operation == AIOperation.GENERATE:
                self.report({'WARNING'}, "Lütfen ne üretmek istediğinizi Prompt alanına yazın!")
                return {'CANCELLED'}

        # 6. Referans Görsel
        ref_images = []
        if props.reference_image:
            ref_arr = BlenderImageAdapter.image_to_numpy(props.reference_image)
            ref_images.append(ref_arr)

        # 7. AI İstek (AIRequest) nesnesi oluştur
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
            selection_context=selection_group.name if selection_group else "",
            island_count=selection_group.island_count if selection_group else 0,
        )

        errors = request.validate()
        if errors:
            self.report({'WARNING'}, "; ".join(errors))
            return {'CANCELLED'}

        state_mgr = get_state_manager()
        req_hash = request.to_hash()
        base_img_name = base_image.name
        feather_rad = props.feather_radius

        def _apply_response(response: AIResponse):
            """Dönen yanıtı ana iş parçacığında composite edip önizlemeye açar."""
            target_image = bpy.data.images.get(base_img_name)
            if not target_image:
                state_mgr.set_error("Hedef görsel kayboldu!", "IMAGE_LOST")
                return

            composited_variations: List[np.ndarray] = []
            for gen_img in response.images:
                if is_packed_mode and packing_manifest:
                    # 1a. Paketlenmiş AI tuvalinden her UV adacığını tersine dönüştürerek yerleştir
                    comp = IslandPacker.unpack_and_composite(
                        packed_generated=gen_img,
                        manifest=packing_manifest,
                        original_base=original_pixels,
                        feather_radius=feather_rad,
                    )
                else:
                    # 1b. Klasik kırpılmış bölge kompozitleme
                    gen_cropped = ResolutionManager.resize_image(gen_img, crop_w, crop_h)
                    comp_cropped = TextureCompositor.composite_with_feather(
                        original=cropped_original,
                        generated=gen_cropped,
                        mask=cropped_mask,
                        feather_radius=feather_rad,
                    )
                    comp = ResolutionManager.place_region(original_pixels, comp_cropped, bbox)

                composited_variations.append(comp)

            state_mgr.update(
                variations=composited_variations,
                selected_variation=0,
            )
            state_mgr.finish_generation()


            preview_img = ImageManager.create_or_update_preview(target_image, composited_variations[0])

            for window in getattr(getattr(bpy.context, "window_manager", None), "windows", []):
                for area in getattr(window.screen, "areas", []):
                    if area.type == 'IMAGE_EDITOR' and area.spaces.active:
                        area.spaces.active.image = preview_img

            from ..blender.material_adapter import BlenderMaterialAdapter
            BlenderMaterialAdapter.force_viewport_redraw()

            logger.info("Texture generation preview ready", mask_type=mask_desc)

        # 9. Önbellek Denetimi (Cache Check)
        cached_resp = GenerationCache.get(req_hash)
        if cached_resp is not None:
            logger.info("Loaded from cache, applying immediately", mask_type=mask_desc)
            state_mgr.start_generation(prompt=request.prompt, operation=props.operation, provider="Cache")
            _apply_response(cached_resp)
            self.report({'INFO'}, f"Önizleme önbellekten anında yüklendi! [{mask_desc}]")
            return {'FINISHED'}

        # 10. Asenkron Worker ve Timer Callback
        state_mgr.start_generation(
            prompt=request.prompt,
            operation=props.operation,
            provider=provider.display_name,
        )
        state_mgr.update(progress=0.1, progress_message=f"{provider.display_name} ile iletişim kuruluyor... ({mask_desc})")

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
            # Kullanıcı iptal ettiyse timer'ı derhal durdur
            if state_mgr.is_aborted():
                logger.info("Timer callback detected abort signal, terminating generation loop")
                return None

            wm = getattr(bpy.context, "window_manager", None)
            if not bg_result["done"]:
                cur_prog = state_mgr.state.progress
                if cur_prog < 0.85:
                    new_prog = min(0.85, cur_prog + 0.1)
                    state_mgr.update(progress=new_prog, progress_message=f"AI üretimi sürüyor... (%{int(new_prog * 100)})")
                    if wm:
                        wm.ai_texture_progress = new_prog
                if wm:
                    for window in getattr(wm, "windows", []):
                        for area in getattr(window.screen, "areas", []):
                            area.tag_redraw()
                return 0.25

            if wm:
                wm.ai_texture_progress = 1.0

            if state_mgr.is_aborted():
                return None

            if bg_result["error"]:
                state_mgr.set_error(bg_result["error"], "ASYNC_ERROR")
                logger.error("Async worker failed", error=bg_result["error"])
                return None

            response: AIResponse = bg_result["response"]
            if not response or not response.success or not response.images:
                err_msg = response.error_message if response else "AI yanıt döndürmedi."
                state_mgr.set_error(err_msg, response.error_code if response else "EMPTY_RESPONSE")
                return None

            _apply_response(response)
            return None

        bpy.app.timers.register(_timer_callback, first_interval=0.1)

        self.report({'INFO'}, f"AI isteği başlatıldı [{mask_desc}] -> {provider.display_name}")
        return {'FINISHED'}
