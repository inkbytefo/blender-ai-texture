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
            ('OPENROUTER', "OpenRouter", "OpenRouter (GPT Image 2, Seedream 4.5, FLUX.2, Recraft vb.)"),
            ('FAL_AI', "fal.ai", "fal.ai (Nano Banana 2, FLUX.1/2, GPT Image 2 vb.)"),
            ('OPENAI_COMPATIBLE', "OpenAI (ChatGPT)", "OpenAI resmi API (GPT Image 2, DALL-E 3) veya uyumlu servisler"),
            ('GEMINI', "Google Gemini / Imagen", "Google AI Studio (Nano Banana 2, Gemini Flash / Pro)"),
            ('MOCK', "Mock (Test)", "Test sağlayıcısı — API anahtarı gerekmez"),
        ],
        default='OPENROUTER',
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

    # ── OpenRouter Ayarları ──

    openrouter_api_key: bpy.props.StringProperty(
        name="OpenRouter API Key",
        description="OpenRouter API anahtarınız (openrouter.ai/keys)",
        subtype='PASSWORD',
        default="",
    )

    openrouter_base_url: bpy.props.StringProperty(
        name="Base URL",
        description="OpenRouter API uç noktası",
        default="https://openrouter.ai/api/v1",
    )

    openrouter_model_choice: bpy.props.EnumProperty(
        name="Model",
        description="Kullanılacak OpenRouter görsel modeli",
        items=[
            ('openai/gpt-image-2', "GPT Image 2 (OpenAI Next-Gen)", "OpenAI GPT Image 2 en güncel görsel modeli (Önerilen)"),
            ('bytedance-seed/seedream-4.5', "Seedream 4.5 (ByteDance High Quality)", "ByteDance Seedream 4.5 yüksek kalite görsel modeli"),
            ('black-forest-labs/flux.2-pro', "FLUX.2 [pro] (Black Forest Labs)", "En yüksek kaliteli FLUX.2 modeli"),
            ('black-forest-labs/flux-1-schnell', "FLUX.1 [schnell] (Hızlı)", "FLUX.1 Schnell hızlı görsel üretim modeli"),
            ('google/gemini-2.5-flash-image', "Gemini 2.5 Flash Image (Google)", "Google Gemini multimodal görsel modeli"),
            ('recraft/recraft-v3', "Recraft V3 (Tasarım & Raster/Vektör)", "Recraft V3 profesyonel tasarım modeli"),
            ('CUSTOM', "Custom Model ID (Özel Model)", "OpenRouter üzerindeki herhangi bir görsel model slug'ı"),
        ],
        default='openai/gpt-image-2',
    )

    openrouter_custom_model: bpy.props.StringProperty(
        name="Custom Model ID",
        description="Özel OpenRouter model ID (Örn: stabilityai/stable-diffusion-3.5-large)",
        default="",
    )

    openrouter_quality: bpy.props.EnumProperty(
        name="Kalite",
        description="Görsel üretim kalitesi",
        items=[
            ('high', "High (Yüksek Kalite)", "En yüksek detay ve çözünürlük"),
            ('medium', "Medium (Orta)", "Dengeli kalite ve maliyet"),
            ('low', "Low (Hızlı Taslak)", "En hızlı ve en ekonomik taslak üretimi"),
            ('auto', "Auto (Otomatik)", "Sağlayıcının varsayılanı"),
        ],
        default='high',
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
        description="Kullanılacak OpenAI / ChatGPT modeli",
        items=[
            ('gpt-image-2', "GPT Image 2 (Official OpenAI Next-Gen)", "OpenAI en güncel, yüksek detay ve mükemmel tipografi modeli (Önerilen)"),
            ('gpt-image-1.5', "GPT Image 1.5", "OpenAI GPT Image 1.5 modeli"),
            ('gpt-image-1', "GPT Image 1", "OpenAI GPT Image 1 modeli"),
            ('gpt-image-1-mini', "GPT Image 1 Mini", "Hızlı ve ekonomik OpenAI modeli"),
            ('dall-e-3', "DALL-E 3 (High Quality)", "OpenAI DALL-E 3 modeli"),
            ('dall-e-2', "DALL-E 2 (Legacy Inpaint)", "OpenAI DALL-E 2 modeli"),
            ('gpt-4o', "GPT-4o (Multimodal)", "OpenAI GPT-4o multimodal modeli"),
            ('CUSTOM', "Custom Model ID (Özel Model)", "Özel model ID"),
        ],
        default='gpt-image-2',
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
            ('imagen-3.0-generate-002', "Imagen 3 (imagen-3.0-generate-002)", "Google Imagen 3 resmi görsel üretim modeli (Önerilen)"),
            ('gemini-3.1-flash-image', "Nano Banana 2 (gemini-3.1-flash-image)", "Google en güncel görsel modeli"),
            ('gemini-3.1-flash-lite-image', "Nano Banana 2 Lite (gemini-3.1-flash-lite-image)", "Hızlı ve ekonomik görsel modeli"),
            ('gemini-3-pro-image', "Nano Banana Pro (gemini-3-pro-image)", "Yüksek detay ve profesyonel kalite"),
            ('gemini-2.5-flash-image', "Nano Banana (gemini-2.5-flash-image)", "Kararlı görsel modeli"),
            ('CUSTOM', "Custom Model ID (Özel Model)", "Özel Google model ID"),
        ],
        default='imagen-3.0-generate-002',
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

        elif provider == 'OPENROUTER':
            box.label(text="OpenRouter Ayarları", icon='LOCKED')
            box.prop(self, "openrouter_api_key")
            box.prop(self, "openrouter_base_url")
            box.prop(self, "openrouter_model_choice", text="Model")
            if self.openrouter_model_choice == 'CUSTOM':
                box.prop(self, "openrouter_custom_model", text="Custom ID")
            box.prop(self, "openrouter_quality", text="Kalite")
            box.separator()
            box.label(text="API Key: openrouter.ai/keys", icon='URL')

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
