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
        """Objenin aktif materyalinde Base Color / Albedo / Diffuse dokusunu bulur."""
        if not obj or not getattr(obj, "active_material", None) or not getattr(obj.active_material, "use_nodes", False):
            return None

        node_tree = getattr(obj.active_material, "node_tree", None)
        if not node_tree:
            return None

        nodes = node_tree.nodes

        # 1. Principled BSDF -> Base Color soketine bağlı TEX_IMAGE
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                base_color_socket = node.inputs.get("Base Color")
                if base_color_socket and base_color_socket.is_linked:
                    for link in base_color_socket.links:
                        from_node = link.from_node
                        if from_node.type == 'TEX_IMAGE' and from_node.image:
                            return from_node.image
                        # Eğer bir Mix/Color node'u üzerinden bağlıysa bir adım daha geriye git
                        if hasattr(from_node, "inputs"):
                            for inp in from_node.inputs:
                                if inp.is_linked:
                                    for sub_link in inp.links:
                                        if sub_link.from_node.type == 'TEX_IMAGE' and sub_link.from_node.image:
                                            return sub_link.from_node.image

        # 2. İsmi veya etiketinde color/diffuse/albedo/base geçen Image Texture node'ları (Roughness/Normal hariç)
        keywords = ("base", "color", "albedo", "diffuse", "col", "d")
        for node in nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                img_name = node.image.name.lower()
                node_name = (node.name + " " + getattr(node, "label", "")).lower()
                # Roughness / Normal / Metallic / Specular / Height olanları atla
                if any(bad in img_name or bad in node_name for bad in ("rough", "norm", "metal", "spec", "height", "disp", "ao", "occ", "mask")):
                    continue
                if any(kw in img_name or kw in node_name for kw in keywords):
                    return node.image

        # 3. Seçili (Active/Selected) TEX_IMAGE node'u
        for node in nodes:
            if node.type == 'TEX_IMAGE' and getattr(node, "select", False) and node.image:
                return node.image

        # 4. İlk bulunan (Roughness/Normal olmayan) TEX_IMAGE node'u
        for node in nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                img_name = node.image.name.lower()
                if not any(bad in img_name for bad in ("rough", "norm", "metal", "spec", "disp", "ao")):
                    return node.image

        # 5. Herhangi bir TEX_IMAGE node'u
        for node in nodes:
            if node.type == 'TEX_IMAGE' and node.image:
                return node.image

        return None

    @staticmethod
    def force_viewport_redraw() -> None:
        """3D Viewport ve Image Editor alanlarının ekranını anında tazeler."""
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type in {'VIEW_3D', 'IMAGE_EDITOR', 'NODE_EDITOR'}:
                    area.tag_redraw()
