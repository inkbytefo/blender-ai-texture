# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Blender Image Adapter.

bpy.types.Image ile NumPy array'leri arasında hızlı, güvenli
ve float32 uyumlu veri dönüşümlerini sağlar.
"""

from typing import Optional
import numpy as np
import bpy

from ..core.logging import get_logger

logger = get_logger("blender.image_adapter")


class BlenderImageAdapter:
    """Blender Image API için adapter katmanı."""

    @staticmethod
    def get_active_image(context: bpy.types.Context) -> Optional[bpy.types.Image]:
        """Context'ten veya aktif 3D materyalden boyanacak hedef dokuyu bulur.

        Öncelik:
        1. Kullanıcının panelde açıkça seçtiği target_image (eğer varsa)
        2. Aktif 3D Mesh materyalinin Base Color / Albedo dokusu (Principled BSDF)
        3. Aktif Image Editor alanı space_data.image
        4. Aktif materyaldeki diğer TEX_IMAGE dokuları
        """
        # 1. Kullanıcının açıkça seçtiği hedef doku varsa önceliklidir
        scene = getattr(context, "scene", None)
        if scene and hasattr(scene, "ai_texture"):
            tgt = getattr(scene.ai_texture, "target_image", None)
            if tgt:
                return tgt

        # 2. 3D Model / Aktif Mesh üzerinden Base Color (Albedo) dokusunu bul
        obj = getattr(context, "active_object", None)
        if obj and obj.type == 'MESH':
            from .material_adapter import BlenderMaterialAdapter
            base_col = BlenderMaterialAdapter.get_base_color_image(obj)
            if base_col:
                return base_col

        # 3. Image Editor alanındaysa space_data'dan al
        if context.space_data and context.space_data.type == 'IMAGE_EDITOR':
            if context.space_data.image:
                return context.space_data.image

        # 4. Fallback: Aktif materyaldeki diğer Image Texture node'ları
        if obj and getattr(obj, "active_material", None) and getattr(obj.active_material, "use_nodes", False):
            for node in obj.active_material.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    return node.image

        return None

    @staticmethod
    def image_to_numpy(image: bpy.types.Image) -> np.ndarray:
        """Blender Image verisini (H, W, 4) float32 RGBA NumPy dizisine dönüştürür.

        Args:
            image: bpy.types.Image nesnesi

        Returns:
            (H, W, 4) şeklinde [0.0 - 1.0] aralığında float32 NumPy array
        """
        width, height = image.size[0], image.size[1]

        # Blender Image.pixels DAİMA 4 kanallı (RGBA) float32 dizisidir
        total_pixels = width * height * 4
        pixels = np.empty(total_pixels, dtype=np.float32)
        image.pixels.foreach_get(pixels)

        # (Height, Width, 4) şeklinde yeniden şekillendir
        return pixels.reshape((height, width, 4))

    @staticmethod
    def numpy_to_image(array: np.ndarray, target_image: bpy.types.Image) -> None:
        """(H, W, 4) float32 NumPy dizisini Blender Image piksel tamponuna yazar.

        Args:
            array: (H, W, 4) float32 array
            target_image: Güncellenecek bpy.types.Image
        """
        height, width = target_image.size[1], target_image.size[0]

        # Boyut uyuşmazlığı varsa hedef imajı yeniden boyutlandır
        if array.shape[0] != height or array.shape[1] != width:
            target_image.scale(array.shape[1], array.shape[0])
            width, height = array.shape[1], array.shape[0]

        # 4 kanala uydur ve clip et
        data = np.clip(array, 0.0, 1.0).astype(np.float32)
        if data.ndim == 2:
            alpha = np.ones((height, width, 1), dtype=np.float32)
            rgb = np.repeat(data[..., np.newaxis], 3, axis=-1)
            data = np.concatenate([rgb, alpha], axis=-1)
        elif data.shape[-1] == 3:
            alpha = np.ones((height, width, 1), dtype=np.float32)
            data = np.concatenate([data, alpha], axis=-1)

        target_image.pixels.foreach_set(data.ravel())
        target_image.update()

        # Viewport texture önbelleğini temizleyerek anında yenilenmesini sağla
        try:
            target_image.gl_free()
        except AttributeError:
            pass

    @staticmethod
    def get_or_create_image(
        name: str, width: int, height: int, alpha: bool = True
    ) -> bpy.types.Image:
        """Verilen isimde imaj varsa alır, yoksa sıfırdan oluşturur."""
        img = bpy.data.images.get(name)
        if img is None:
            img = bpy.data.images.new(
                name=name,
                width=width,
                height=height,
                alpha=alpha,
                float_buffer=False,
            )
        elif img.size[0] != width or img.size[1] != height:
            img.scale(width, height)

        return img
