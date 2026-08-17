# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Uninstall Operator.

Eklentinin Blender içerisinden tek tıkla devre dışı bırakılmasını
ve diskteki dosyalarının güvenle temizlenmesini sağlar.
"""

import os
import shutil
import bpy

from ..core.logging import get_logger

logger = get_logger("operators.uninstall")


class AITEXTURE_OT_uninstall(bpy.types.Operator):
    """AI Texture Painter eklentisini tamamen kaldırır ve diskten siler."""

    bl_idname = "ai_texture.uninstall"
    bl_label = "Uninstall AI Texture Painter"
    bl_description = "Eklentiyi devre dışı bırak ve diskteki dosyalarını temizle"
    bl_options = {'INTERNAL'}

    confirm: bpy.props.BoolProperty(
        name="Eminim, kaldır",
        default=False,
    )

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.label(text="Eklentiyi Kaldır (Uninstall):", icon='CANCEL')
        box = layout.box()
        box.alert = True
        box.label(text="Bu işlem eklentiyi tamamen kaldıracaktır.")
        box.label(text="Devam etmek istiyor musunuz?")
        layout.prop(self, "confirm")

    def execute(self, context: bpy.types.Context):
        if not self.confirm:
            self.report({'WARNING'}, "Kaldırma işlemi onaylanmadı.")
            return {'CANCELLED'}

        # Eklenti kök dizinini bul
        module_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        pkg_name = __package__.split(".")[0] if __package__ else "ai_texture_painter"

        logger.info("Uninstalling addon", directory=module_dir, package=pkg_name)

        try:
            # 1. Addon'u devre dışı bırak
            if pkg_name in bpy.context.preferences.addons:
                bpy.ops.preferences.addon_disable(module=pkg_name)

            # 2. Dosyaları temizle
            if os.path.exists(module_dir) and "ai_texture_painter" in module_dir:
                shutil.rmtree(module_dir, ignore_errors=True)

            self.report({'INFO'}, "AI Texture Painter başarıyla kaldırıldı.")
            return {'FINISHED'}

        except Exception as e:
            logger.error("Uninstall failed", error=str(e))
            self.report({'ERROR'}, f"Kaldırma sırasında hata: {str(e)}")
            return {'CANCELLED'}
