# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""Unit tests for pure Python PNG encoder / decoder."""

import numpy as np
import pytest

from ai_texture_painter.utils.png import numpy_to_png_bytes, png_bytes_to_numpy


class TestPngUtility:
    def test_png_roundtrip_rgba(self):
        """RGBA float32 görselin PNG'ye dönüştürülüp tekrar kayıpsız okunması testi."""
        h, w = 32, 32
        original = np.random.RandomState(42).uniform(0.0, 1.0, (h, w, 4)).astype(np.float32)

        png_bytes = numpy_to_png_bytes(original)
        assert len(png_bytes) > 0
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

        decoded = png_bytes_to_numpy(png_bytes)
        assert decoded.shape == (h, w, 4)
        assert decoded.dtype == np.float32

        # 8-bit kuantizasyon toleransı (1/255 ≈ 0.004)
        np.testing.assert_allclose(decoded, original, atol=1.0 / 255.0)

    def test_png_roundtrip_rgb(self):
        """RGB görselin otomatik alpha eklenerek RGBA olarak okunması testi."""
        h, w = 16, 16
        original_rgb = np.full((h, w, 3), 0.8, dtype=np.float32)

        png_bytes = numpy_to_png_bytes(original_rgb)
        decoded = png_bytes_to_numpy(png_bytes)

        assert decoded.shape == (h, w, 4)
        # Alfa kanalı 1.0 olmalı
        np.testing.assert_allclose(decoded[..., 3], 1.0)
        np.testing.assert_allclose(decoded[..., :3], 0.8, atol=1.0 / 255.0)

    def test_invalid_png_signature(self):
        """Geçersiz PNG verisinde ValueError fırlatılması testi."""
        with pytest.raises(ValueError, match="Geçersiz PNG imzası"):
            png_bytes_to_numpy(b"NOT_A_PNG_FILE")
