# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

import pytest
import numpy as np

from ai_texture_painter.texture.pbr import PBRGenerator


class TestPBRGenerator:
    """Saf NumPy PBR Generator birim testleri."""

    def test_generate_height_map(self):
        # 4 kanallı RGB test görseli (H=32, W=32)
        rgb = np.zeros((32, 32, 4), dtype=np.float32)
        rgb[..., 0] = 1.0  # Tamamen kırmızı
        rgb[..., 3] = 1.0

        height = PBRGenerator.generate_height_map(rgb)
        assert height.shape == (32, 32)
        # Rec.709 Kırmızı luma katsayısı: ~0.2126
        assert np.allclose(height, 0.2126, atol=1e-3)

        # Invert kontrolü
        inv_height = PBRGenerator.generate_height_map(rgb, invert=True)
        assert np.allclose(inv_height, 1.0 - 0.2126, atol=1e-3)

    def test_generate_normal_map_flat_surface(self):
        # Düz beyaz yüzey
        flat = np.ones((64, 64, 4), dtype=np.float32)
        normal = PBRGenerator.generate_normal_map(flat, strength=1.0)

        assert normal.shape == (64, 64, 4)
        assert normal.dtype == np.float32

        # Düz yüzeyde teğet uzayı normali N = (0, 0, 1) olmalıdır.
        # [0, 1] aralığına kodlandığında: R = 0.5, G = 0.5, B = 1.0, A = 1.0 (Mor/Mavi tonu #8080FF)
        assert np.allclose(normal[..., 0], 0.5, atol=1e-3)
        assert np.allclose(normal[..., 1], 0.5, atol=1e-3)
        assert np.allclose(normal[..., 2], 1.0, atol=1e-3)
        assert np.allclose(normal[..., 3], 1.0, atol=1e-3)

    def test_generate_normal_map_gradient_slope(self):
        # Soldan sağa eğimli rampa
        ramp = np.linspace(0.0, 1.0, 64, dtype=np.float32)
        img = np.tile(ramp, (64, 1))

        normal = PBRGenerator.generate_normal_map(img, strength=2.0)
        assert normal.shape == (64, 64, 4)

        # X türevi pozitif olduğundan normalin R bileşeni 0.5'ten küçük olmalı
        # (N_x = -dx < 0 -> (N_x + 1)/2 < 0.5)
        middle_r = normal[32, 32, 0]
        assert middle_r < 0.5

        # Normal vektör uzunluğu 1.0 olmalıdır
        nx = (normal[..., 0] * 2.0) - 1.0
        ny = (normal[..., 1] * 2.0) - 1.0
        nz = (normal[..., 2] * 2.0) - 1.0
        length = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
        assert np.allclose(length, 1.0, atol=1e-3)

    def test_generate_roughness_map(self):
        img = np.random.RandomState(42).uniform(0.0, 1.0, (40, 40, 4)).astype(np.float32)
        rough = PBRGenerator.generate_roughness_map(img, base_roughness=0.6, variance=0.2)

        assert rough.shape == (40, 40, 4)
        assert np.all(rough >= 0.0) and np.all(rough <= 1.0)
        # R, G, B kanalları birbirine eşit grayscale olmalıdır
        assert np.allclose(rough[..., 0], rough[..., 1])
        assert np.allclose(rough[..., 1], rough[..., 2])
        assert np.allclose(rough[..., 3], 1.0)
