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

    @staticmethod
    def connect_normal_map_to_material(obj: bpy.types.Object, normal_image: bpy.types.Image, strength: float = 1.0) -> bool:
        """Normal Map görselini aktif materyalin Principled BSDF node'una Tangent Space Normal Map ile bağlar."""
        if not obj or not getattr(obj, "active_material", None):
            return False

        mat = obj.active_material
        if not mat.use_nodes:
            mat.use_nodes = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # 1. Renk uzayını DAİMA 'Non-Color' yap
        try:
            normal_image.colorspace_settings.name = 'Non-Color'
        except Exception:
            pass

        # 2. Principled BSDF node'unu bul veya oluştur
        principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not principled:
            principled = nodes.new(type='ShaderNodeBsdfPrincipled')
            principled.location = (0, 0)
            # Material Output'a bağla
            output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
            if not output_node:
                output_node = nodes.new(type='ShaderNodeOutputMaterial')
                output_node.location = (300, 0)
            links.new(principled.outputs.get("BSDF"), output_node.inputs.get("Surface"))

        px, py = principled.location.x, principled.location.y

        # 3. Normal Map node'u bul veya oluştur
        normal_map_node = None
        for n in nodes:
            if n.type == 'NORMAL_MAP':
                normal_map_node = n
                break

        if not normal_map_node:
            normal_map_node = nodes.new(type='ShaderNodeNormalMap')
            normal_map_node.space = 'TANGENT'
            normal_map_node.location = (px - 250, py - 350)

        normal_map_node.inputs["Strength"].default_value = strength

        # 4. Image Texture node'u bul veya oluştur
        tex_node = None
        for link in normal_map_node.inputs["Color"].links:
            if link.from_node.type == 'TEX_IMAGE':
                tex_node = link.from_node
                break

        if not tex_node:
            tex_node = nodes.new(type='ShaderNodeTexImage')
            tex_node.location = (px - 550, py - 350)
            tex_node.label = "AI Normal Map"

        tex_node.image = normal_image

        # 5. Bağlantıları kur: TexImage -> NormalMap -> Principled
        links.new(tex_node.outputs.get("Color"), normal_map_node.inputs.get("Color"))
        links.new(normal_map_node.outputs.get("Normal"), principled.inputs.get("Normal"))

        logger.info("Connected Normal Map to material shader nodes", material=mat.name, image=normal_image.name)
        return True

    @staticmethod
    def connect_roughness_map_to_material(obj: bpy.types.Object, roughness_image: bpy.types.Image) -> bool:
        """Roughness görselini aktif materyalin Principled BSDF Roughness soketine bağlar."""
        if not obj or not getattr(obj, "active_material", None):
            return False

        mat = obj.active_material
        if not mat.use_nodes:
            mat.use_nodes = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # 1. Renk uzayını 'Non-Color' yap
        try:
            roughness_image.colorspace_settings.name = 'Non-Color'
        except Exception:
            pass

        # 2. Principled BSDF'i bul
        principled = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not principled:
            principled = nodes.new(type='ShaderNodeBsdfPrincipled')
            principled.location = (0, 0)

        px, py = principled.location.x, principled.location.y

        # 3. Image Texture node'u bul veya oluştur
        tex_node = None
        rough_sock = principled.inputs.get("Roughness")
        if rough_sock and rough_sock.is_linked:
            for link in rough_sock.links:
                if link.from_node.type == 'TEX_IMAGE':
                    tex_node = link.from_node
                    break

        if not tex_node:
            tex_node = nodes.new(type='ShaderNodeTexImage')
            tex_node.location = (px - 400, py - 100)
            tex_node.label = "AI Roughness Map"

        tex_node.image = roughness_image

        # 4. Bağlantıyı kur: TexImage.Color -> Principled.Roughness
        if rough_sock:
            links.new(tex_node.outputs.get("Color"), rough_sock)

        logger.info("Connected Roughness Map to material shader nodes", material=mat.name, image=roughness_image.name)
        return True

    @staticmethod
    def force_viewport_redraw() -> None:
        """3D Viewport ve Image Editor alanlarının ekranını anında tazeler."""
        wm = getattr(bpy.context, "window_manager", None)
        if wm:
            for window in getattr(wm, "windows", []):
                for area in getattr(window.screen, "areas", []):
                    if area.type in {'VIEW_3D', 'IMAGE_EDITOR', 'NODE_EDITOR'}:
                        area.tag_redraw()
