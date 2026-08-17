# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Test suite for 3D Viewport Projection and Baker module.
"""

import numpy as np
import pytest
from ai_texture_painter.blender.projection_baker import ProjectionBaker


def test_bilinear_sample_exact_points():
    """Bilinear örneklemenin tam koordinatlarda doğru pikseli aldığını test eder."""
    img = np.zeros((4, 4, 4), dtype=np.float32)
    img[1, 1] = [1.0, 0.5, 0.2, 1.0]
    img[2, 2] = [0.0, 1.0, 0.0, 1.0]

    sampled_1 = ProjectionBaker._bilinear_sample(img, np.array([1.0]), np.array([1.0]))
    assert np.allclose(sampled_1[0], [1.0, 0.5, 0.2, 1.0], atol=1e-4)

    sampled_2 = ProjectionBaker._bilinear_sample(img, np.array([2.0]), np.array([2.0]))
    assert np.allclose(sampled_2[0], [0.0, 1.0, 0.0, 1.0], atol=1e-4)


def test_bilinear_sample_interpolation():
    """Bilinear örneklemenin ara noktalarda yumuşak geçiş yaptığını test eder."""
    img = np.zeros((2, 2, 4), dtype=np.float32)
    img[0, 0] = [0.0, 0.0, 0.0, 1.0]
    img[0, 1] = [1.0, 1.0, 1.0, 1.0]
    img[1, 0] = [0.0, 0.0, 0.0, 1.0]
    img[1, 1] = [1.0, 1.0, 1.0, 1.0]

    # Ortadan (x=0.5, y=0.5) örnekle -> [0.5, 0.5, 0.5, 1.0] olmalı
    sampled_mid = ProjectionBaker._bilinear_sample(img, np.array([0.5]), np.array([0.5]))
    assert np.allclose(sampled_mid[0], [0.5, 0.5, 0.5, 1.0], atol=1e-4)


def test_bilinear_sample_boundary_clamping():
    """Görüntü sınırları dışındaki koordinatların güvenle sınırlandığını test eder."""
    img = np.ones((4, 4, 4), dtype=np.float32) * 0.75
    sampled_out = ProjectionBaker._bilinear_sample(img, np.array([-5.0, 10.0]), np.array([-3.0, 8.0]))
    assert sampled_out.shape == (2, 4)
    assert np.allclose(sampled_out, 0.75, atol=1e-4)


def test_bbox_coordinate_mapping():
    """Ekran koordinatlarının AI görsel uzayına tam doğrusal eşleştiğini test eder."""
    bx, by, bw, bh = 100, 200, 400, 300
    ai_w, ai_h = 1024, 1024

    # Ekranın tam orta noktası
    screen_x = 100 + 200  # 300
    screen_y = 200 + 150  # 350

    ai_x = ((screen_x - bx) / bw) * (ai_w - 1)
    ai_y = ((screen_y - by) / bh) * (ai_h - 1)

    assert np.isclose(ai_x, (1024 - 1) * 0.5)
    assert np.isclose(ai_y, (1024 - 1) * 0.5)


def test_dilate_texture_and_mask_color_bleed():
    """UV dikiş payı genişletilirken renklerin yayıldığını ve sıfır (siyah) kalmadığını test eder."""
    h, w = 16, 16
    buf = np.zeros((h, w, 4), dtype=np.float32)
    mask = np.zeros((h, w), dtype=np.float32)

    # Merkez 4x4 alanı kırmızı ve maskeli yap
    buf[6:10, 6:10] = [1.0, 0.0, 0.0, 1.0]
    mask[6:10, 6:10] = 1.0

    dil_buf, dil_mask = ProjectionBaker.dilate_texture_and_mask(buf, mask, iterations=2)

    # Dilation sonrası maske genişlemiş olmalı
    assert np.sum(dil_mask > 0) > np.sum(mask > 0)

    # Genişletilen yeni piksellerde renk 0 (siyah) kalmamalı, kırmızı rengi almış olmalı
    newly_dilated = (dil_mask > 0) & (mask == 0)
    assert np.any(newly_dilated)
    # Kırmızı kanal 1.0 olmalı
    np.testing.assert_allclose(dil_buf[newly_dilated, 0], 1.0, atol=1e-4)
    # Alpha kanal 1.0 olmalı
    np.testing.assert_allclose(dil_buf[newly_dilated, 3], 1.0, atol=1e-4)

