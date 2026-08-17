# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
AI capability ve operation enum tanımları.

Bu modül Phase 3'te provider'lar tarafından kullanılacak
capability tanımlarını içerir. Phase 1'de UI'ın capability-aware
tasarlanabilmesi için şimdiden tanımlanmıştır.
"""

from enum import Enum, auto


class AIOperation(Enum):
    """AI işlem türleri.

    Her işlem türü farklı gereksinimler ve parametreler taşır.
    """

    GENERATE = auto()
    """Tamamen yeni texture üretimi.
    Gerekli: prompt, width, height
    """

    FILL = auto()
    """Maskeli alanı prompt'a göre doldurma (inpaint).
    Gerekli: source_image, mask, prompt
    """

    REMOVE = auto()
    """Maskeli alandaki içeriği kaldırma.
    Gerekli: source_image, mask
    Opsiyonel: prompt
    """

    EXPAND = auto()
    """Texture sınırlarını genişletme (outpaint).
    Gerekli: source_image, mask
    """

    UPSCALE = auto()
    """Çözünürlük artırma (super-resolution).
    Gerekli: source_image
    """

    VARIATION = auto()
    """Mevcut sonucun varyasyonunu üretme.
    Gerekli: source_image
    """


class Capability(Enum):
    """AI provider'ın desteklediği özellikler.

    Her provider hangi capability'leri desteklediğini bildirmeli.
    UI, desteklenmeyen özellikleri otomatik olarak gizler/devre dışı bırakır.
    """

    # ── Temel generation modları ──

    TEXT_TO_IMAGE = auto()
    """Sadece prompt ile sıfırdan image üretme."""

    IMAGE_TO_IMAGE = auto()
    """Var olan image'ı prompt ile dönüştürme."""

    INPAINT = auto()
    """Maskeli bölgeyi prompt'a göre doldurma."""

    OUTPAINT = auto()
    """Image sınırlarını genişletme."""

    # ── Ek özellikler ──

    REFERENCE_IMAGE = auto()
    """Referans image ile yönlendirme."""

    VARIATIONS = auto()
    """Çoklu sonuç üretimi."""

    UPSCALE = auto()
    """Çözünürlük artırma (super-resolution)."""

    SEAMLESS = auto()
    """Tileable/seamless texture üretimi."""

    # ── Mask & kontrol ──

    MASK = auto()
    """Mask desteği (tüm inpaint provider'lar desteklemeli)."""

    DEPTH_CONTROL = auto()
    """Depth map ile kontrol (ControlNet benzeri)."""

    NORMAL_CONTROL = auto()
    """Normal map ile kontrol."""

    # ── Parametre kontrolü ──

    NEGATIVE_PROMPT = auto()
    """İstenmeyen özellikleri belirtme."""

    SEED_CONTROL = auto()
    """Seed ile tekrarlanabilir sonuçlar."""

    STRENGTH_CONTROL = auto()
    """Denoising strength (0-1) kontrolü."""
