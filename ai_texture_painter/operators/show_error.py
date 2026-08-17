# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Error Dialog Operator.

Kullanıcıya hata ayrıntılarını, çözüm önerilerini ve
Preferences kısayolunu içeren bir açılır pencere sunar.
"""

import bpy


class AITEXTURE_OT_show_error(bpy.types.Operator):
    """AI hata detaylarını ve çözüm önerilerini gösterir."""

    bl_idname = "ai_texture.show_error"
    bl_label = "AI Texture Painter — Hata"
    bl_options = {'INTERNAL'}

    message: bpy.props.StringProperty(name="Hata Mesajı", default="Bilinmeyen bir hata oluştu.")
    error_code: bpy.props.StringProperty(name="Hata Kodu", default="UNKNOWN")

    def execute(self, context: bpy.types.Context):
        return {'FINISHED'}

    def invoke(self, context: bpy.types.Context, event: bpy.types.Event):
        return context.window_manager.invoke_props_dialog(self, width=450)

    def draw(self, context: bpy.types.Context):
        layout = self.layout
        layout.label(text="İşlem Sırasında Hata Oluştu:", icon='ERROR')
        layout.separator()

        box = layout.box()
        box.alert = True
        box.label(text=self.message, icon='CANCEL')
        box.label(text=f"Hata Kodu: {self.error_code}")

        layout.separator()

        if self.error_code in {"API_KEY_MISSING", "AUTH_ERROR"}:
            layout.label(text="Çözüm: Lütfen Preferences altından geçerli API anahtarınızı kontrol edin.", icon='HELP')
            layout.operator("screen.userpref_show", text="Open Preferences", icon='PREFERENCES')
        elif self.error_code == "RATE_LIMIT":
            layout.label(text="Çözüm: API sağlayıcınızın dakikalık kota limiti aşıldı. Lütfen 30 saniye bekleyin.", icon='TIME')
        elif self.error_code == "NETWORK_ERROR":
            layout.label(text="Çözüm: İnternet bağlantınızı veya yerel sunucu adresinizi kontrol edin.", icon='WORLD')
