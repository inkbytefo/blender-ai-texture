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
        """Context'ten aktif Image Editor görselini veya aktif texture'ı bulur.

        Args:
            context: Blender context nesnesi

        Returns:
            bpy.types.Image veya None
        """
        # 1. Image Editor alanı içindeyse doğrudan space_data'dan al
        if context.space_data and context.space_data.type == 'IMAGE_EDITOR':
            if context.space_data.image:
                return context.space_data.image

        # 2. 3D Viewport veya Texture Paint modundaysa aktif materyalden bul
        obj = context.active_object
        if obj and obj.active_material and obj.active_material.use_nodes:
            nodes = obj.active_material.node_tree.nodes
            # Aktif seçili Image Texture node'u var mı?
            for node in nodes:
                if node.type == 'TEX_IMAGE' and node.select and node.image:
                    return node.image
            # Yoksa ilk Image Texture node'unun imajını al
            for node in nodes:
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
        channels = image.channels

        # Piksel dizisi float32 olarak (H * W * channels) uzunluğundadır
        pixels = np.empty(width * height * channels, dtype=np.float32)
        image.pixels.foreach_get(pixels)

        # (Height, Width, Channels) şeklinde yeniden şekillendir
        pixels = pixels.reshape((height, width, channels))

        # Eğer 3 kanallı (RGB) ise 4 kanala (RGBA) genişlet
        if channels == 3:
            alpha = np.ones((height, width, 1), dtype=np.float32)
            pixels = np.concatenate([pixels, alpha], axis=-1)
        elif channels == 1:
            # Grayscale ise RGBA yap
            rgb = np.repeat(pixels, 3, axis=-1)
            alpha = np.ones((height, width, 1), dtype=np.float32)
            pixels = np.concatenate([rgb, alpha], axis=-1)

        return pixels

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
        if data.shape[-1] != target_image.channels:
            if target_image.channels == 4 and data.shape[-1] == 3:
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
