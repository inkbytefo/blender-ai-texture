# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
History Operators.

Eklenti içi doku geçmişini (Undo, Redo, Clear) yöneten Blender operatörleri.
"""

import bpy

from ..blender.image_adapter import BlenderImageAdapter
from ..texture.history import get_history_manager
from ..core.logging import get_logger

logger = get_logger("operators.history")


class AITEXTURE_OT_undo(bpy.types.Operator):
    """Son AI texture değişikliğini geri alır."""

    bl_idname = "ai_texture.undo"
    bl_label = "Undo AI Change"
    bl_description = "Bir önceki texture durumuna geri dön"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return get_history_manager().can_undo and BlenderImageAdapter.get_active_image(context) is not None

    def execute(self, context: bpy.types.Context):
        hist_mgr = get_history_manager()
        entry = hist_mgr.undo()

        if not entry:
            self.report({'WARNING'}, "Geri alınacak başka adım yok.")
            return {'CANCELLED'}

        base_image = BlenderImageAdapter.get_active_image(context)
        if base_image:
            BlenderImageAdapter.numpy_to_image(entry.pixels, base_image)
            self.report({'INFO'}, f"Geri alındı: {entry.label}")
            logger.info("Texture state reverted", label=entry.label)

        return {'FINISHED'}


class AITEXTURE_OT_redo(bpy.types.Operator):
    """Geri alınan AI texture değişikliğini tekrar uygular."""

    bl_idname = "ai_texture.redo"
    bl_label = "Redo AI Change"
    bl_description = "Geri alınan texture durumunu tekrar uygula"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return get_history_manager().can_redo and BlenderImageAdapter.get_active_image(context) is not None

    def execute(self, context: bpy.types.Context):
        hist_mgr = get_history_manager()
        entry = hist_mgr.redo()

        if not entry:
            self.report({'WARNING'}, "İleri alınacak başka adım yok.")
            return {'CANCELLED'}

        base_image = BlenderImageAdapter.get_active_image(context)
        if base_image:
            BlenderImageAdapter.numpy_to_image(entry.pixels, base_image)
            self.report({'INFO'}, f"Tekrar uygulandı: {entry.label}")
            logger.info("Texture state reapplied", label=entry.label)

        return {'FINISHED'}


class AITEXTURE_OT_clear_history(bpy.types.Operator):
    """Tüm doku geçmişi yığınını ve ayrılan belleği temizler."""

    bl_idname = "ai_texture.clear_history"
    bl_label = "Clear History"
    bl_description = "Doku geçmişini temizle ve belleği boşalt"
    bl_options = {'REGISTER'}

    def execute(self, context: bpy.types.Context):
        get_history_manager().clear()
        self.report({'INFO'}, "Doku geçmişi temizlendi.")
        return {'FINISHED'}
