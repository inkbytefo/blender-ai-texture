# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""Test configuration and Blender module mocking for offline test execution."""

import sys
from unittest.mock import MagicMock

# Eğer bpy kurulu değilse mock objesi oluşturarak testlerin çalışmasını sağla
if "bpy" not in sys.modules:
    mock_bpy = MagicMock()
    mock_bmesh = MagicMock()
    mock_bpy_extras = MagicMock()
    mock_mathutils = MagicMock()
    sys.modules["bpy"] = mock_bpy
    sys.modules["bmesh"] = mock_bmesh
    sys.modules["bpy_extras"] = mock_bpy_extras
    sys.modules["bpy_extras.view3d_utils"] = mock_bpy_extras.view3d_utils
    sys.modules["mathutils"] = mock_mathutils
