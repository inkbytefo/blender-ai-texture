# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""Tests for IslandPacker round-trip unpacking and inverse compositing."""

import pytest
import numpy as np
from ai_texture_painter.blender.selection_group import UVIsland
from ai_texture_painter.texture.island_packer import IslandPacker


def test_roundtrip_pack_unpack_compositing():
    """Test that generated artwork on temporary canvas is mapped back to original UVs without leaking to non-selected areas."""
    base_h, base_w = 256, 256
    # Base image: Solid Gray [0.5, 0.5, 0.5, 1.0]
    base_image = np.full((base_h, base_w, 4), 0.5, dtype=np.float32)

    # Island 1: at ~ (0.1..0.3, 0.1..0.3)
    isl1 = UVIsland(
        island_id=0,
        face_indices=[0],
        uv_loops=[[(0.1, 0.1), (0.3, 0.1), (0.3, 0.3), (0.1, 0.3)]],
        uv_bbox=(0.1, 0.1, 0.3, 0.3),
    )

    # Island 2: at ~ (0.7..0.9, 0.7..0.9)
    isl2 = UVIsland(
        island_id=1,
        face_indices=[1],
        uv_loops=[[(0.7, 0.7), (0.9, 0.7), (0.9, 0.9), (0.7, 0.9)]],
        uv_bbox=(0.7, 0.7, 0.9, 0.9),
    )

    canvas, mask, manifest = IslandPacker.pack_islands(
        base_image=base_image,
        islands=[isl1, isl2],
        target_canvas_size=(256, 256),
        padding=4,
        bleed_pixels=0,
    )

    # Simulate AI output on the canvas: Solid Bright Red [1.0, 0.0, 0.0, 1.0]
    ai_generated_canvas = np.zeros_like(canvas)
    ai_generated_canvas[:, :, 0] = 1.0  # Red
    ai_generated_canvas[:, :, 3] = 1.0  # Alpha

    # Unpack and composite back onto base image
    result = IslandPacker.unpack_and_composite(
        packed_generated=ai_generated_canvas,
        manifest=manifest,
        original_base=base_image,
        feather_radius=0,
    )

    assert result.shape == (base_h, base_w, 4)

    # 1. Check that the center of Island 1 is painted Red
    # UV (0.2, 0.2) -> pixel (y ~ 51, x ~ 51)
    y1, x1 = int(0.2 * base_h), int(0.2 * base_w)
    assert result[y1, x1, 0] > 0.9  # Red channel active
    assert result[y1, x1, 1] < 0.1  # Green channel 0

    # 2. Check that the center of Island 2 is painted Red
    # UV (0.8, 0.8) -> pixel (y ~ 204, x ~ 204)
    y2, x2 = int(0.8 * base_h), int(0.8 * base_w)
    assert result[y2, x2, 0] > 0.9
    assert result[y2, x2, 1] < 0.1

    # 3. CRITICAL: Check that the unselected center area (0.5, 0.5) is UNTOUCHED (remains 0.5 gray)
    y_mid, x_mid = int(0.5 * base_h), int(0.5 * base_w)
    assert pytest.approx(result[y_mid, x_mid, 0], 1e-3) == 0.5
    assert pytest.approx(result[y_mid, x_mid, 1], 1e-3) == 0.5
    assert pytest.approx(result[y_mid, x_mid, 2], 1e-3) == 0.5
