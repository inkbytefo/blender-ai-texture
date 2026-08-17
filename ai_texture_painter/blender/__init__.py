# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""AI Texture Painter — Blender API adapter package."""

from .image_adapter import BlenderImageAdapter
from .material_adapter import BlenderMaterialAdapter
from .uv_adapter import BlenderUVAdapter
from .selection_group import SelectionGroup, UVIsland, SelectionGroupResolver

__all__ = [
    "BlenderImageAdapter",
    "BlenderMaterialAdapter",
    "BlenderUVAdapter",
    "SelectionGroup",
    "UVIsland",
    "SelectionGroupResolver",
]
