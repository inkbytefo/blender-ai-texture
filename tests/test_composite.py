# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""Unit tests for TextureCompositor and MaskProcessor."""

import numpy as np
import pytest

from ai_texture_painter.texture.composite import TextureCompositor
from ai_texture_painter.texture.mask import MaskProcessor


class TestMaskProcessor:
    def test_normalize_mask_range(self):
        """Maske değerlerinin [0.0, 1.0] float32 aralığında olmasını doğrula."""
        raw_uint8 = np.array([[0, 128, 255]], dtype=np.uint8)
        normalized = MaskProcessor.normalize_mask(raw_uint8)

        assert normalized.dtype == np.float32
        assert normalized.min() >= 0.0
        assert normalized.max() <= 1.0
        assert np.isclose(normalized[0, 0], 0.0)
        assert np.isclose(normalized[0, 2], 1.0)

    def test_apply_feather_smooths_edge(self):
        """Feather operasyonunun sert kenarı kademeli geçişe dönüştürdüğünü doğrula."""
        mask = np.zeros((32, 32), dtype=np.float32)
        mask[8:24, 8:24] = 1.0

        feathered = MaskProcessor.apply_feather(mask, radius=4)

        assert feathered.shape == mask.shape
        # Merkez hala yüksek olmalı
        assert feathered[16, 16] > 0.8
        # Sınırın hemen dışı yumuşatılmış olmalı (0'dan büyük ama 1'den küçük)
        assert 0.0 < feathered[7, 16] < 1.0

    def test_invert_mask(self):
        """Maske tersleme testi."""
        mask = np.array([[0.0, 0.25, 1.0]], dtype=np.float32)
        inverted = MaskProcessor.invert_mask(mask)
        np.testing.assert_allclose(inverted, [[1.0, 0.75, 0.0]])


class TestTextureCompositor:
    def test_full_mask_compositing(self):
        """Mask = 1 olan yerlerde tamamen üretilmiş görselin gelmesini doğrula."""
        original = np.zeros((8, 8, 4), dtype=np.float32)
        generated = np.ones((8, 8, 4), dtype=np.float32)
        mask = np.ones((8, 8), dtype=np.float32)

        result = TextureCompositor.composite(original, generated, mask)
        np.testing.assert_allclose(result, generated)

    def test_zero_mask_compositing(self):
        """Mask = 0 olan yerlerde tamamen orijinal görselin korunmasını doğrula."""
        original = np.full((8, 8, 4), 0.4, dtype=np.float32)
        generated = np.ones((8, 8, 4), dtype=np.float32)
        mask = np.zeros((8, 8), dtype=np.float32)

        result = TextureCompositor.composite(original, generated, mask)
        np.testing.assert_allclose(result, original)

    def test_protected_pixel_verification(self):
        """Korumalı piksellerin bozulmadığını doğrulayan kontrol metodunu test et."""
        h, w = 16, 16
        original = np.random.RandomState(42).uniform(0, 1, (h, w, 4)).astype(np.float32)
        generated = np.random.RandomState(99).uniform(0, 1, (h, w, 4)).astype(np.float32)

        # Sadece merkez 8x8 alanı maskeli yap
        mask = np.zeros((h, w), dtype=np.float32)
        mask[4:12, 4:12] = 1.0

        result = TextureCompositor.composite(original, generated, mask)

        # Doğrulama başarılı olmalı
        assert TextureCompositor.verify_protected_pixels(original, result, mask)

        # Eğer dışarıdaki piksellerden biri bile değiştirilirse doğrulama hata vermelidir
        tampered = result.copy()
        tampered[0, 0, 0] += 0.1
        assert not TextureCompositor.verify_protected_pixels(original, tampered, mask)


class TestUVPolygonRasterizer:
    def test_triangle_rasterization(self):
        """2D UV üçgeninin doğru piksel maskesine rasterize edildiğini doğrula."""
        from ai_texture_painter.blender.uv_adapter import BlenderUVAdapter
        mask = np.zeros((64, 64), dtype=bool)
        # 0.2, 0.2 -> 0.8, 0.2 -> 0.5, 0.8 üçgeni
        v0 = (0.2 * 63, 0.2 * 63)
        v1 = (0.8 * 63, 0.2 * 63)
        v2 = (0.5 * 63, 0.8 * 63)

        BlenderUVAdapter._rasterize_triangle(v0, v1, v2, 64, 64, mask)
        active_pixels = np.sum(mask)
        assert active_pixels > 200
        # Merkez (32, 25) üçgenin içinde olmalı
        assert mask[25, 32]
        # Dışarıdaki köşe (5, 5) dışarıda olmalı
        assert not mask[5, 5]
