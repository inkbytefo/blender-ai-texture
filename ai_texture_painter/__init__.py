# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
AI Texture Painter — Blender Extension Entry Point.

Blender 5.x Extensions Platform kullanır.
Metadata blender_manifest.toml dosyasında tanımlanmıştır.
"""

import bpy

from .ui.properties import AITextureProperties
from .ui.preferences import AITexturePreferences
from .ui.panels import (
    AITEXTURE_PT_main_panel,
    AITEXTURE_PT_results_panel,
    AITEXTURE_PT_settings_panel,
)
from .operators.generate import AITEXTURE_OT_generate
from .operators.apply import AITEXTURE_OT_apply
from .operators.cancel import AITEXTURE_OT_cancel
from .operators.select_variation import AITEXTURE_OT_select_variation
from .operators.history_ops import (
    AITEXTURE_OT_undo,
    AITEXTURE_OT_redo,
    AITEXTURE_OT_clear_history,
)
from .operators.show_error import AITEXTURE_OT_show_error
from .operators.uninstall import AITEXTURE_OT_uninstall
from .ai.registry import get_registry
from .ai.providers.mock import MockProvider
from .ai.providers.openai_compatible import OpenAICompatibleProvider
from .ai.providers.openrouter import OpenRouterProvider
from .ai.providers.gemini import GeminiProvider
from .ai.providers.fal_ai import FalAIProvider


# ──────────────────────────────────────────────
# Kayıt edilecek tüm sınıflar
# ──────────────────────────────────────────────

_classes = (
    # Property groups
    AITextureProperties,

    # Preferences
    AITexturePreferences,

    # Operators
    AITEXTURE_OT_generate,
    AITEXTURE_OT_apply,
    AITEXTURE_OT_cancel,
    AITEXTURE_OT_select_variation,
    AITEXTURE_OT_undo,
    AITEXTURE_OT_redo,
    AITEXTURE_OT_clear_history,
    AITEXTURE_OT_show_error,
    AITEXTURE_OT_uninstall,

    # Panels (parent önce, child'lar sonra)
    AITEXTURE_PT_main_panel,
    AITEXTURE_PT_results_panel,
    AITEXTURE_PT_settings_panel,
)


# ──────────────────────────────────────────────
# Register / Unregister
# ──────────────────────────────────────────────

def register():
    """Extension kayıt fonksiyonu."""
    if __package__:
        AITexturePreferences.bl_idname = __package__

    for cls in _classes:
        bpy.utils.register_class(cls)

    # Scene'e property group ata
    bpy.types.Scene.ai_texture = bpy.props.PointerProperty(
        type=AITextureProperties,
        name="AI Texture Painter",
        description="AI Texture Painter ayarları",
    )

    # WindowManager'a progress property'leri ata
    bpy.types.WindowManager.ai_texture_progress = bpy.props.FloatProperty(
        name="AI Generation Progress",
        description="AI generation ilerleme durumu",
        default=0.0,
        min=0.0,
        max=1.0,
        subtype='FACTOR',
    )

    bpy.types.WindowManager.ai_texture_status = bpy.props.StringProperty(
        name="AI Status",
        description="AI generation durum mesajı",
        default="Hazır",
    )

    # Core initialization
    from .core import config
    config.initialize()

    # AI Provider Registry başlatma ve sağlayıcıların kaydı
    registry = get_registry()
    registry.register(MockProvider())
    registry.register(OpenAICompatibleProvider())
    registry.register(OpenRouterProvider())
    registry.register(GeminiProvider())
    registry.register(FalAIProvider())


def unregister():
    """Extension kayıt silme fonksiyonu."""
    try:
        del bpy.types.WindowManager.ai_texture_status
    except (AttributeError, RuntimeError):
        pass

    try:
        del bpy.types.WindowManager.ai_texture_progress
    except (AttributeError, RuntimeError):
        pass

    try:
        del bpy.types.Scene.ai_texture
    except (AttributeError, RuntimeError):
        pass

    for cls in reversed(_classes):
        try:
            bpy.utils.unregister_class(cls)
        except (RuntimeError, ValueError):
            pass

    # Registry temizleme
    get_registry().clear()
