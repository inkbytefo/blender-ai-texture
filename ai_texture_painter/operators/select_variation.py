# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Select Variation Operator.

Üretilen çoklu varyasyonlar arasında kullanıcının seçim yapmasını
ve önizlemenin anında seçilen varyasyona güncellenmesini sağlar.
"""

import bpy

from ..blender.image_adapter import BlenderImageAdapter
from ..texture.image_manager import ImageManager
from ..core.state import get_state_manager, StateStatus
from ..core.logging import get_logger

logger = get_logger("operators.select_variation")


class AITEXTURE_OT_select_variation(bpy.types.Operator):
    """Üretilen varyasyonlardan birini aktif önizleme olarak seçer."""

    bl_idname = "ai_texture.select_variation"
    bl_label = "Select Variation"
    bl_description = "Bu varyasyonu önizleme olarak seç"
    bl_options = {'REGISTER', 'UNDO'}

    variation_index: bpy.props.IntProperty(
        name="Variation Index",
        description="Seçilen varyasyon indeksi (0 tabanlı)",
        default=0,
        min=0,
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        state = get_state_manager().state
        return (
            state.status == StateStatus.PREVIEW
            and len(state.variations) > 0
        )

    def execute(self, context: bpy.types.Context):
        state_mgr = get_state_manager()
        state = state_mgr.state

        if not (0 <= self.variation_index < len(state.variations)):
            self.report({'ERROR'}, f"Geçersiz varyasyon indeksi: {self.variation_index}")
            return {'CANCELLED'}

        # State'i güncelle
        state_mgr.update(selected_variation=self.variation_index)

        # Aktif görseli bul
        base_image = BlenderImageAdapter.get_active_image(context)
        if not base_image and state.active_image_name:
            base_image = bpy.data.images.get(state.active_image_name)

        if not base_image:
            self.report({'ERROR'}, "Aktif texture bulunamadı!")
            return {'CANCELLED'}

        # Seçilen varyasyonun pikselleriyle preview'ı güncelle
        selected_pixels = state.variations[self.variation_index]
        preview_img = ImageManager.create_or_update_preview(base_image, selected_pixels)

        if context.space_data and context.space_data.type == 'IMAGE_EDITOR':
            context.space_data.image = preview_img

        logger.info("Variation selected", index=self.variation_index)
        return {'FINISHED'}
