# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Addon Preferences Paneli.

Hazır model seçim listeleri (dropdown) ve özel (Custom) Model ID girişi sunar.
"""

import bpy


def _get_pref_idname() -> str:
    """Extension kök paket adını döndürür."""
    pkg = __package__
    if pkg:
        parts = pkg.split(".")
        if parts[0] == "bl_ext" and len(parts) >= 3:
            return ".".join(parts[:3])
        return parts[0]
    return "ai_texture_painter"


class AITexturePreferences(bpy.types.AddonPreferences):
    """AI Texture Painter addon preferences."""

    bl_idname = _get_pref_idname()

    # ── Provider seçimi ──

    active_provider: bpy.props.EnumProperty(
        name="AI Provider",
        description="Kullanılacak AI sağlayıcısı",
        items=[
            ('MOCK', "Mock (Test)", "Test sağlayıcısı — API anahtarı gerekmez"),
            ('FAL_AI', "fal.ai", "fal.ai (FLUX.1 Kontext, Schnell, Dev, Pro, Recraft vb.)"),
            ('OPENAI_COMPATIBLE', "OpenAI Compatible", "OpenAI DALL-E, OpenRouter, Together, LocalAI"),
            ('GEMINI', "Google Gemini / Imagen", "Google AI Studio (Imagen 3, Gemini Flash / Pro)"),
        ],
        default='FAL_AI',
    )

    # ── fal.ai Ayarları ──

    fal_api_key: bpy.props.StringProperty(
        name="fal.ai API Key",
        description="fal.ai API anahtarınız (fal.ai/dashboard/keys adresinden alınır)",
        subtype='PASSWORD',
        default="",
    )

    fal_model_choice: bpy.props.EnumProperty(
        name="Model",
        description="Kullanılacak fal.ai modeli",
        items=[
            ('fal-ai/nano-banana-2/edit', "Nano Banana 2 (Google Next-Gen SOTA)", "Google'ın en gelişmiş görsel üretim ve düzenleme modeli"),
            ('openai/gpt-image-2', "GPT Image 2 (OpenAI Next-Gen)", "OpenAI'ın en güncel detaylı metin ve tipografi modeli"),
            ('openai/gpt-image-2/edit', "GPT Image 2 Edit (OpenAI Inpaint)", "OpenAI'ın hassas görsel düzenleme ve inpainting modeli"),
            ('fal-ai/flux-2-pro', "FLUX.2 [pro] (Next-Gen High Quality)", "En güncel FLUX.2 yüksek kalite görsel üretim modeli"),
            ('fal-ai/flux-pro/kontext', "FLUX.1 Kontext [pro] (Local & Scene Edits)", "Referans görsel ve metin ile hedeflenmiş bölgesel düzenleme"),
            ('fal-ai/flux/schnell', "FLUX.1 [schnell] (Ultra Fast - 4 Steps)", "1-4 adımda ultra hızlı ve ekonomik üretim"),
            ('fal-ai/flux/dev', "FLUX.1 [dev] (High Quality)", "Yüksek detay ve görsel kalitesi"),
            ('fal-ai/flux-pro', "FLUX.1 [pro] (Frontier Quality)", "En üst düzey görsel üretimi"),
            ('fal-ai/flux-lora/inpainting', "FLUX.1 LoRA Inpainting", "Maske tabanlı dolgu"),
            ('fal-ai/flux-pro/v1/fill', "FLUX.1 Fill [pro]", "Profesyonel inpainting ve outpainting"),
            ('fal-ai/recraft-v3', "Recraft V3", "Tasarım ve vektör/raster doku modeli"),
            ('CUSTOM', "Custom Model ID (Özel Model)", "Kendi belirleyeceğiniz özel model ID"),
        ],
        default='fal-ai/nano-banana-2/edit',
    )

    fal_custom_model: bpy.props.StringProperty(
        name="Custom Model ID",
        description="Özel fal.ai model ID'si (Örn: fal-ai/flux-pro/kontext)",
        default="",
    )

    # ── OpenAI / Compatible Ayarları ──

    openai_api_key: bpy.props.StringProperty(
        name="OpenAI API Key",
        description="OpenAI veya OpenRouter API anahtarınız",
        subtype='PASSWORD',
        default="",
    )

    openai_base_url: bpy.props.StringProperty(
        name="Base URL",
        description="API uç nokta adresi (Örn: https://api.openai.com/v1 veya https://openrouter.ai/api/v1)",
        default="https://api.openai.com/v1",
    )

    openai_model_choice: bpy.props.EnumProperty(
        name="Model",
        description="Kullanılacak OpenAI uyumlu model",
        items=[
            ('dall-e-3', "DALL-E 3 (High Quality)", "OpenAI en yüksek kaliteli model"),
            ('dall-e-2', "DALL-E 2 (Fast / Inpaint)", "OpenAI hızlı inpainting modeli"),
            ('gpt-4o', "GPT-4o (Multimodal)", "OpenAI multimodal görsel modeli"),
            ('CUSTOM', "Custom Model ID (Özel Model)", "Özel model ID"),
        ],
        default='dall-e-3',
    )

    openai_custom_model: bpy.props.StringProperty(
        name="Custom Model ID",
        description="Özel OpenAI uyumlu model ID (Örn: flux-1-schnell, midjourney)",
        default="",
    )

    # ── Google Gemini / Imagen Ayarları ──

    gemini_api_key: bpy.props.StringProperty(
        name="Gemini API Key",
        description="Google AI Studio API anahtarınız (aistudio.google.com)",
        subtype='PASSWORD',
        default="",
    )

    gemini_model_choice: bpy.props.EnumProperty(
        name="Model",
        description="Google görsel üretim modeli",
        items=[
            ('gemini-3.1-flash-image', "Nano Banana 2 (gemini-3.1-flash-image)", "Google'ın en güncel SOTA görsel üretim modeli (Önerilen)"),
            ('gemini-3.1-flash-lite-image', "Nano Banana 2 Lite (gemini-3.1-flash-lite-image)", "Hızlı ve ekonomik görsel üretim modeli"),
            ('gemini-3-pro-image', "Nano Banana Pro (gemini-3-pro-image)", "En yüksek detay ve profesyonel kalite"),
            ('gemini-2.5-flash-image', "Nano Banana (gemini-2.5-flash-image)", "Kararlı görsel üretim modeli"),
            ('CUSTOM', "Custom Model ID (Özel Model)", "Özel Google model ID"),
        ],
        default='gemini-3.1-flash-image',
    )

    gemini_custom_model: bpy.props.StringProperty(
        name="Custom Model ID",
        description="Özel Google model ID (Örn: gemini-2.0-flash)",
        default="",
    )

    # ── Genel Ayarlar ──

    default_variation_count: bpy.props.IntProperty(
        name="Default Variations",
        description="Varsayılan varyasyon sayısı",
        default=4,
        min=1,
        max=8,
    )

    cache_enabled: bpy.props.BoolProperty(
        name="Enable Cache",
        description="Aynı request tekrarlandığında önbellek kullan",
        default=True,
    )

    log_level: bpy.props.EnumProperty(
        name="Log Level",
        description="Console log detay seviyesi",
        items=[
            ('DEBUG', "Debug", "Tüm mesajlar"),
            ('INFO', "Info", "Bilgilendirme ve üzeri"),
            ('WARNING', "Warning", "Uyarı ve üzeri"),
            ('ERROR', "Error", "Sadece hatalar"),
        ],
        default='INFO',
    )

    def draw(self, context):
        layout = self.layout

        layout.label(text="Aktif AI Sağlayıcısı:", icon='WORLD')
        layout.prop(self, "active_provider", text="")

        layout.separator()

        box = layout.box()
        provider = self.active_provider

        if provider == 'MOCK':
            box.label(text="Mock Provider (Test Modu)", icon='INFO')
            box.label(text="İnternet bağlantısı veya API anahtarı gerekmez. Sentetik doku üretir.")

        elif provider == 'FAL_AI':
            box.label(text="fal.ai Ayarları", icon='LOCKED')
            box.prop(self, "fal_api_key")
            box.prop(self, "fal_model_choice", text="Model")
            if self.fal_model_choice == 'CUSTOM':
                box.prop(self, "fal_custom_model", text="Custom ID")
            box.separator()
            box.label(text="API Key: fal.ai/dashboard/keys", icon='URL')

        elif provider == 'OPENAI_COMPATIBLE':
            box.label(text="OpenAI / Compatible API Ayarları", icon='LOCKED')
            box.prop(self, "openai_api_key")
            box.prop(self, "openai_base_url")
            box.prop(self, "openai_model_choice", text="Model")
            if self.openai_model_choice == 'CUSTOM':
                box.prop(self, "openai_custom_model", text="Custom ID")

        elif provider == 'GEMINI':
            box.label(text="Google AI Studio (Gemini / Imagen) Ayarları", icon='LOCKED')
            box.prop(self, "gemini_api_key")
            box.prop(self, "gemini_model_choice", text="Model")
            if self.gemini_model_choice == 'CUSTOM':
                box.prop(self, "gemini_custom_model", text="Custom ID")
            box.separator()
            box.label(text="Ücretsiz API anahtarı: aistudio.google.com", icon='URL')

        layout.separator()
        box_gen = layout.box()
        box_gen.label(text="Genel Ayarlar", icon='PREFERENCES')
        box_gen.prop(self, "default_variation_count")
        box_gen.prop(self, "cache_enabled")
        box_gen.prop(self, "log_level")

        # ── Uninstall butonu ──
        layout.separator()
        box_un = layout.box()
        box_un.label(text="Eklenti Yönetimi", icon='TRASH')
        box_un.operator("ai_texture.uninstall", text="Uninstall AI Texture Painter", icon='CANCEL')
