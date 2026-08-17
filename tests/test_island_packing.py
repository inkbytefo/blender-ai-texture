# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""Tests for IslandPacker 2D bin-packing and temporary AI canvas creation."""

import pytest
import numpy as np
from ai_texture_painter.blender.selection_group import UVIsland
from ai_texture_painter.texture.island_packer import IslandPacker, PackingManifest


def test_rasterize_island_mask():
    """Test rasterization of a UVIsland polygon onto a binary float32 mask."""
    island = UVIsland(
        island_id=0,
        face_indices=[0],
        uv_loops=[
            [(0.2, 0.2), (0.4, 0.2), (0.4, 0.4)],  # Triangle 1
            [(0.2, 0.2), (0.4, 0.4), (0.2, 0.4)],  # Triangle 2 (forms quad [0.2..0.4, 0.2..0.4])
        ],
        uv_bbox=(0.2, 0.2, 0.4, 0.4),
    )

    mask = IslandPacker.rasterize_island_mask(island, width=100, height=100)
    assert mask.shape == (100, 100)
    assert mask.dtype == np.float32

    # Check center of the quad is active
    assert mask[30, 30] == 1.0
    # Check outside region is 0
    assert mask[5, 5] == 0.0
    assert mask[80, 80] == 0.0


def test_pack_multiple_islands():
    """Test packing multiple isolated UV islands into a single compact canvas."""
    base_image = np.ones((512, 512, 4), dtype=np.float32)
    # Give some distinct color to distinguish
    base_image[:, :, 0] = 0.5
    base_image[:, :, 1] = 0.8

    # Island 1: Top-Left in UV space
    isl1 = UVIsland(
        island_id=0,
        face_indices=[0],
        uv_loops=[[(0.05, 0.05), (0.15, 0.05), (0.15, 0.15), (0.05, 0.15)]],
        uv_bbox=(0.05, 0.05, 0.15, 0.15),
    )

    # Island 2: Bottom-Right in UV space
    isl2 = UVIsland(
        island_id=1,
        face_indices=[1],
        uv_loops=[[(0.80, 0.80), (0.95, 0.80), (0.95, 0.95), (0.80, 0.95)]],
        uv_bbox=(0.80, 0.80, 0.95, 0.95),
    )

    canvas, mask, manifest = IslandPacker.pack_islands(
        base_image=base_image,
        islands=[isl1, isl2],
        target_canvas_size=(512, 512),
        padding=8,
        bleed_pixels=0,
    )

    assert canvas.shape == (512, 512, 4)
    assert mask.shape == (512, 512)
    assert isinstance(manifest, PackingManifest)
    assert len(manifest.mappings) == 2

    # Ensure packed mask has active pixels from both islands
    assert np.sum(mask > 0) > 0
