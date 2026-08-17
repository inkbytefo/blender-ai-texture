# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""Tests for UV Island resolution and 3D Selection Group topology analysis."""

import pytest
import numpy as np
from unittest.mock import MagicMock
from ai_texture_painter.blender.selection_group import (
    UVIsland,
    SelectionGroup,
    SelectionGroupResolver,
)


def test_uv_island_dataclass_properties():
    """Test basic properties of UVIsland."""
    island = UVIsland(
        island_id=0,
        face_indices=[1, 2, 3],
        uv_loops=[
            [(0.1, 0.1), (0.2, 0.1), (0.2, 0.3)],
            [(0.2, 0.1), (0.3, 0.1), (0.3, 0.3)],
        ],
        uv_bbox=(0.1, 0.1, 0.3, 0.3),
        center_3d=(1.0, 2.0, 3.0),
        normal_3d=(0.0, 0.0, 1.0),
    )

    assert island.island_id == 0
    assert island.face_indices == [1, 2, 3]
    assert pytest.approx(island.width_uv, 1e-4) == 0.2
    assert pytest.approx(island.height_uv, 1e-4) == 0.2
    assert pytest.approx(island.area_uv, 1e-4) == 0.04


def test_selection_group_dataclass():
    """Test SelectionGroup properties and island counting."""
    islands = [
        UVIsland(island_id=0, face_indices=[1, 2]),
        UVIsland(island_id=1, face_indices=[3, 4, 5]),
    ]
    group = SelectionGroup(
        name="Slider",
        face_indices=[1, 2, 3, 4, 5],
        islands=islands,
        adjacency_3d={0: [1], 1: [0]},
    )

    assert group.name == "Slider"
    assert group.island_count == 2
    assert group.total_faces == 5
    assert group.adjacency_3d[0] == [1]


def test_cluster_uv_islands_disconnected():
    """Test clustering logic on mock bmesh faces that are disconnected in UV space."""
    # 2 faces sharing a 3D edge, but having different UVs (UV seam)
    face1 = MagicMock()
    face1.index = 0
    loop1_0 = MagicMock()
    loop1_0.edge.index = 10
    loop1_0.vert.index = 0
    loop1_0.link_loop_next.vert.index = 1
    loop1_0.__getitem__.return_value.uv.x = 0.1
    loop1_0.__getitem__.return_value.uv.y = 0.1
    loop1_0.link_loop_next.__getitem__.return_value.uv.x = 0.2
    loop1_0.link_loop_next.__getitem__.return_value.uv.y = 0.1
    face1.loops = [loop1_0]

    face2 = MagicMock()
    face2.index = 1
    loop2_0 = MagicMock()
    loop2_0.edge.index = 10
    loop2_0.vert.index = 0
    loop2_0.link_loop_next.vert.index = 1
    # UVs are far away (e.g. 0.8, 0.8)
    loop2_0.__getitem__.return_value.uv.x = 0.8
    loop2_0.__getitem__.return_value.uv.y = 0.8
    loop2_0.link_loop_next.__getitem__.return_value.uv.x = 0.9
    loop2_0.link_loop_next.__getitem__.return_value.uv.y = 0.8
    face2.loops = [loop2_0]

    uv_layer = MagicMock()
    clusters = SelectionGroupResolver._cluster_uv_islands([face1, face2], uv_layer)
    assert len(clusters) == 2
    assert [clusters[0][0].index, clusters[1][0].index] == [0, 1]
