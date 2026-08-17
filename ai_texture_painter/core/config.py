# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Konfigürasyon yönetimi.

Addon preferences'tan ayarları okur ve global config sağlar.
Blender 5.x Extensions Platform ve geleneksel eklenti yükleme biçimlerini destekler.
"""

from typing import Optional
import bpy

# Addon ID — blender_manifest.toml ile eşleşmeli
ADDON_ID = "ai_texture_painter"

# Sürüm bilgisi
ADDON_VERSION = (0, 1, 0)
ADDON_VERSION_STRING = "0.1.0"


def get_addon_preferences() -> Optional[bpy.types.AddonPreferences]:
    """Blender addon preferences nesnesini döndürür.

    Blender 5.x Extensions (bl_ext.user_default.ai_texture_painter)
    ve yerel geliştirme yollarını otomatik tarar.
    """
    if not hasattr(bpy.context, "preferences") or not hasattr(bpy.context.preferences, "addons"):
        return None

    addons = bpy.context.preferences.addons

    # 1. Doğrudan paket adı ile dene
    pkg_name = __package__
    if pkg_name:
        root_pkg = pkg_name.split(".")[0]
        if root_pkg in addons:
            return addons[root_pkg].preferences
        if pkg_name in addons:
            return addons[pkg_name].preferences

    # 2. Standart ADDON_ID ile dene
    if ADDON_ID in addons:
        return addons[ADDON_ID].preferences

    # 3. Extensions Platform için sonu '.ai_texture_painter' ile biten anahtarı ara
    for key, addon in addons.items():
        if key.endswith(f".{ADDON_ID}") or key == ADDON_ID:
            return addon.preferences

    return None


def get_config() -> dict:
    """Genel konfigürasyon sözlüğünü döndürür."""
    defaults = {
        "active_provider": "MOCK",
        "log_level": "INFO",
        "cache_enabled": True,
        "default_variation_count": 4,
    }

    prefs = get_addon_preferences()
    if prefs is None:
        return defaults

    return {
        "active_provider": getattr(prefs, "active_provider", defaults["active_provider"]),
        "log_level": getattr(prefs, "log_level", defaults["log_level"]),
        "cache_enabled": getattr(prefs, "cache_enabled", defaults["cache_enabled"]),
        "default_variation_count": getattr(
            prefs, "default_variation_count", defaults["default_variation_count"]
        ),
    }


def initialize():
    """Addon ilk başlatma işlemleri."""
    from . import logging as log_module

    config = get_config()
    log_module.set_log_level(config["log_level"])

    logger = log_module.get_logger("config")
    logger.info(
        "AI Texture Painter initialized",
        version=ADDON_VERSION_STRING,
    )
