# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""Unit tests for ResolutionManager."""

import numpy as np
import pytest

from ai_texture_painter.texture.resolution import ResolutionManager


class TestResolutionManager:
    def test_bounding_box_extraction(self):
        """Maskelenmiş alanın bounding box sınırlarını test et."""
        mask = np.zeros((100, 100), dtype=np.float32)
        mask[20:60, 30:80] = 1.0

        x, y, w, h = ResolutionManager.get_mask_bounding_box(mask, padding=0)

        assert x == 30
        assert y == 20
        assert w == 50
        assert h == 40

    def test_crop_and_place_roundtrip(self):
        """Kırpma ve tekrar yerleştirme işlemlerinin piksel konumunu koruduğunu doğrula."""
        original = np.zeros((64, 64, 4), dtype=np.float32)
        # Bounding box alanı
        bbox = (10, 15, 20, 25)  # x, y, w, h

        # Bölgeye özgü bir desen koy
        patch = np.ones((25, 20, 4), dtype=np.float32) * 0.75

        placed = ResolutionManager.place_region(original, patch, bbox)

        # Yerleştirilen bölgeyi tekrar kırp
        recropped = ResolutionManager.crop_region(placed, bbox)

        np.testing.assert_allclose(recropped, patch)
        # Dışarıdaki alanlar 0 olarak kalmalı
        assert np.isclose(placed[0, 0, 0], 0.0)

    def test_resize_image(self):
        """Saf NumPy bilinear resize metodunu doğrula."""
        img = np.ones((16, 16, 4), dtype=np.float32) * 0.5
        resized = ResolutionManager.resize_image(img, 32, 32)

        assert resized.shape == (32, 32, 4)
        np.testing.assert_allclose(resized, 0.5)
