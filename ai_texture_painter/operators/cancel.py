# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Cancel Operator.

Önizleme aşamasındaki işlemi iptal eder, geçici önizleme imajını siler
ve orijinal dokuyu geri yükler.
"""

import bpy

from ..blender.image_adapter import BlenderImageAdapter
from ..texture.image_manager import ImageManager
from ..core.state import get_state_manager, StateStatus
from ..core.logging import get_logger

logger = get_logger("operators.cancel")


class AITEXTURE_OT_cancel(bpy.types.Operator):
    """Önizleme sonucunu iptal eder ve orijinale döner."""

    bl_idname = "ai_texture.cancel"
    bl_label = "Cancel AI Preview"
    bl_description = "Önizlemeyi iptal et ve orijinal dokuyu koru"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        """Sadece önizleme veya işlem durumundayken çalışabilir."""
        state = get_state_manager().state
        return state.status in {StateStatus.PREVIEW, StateStatus.GENERATING, StateStatus.ERROR}

    def execute(self, context: bpy.types.Context):
        state_mgr = get_state_manager()
        state = state_mgr.state

        # Eğer generation devam ediyorsa asenkron abort sinyali gönder
        if state.status == StateStatus.GENERATING:
            state_mgr.request_abort()
            state_mgr.reset()
            wm = getattr(context, "window_manager", None)
            if wm:
                wm.ai_texture_progress = 0.0
                wm.ai_texture_status = "İptal edildi"
            for window in getattr(getattr(context, "window_manager", None), "windows", []):
                for area in getattr(window.screen, "areas", []):
                    area.tag_redraw()
            self.report({'INFO'}, "AI üretimi iptal edildi.")
            logger.info("Generation aborted by user")
            return {'FINISHED'}

        # 1. Asıl orijinal görseli bul (preview görselini değil)
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

        # 2. Image Editor alanlarını önceden asıl görsele yönlendir (silinmeden önce)
        if base_image:
            for window in getattr(getattr(context, "window_manager", None), "windows", []):
                for area in getattr(window.screen, "areas", []):
                    if area.type == 'IMAGE_EDITOR' and area.spaces.active:
                        area.spaces.active.image = base_image

        # 3. İptal et, yedeği yükle ve preview görselini temizle
        ImageManager.cancel_and_restore(base_image)

        # 4. Viewport'u yenile
        for window in getattr(getattr(context, "window_manager", None), "windows", []):
            for area in getattr(window.screen, "areas", []):
                area.tag_redraw()

        self.report({'INFO'}, "İşlem iptal edildi, orijinal doku korundu.")
        logger.info("Cancelled texture generation/preview")

        return {'FINISHED'}
