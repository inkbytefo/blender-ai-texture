# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Blender Material Adapter.

Materyal node ağacını denetler, Base Color ve diğer PBR doku
girdilerini tespit eder ve viewport tazelemesini yönetir.
"""

from typing import Optional
import bpy

from ..core.logging import get_logger

logger = get_logger("blender.material_adapter")


class BlenderMaterialAdapter:
    """Materyal ve Shader Node ağacı için adapter katmanı."""

    @staticmethod
    def get_base_color_image(obj: bpy.types.Object) -> Optional[bpy.types.Image]:
        """Objenin aktif materyalinde Base Color'a bağlı olan Image Texture görselini bulur."""
        if not obj or not obj.active_material or not obj.active_material.use_nodes:
            return None

        nodes = obj.active_material.node_tree.nodes
        # Principled BSDF node'unu bul
        principled = None
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled = node
                break

        if not principled:
            return None

        # Base Color soketine bağlı bağlantıyı bul
        base_color_socket = principled.inputs.get("Base Color")
        if base_color_socket and base_color_socket.is_linked:
            for link in base_color_socket.links:
                from_node = link.from_node
                if from_node.type == 'TEX_IMAGE' and from_node.image:
                    return from_node.image

        return None

    @staticmethod
    def force_viewport_redraw() -> None:
        """3D Viewport ve Image Editor alanlarının ekranını anında tazeler."""
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type in {'VIEW_3D', 'IMAGE_EDITOR', 'NODE_EDITOR'}:
                    area.tag_redraw()
