# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Apply Operator.

Önizleme (preview) aşamasındaki üretilmiş dokuyu kalıcı olarak
ana dokuya uygular, önceki durumu History yığınına kaydeder ve temizlik yapar.
"""

import bpy

from ..blender.image_adapter import BlenderImageAdapter
from ..texture.image_manager import ImageManager
from ..texture.history import get_history_manager
from ..core.state import get_state_manager, StateStatus
from ..core.logging import get_logger

logger = get_logger("operators.apply")


class AITEXTURE_OT_apply(bpy.types.Operator):
    """Üretilen önizleme sonucunu kalıcı olarak texture'a uygular."""

    bl_idname = "ai_texture.apply"
    bl_label = "Apply AI Texture"
    bl_description = "Önizleme sonucunu kalıcı olarak dokuya uygula"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        state = get_state_manager().state
        return state.status == StateStatus.PREVIEW

    def execute(self, context: bpy.types.Context):
        state = get_state_manager().state

        # 1. Asıl orijinal görseli bul
        base_image = None
        if state.active_image_name:
            base_image = bpy.data.images.get(state.active_image_name)

        if not base_image:
            current_img = BlenderImageAdapter.get_active_image(context)
            if current_img:
                if current_img.name.startswith(ImageManager.PREVIEW_PREFIX):
                    real_name = current_img.name[len(ImageManager.PREVIEW_PREFIX):]
                    base_image = bpy.data.images.get(real_name)
                else:
                    base_image = current_img

        if not base_image:
            self.report({'ERROR'}, "Aktif hedef texture bulunamadı!")
            return {'CANCELLED'}

        # Preview imajından pikselleri oku
        preview_img = bpy.data.images.get(state.preview_image_name)
        if not preview_img:
            self.report({'ERROR'}, "Önizleme imajı bulunamadı!")
            return {'CANCELLED'}

        preview_pixels = BlenderImageAdapter.image_to_numpy(preview_img)

        # 2. HistoryManager yığınına kaydet:
        # Eğer geçmiş boşsa önce orijinal temel durumu kaydet, ardından yeni uygulanan durumu kaydet.
        hist_mgr = get_history_manager()
        if hist_mgr.count == 0 and state.original_pixels is not None:
            hist_mgr.push(
                label="Original Texture",
                pixels=state.original_pixels,
                operation="ORIGINAL",
                prompt="",
            )

        hist_mgr.push(
            label=f"AI {state.current_operation}: {state.current_prompt[:25]}",
            pixels=preview_pixels,
            operation=state.current_operation,
            prompt=state.current_prompt,
        )

        # 3. Image Editor alanlarını önceden asıl görsele yönlendir
        for window in getattr(getattr(bpy.context, "window_manager", None), "windows", []):
            for area in getattr(window.screen, "areas", []):
                if area.type == 'IMAGE_EDITOR' and area.spaces.active:
                    area.spaces.active.image = base_image

        # 4. Orijinal dokuya uygula ve preview imajını sil
        ImageManager.apply_to_original(base_image, preview_pixels)

        # 5. Viewport ve materyal ekranını anında yenile
        from ..blender.material_adapter import BlenderMaterialAdapter
        BlenderMaterialAdapter.force_viewport_redraw()

        self.report({'INFO'}, f"Texture uygulandı ve geçmişe kaydedildi: {base_image.name}")
        logger.info("Applied texture changes and saved history entry", image=base_image.name)

        return {'FINISHED'}
