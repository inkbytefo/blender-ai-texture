# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Custom property group tanımları.

Scene'e bağlanan tüm addon property'lerini içerir.
"""

import bpy


class AITextureProperties(bpy.types.PropertyGroup):
    """AI Texture Painter custom property group."""

    # ── İşlem türü ──

    operation: bpy.props.EnumProperty(
        name="Operation",
        description="AI işlem türü",
        items=[
            (
                'FILL',
                "Fill",
                "AI ile maskeli alanı doldur",
                'BRUSH_DATA',
                0,
            ),
            (
                'REMOVE',
                "Remove",
                "Maskeli alandaki içeriği kaldır",
                'BRUSH_SOFTEN',
                1,
            ),
            (
                'GENERATE',
                "Generate",
                "Yeni texture üret",
                'ADD',
                2,
            ),
        ],
        default='FILL',
    )

    # ── Prompt alanları ──

    prompt: bpy.props.StringProperty(
        name="Prompt",
        description="AI'ya ne üretmesini istediğinizi yazın",
        default="",
        maxlen=2000,
    )

    negative_prompt: bpy.props.StringProperty(
        name="Negative Prompt",
        description="İstemediğiniz özellikleri belirtin (ör: blurry, low quality)",
        default="",
        maxlen=500,
    )

    # ── Hedef Doku (Target Texture) ──

    target_image: bpy.props.PointerProperty(
        name="Target Texture",
        type=bpy.types.Image,
        description="Boyanacak hedef doku (Boş bırakılırsa Base Color dokusu otomatik seçilir)",
    )

    # ── Referans Görsel (Reference Conditioning) ──

    reference_image: bpy.props.PointerProperty(
        name="Reference Image",
        type=bpy.types.Image,
        description="AI üretimine stil ve içerik yönlendirmesi sağlayan referans görsel",
    )

    # ── Generation parametreleri ──

    strength: bpy.props.FloatProperty(
        name="Strength",
        description="AI değişiklik gücü. 0 = orijinale yakın, 1 = tamamen yeni",
        default=0.75,
        min=0.0,
        max=1.0,
        step=5,
        precision=2,
    )

    seed: bpy.props.IntProperty(
        name="Seed",
        description="Tekrarlanabilirlik için seed değeri. -1 = rastgele",
        default=-1,
        min=-1,
    )

    random_seed: bpy.props.BoolProperty(
        name="Random Seed",
        description="Her generation'da rastgele seed kullan",
        default=True,
    )

    variation_count: bpy.props.IntProperty(
        name="Variations",
        description="Kaç farklı sonuç üretilecek",
        default=4,
        min=1,
        max=8,
    )

    selected_variation: bpy.props.IntProperty(
        name="Selected Variation",
        description="Seçili varyasyon indeksi",
        default=0,
        min=0,
    )

    # ── Mask & Context parametreleri ──

    context_padding: bpy.props.IntProperty(
        name="Context Padding",
        description="Seçili alanın etrafından AI'a bağlam olarak verilecek piksel payı (Photoshop Generative Fill)",
        default=32,
        min=0,
        max=512,
    )

    feather_radius: bpy.props.IntProperty(
        name="Feather",
        description="Mask kenar yumuşatma yarıçapı (piksel)",
        default=5,
        min=0,
        max=50,
    )
