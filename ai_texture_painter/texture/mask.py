# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Mask Processing Module.

Texture maskeleme, UV seçimi rasterizasyonu, grayscale normalizasyonu,
kenar yumuşatma (feather), thresholding ve morfolojik operasyonları yürütür.
"""

import numpy as np
from typing import Optional, Tuple
import bpy

from ..core.logging import get_logger
from ..blender.image_adapter import BlenderImageAdapter

logger = get_logger("texture.mask")


class MaskProcessor:
    """Maske verisi oluşturma, normalize etme ve işleme motoru."""

    @staticmethod
    def normalize_mask(raw_mask: np.ndarray) -> np.ndarray:
        """Herhangi bir maske verisini (H, W) tek kanallı float32 [0.0 - 1.0] standardına dönüştürür."""
        arr = np.asarray(raw_mask, dtype=np.float32)

        if np.max(arr) > 1.0:
            arr = arr / 255.0

        if arr.ndim == 3:
            if arr.shape[-1] >= 3:
                arr = 0.299 * arr[..., 0] + 0.587 * arr[..., 1] + 0.114 * arr[..., 2]
            else:
                arr = arr[..., 0]

        return np.clip(arr, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def apply_feather(mask: np.ndarray, radius: int) -> np.ndarray:
        """Saf NumPy ile ayrıştırılabilir (separable) 2D Gaussian blur uygulayarak feathering yapar."""
        if radius <= 0:
            return mask.copy()

        sigma = max(0.5, radius / 2.0)
        kernel_size = 2 * radius + 1
        x = np.linspace(-radius, radius, kernel_size)
        kernel = np.exp(-0.5 * (x / sigma) ** 2)
        kernel /= kernel.sum()

        # Yatay konvolüsyon
        blurred = np.empty_like(mask, dtype=np.float32)
        pad_width = radius
        padded = np.pad(mask, ((0, 0), (pad_width, pad_width)), mode='edge')
        for i in range(kernel_size):
            if i == 0:
                blurred = padded[:, i : i + mask.shape[1]] * kernel[i]
            else:
                blurred += padded[:, i : i + mask.shape[1]] * kernel[i]

        # Dikey konvolüsyon
        final = np.empty_like(blurred, dtype=np.float32)
        padded_v = np.pad(blurred, ((pad_width, pad_width), (0, 0)), mode='edge')
        for i in range(kernel_size):
            if i == 0:
                final = padded_v[i : i + mask.shape[0], :] * kernel[i]
            else:
                final += padded_v[i : i + mask.shape[0], :] * kernel[i]

        return np.clip(final, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def invert_mask(mask: np.ndarray) -> np.ndarray:
        """Maskeyi tersler (0.0 <-> 1.0)."""
        return 1.0 - np.clip(mask, 0.0, 1.0)

    @staticmethod
    def threshold_mask(mask: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Maskeyi ikili (binary) 0.0 veya 1.0 değerine indirger."""
        return (mask >= threshold).astype(np.float32)

    @staticmethod
    def dilate_mask(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
        """Saf NumPy ile maskeyi genişletir (Max pooling filter)."""
        res = mask.copy()
        for _ in range(max(1, iterations)):
            pad = np.pad(res, 1, mode='edge')
            shifts = [
                pad[:-2, :-2], pad[:-2, 1:-1], pad[:-2, 2:],
                pad[1:-1, :-2], pad[1:-1, 1:-1], pad[1:-1, 2:],
                pad[2:, :-2], pad[2:, 1:-1], pad[2:, 2:],
            ]
            res = np.maximum.reduce(shifts)
        return res.astype(np.float32)

    @staticmethod
    def erode_mask(mask: np.ndarray, iterations: int = 1) -> np.ndarray:
        """Saf NumPy ile maskeyi daraltır (Min pooling filter)."""
        res = mask.copy()
        for _ in range(max(1, iterations)):
            pad = np.pad(res, 1, mode='edge')
            shifts = [
                pad[:-2, :-2], pad[:-2, 1:-1], pad[:-2, 2:],
                pad[1:-1, :-2], pad[1:-1, 1:-1], pad[1:-1, 2:],
                pad[2:, :-2], pad[2:, 1:-1], pad[2:, 2:],
            ]
            res = np.minimum.reduce(shifts)
        return res.astype(np.float32)

    @staticmethod
    def get_mask_from_context(context: bpy.types.Context, base_image: bpy.types.Image) -> Tuple[Optional[np.ndarray], str]:
        """Context'ten akıllı maske oluşturur.

        Öncelik Sırası:
        1. 3D Model / Edit Mode seçili yüzeyler (UV Selection)
        2. Özel çizilmiş maske (_ai_mask_...)
        3. Hiçbiri yoksa (None, "None")

        Returns:
            (mask_array_or_None, mask_description_string)
        """
        w, h = base_image.size[0], base_image.size[1]

        # 1. 3D Model / UV Edit Mode seçili yüzey kontrolü
        obj = getattr(context, "active_object", None)
        if obj and obj.type == 'MESH':
            from ..blender.uv_adapter import BlenderUVAdapter
            uv_res = BlenderUVAdapter.create_mask_from_uv_selection(obj, width=w, height=h, bleed_pixels=3)
            if uv_res is not None:
                mask_arr, face_cnt = uv_res
                # Eğer yüzey seçiliyse (ve tüm yüzeyler seçili değilse)
                total_faces = len(obj.data.polygons) if obj.data else 0
                if 0 < face_cnt < total_faces:
                    return mask_arr, f"UV Selection ({face_cnt} Face{'s' if face_cnt > 1 else ''})"
                elif face_cnt >= total_faces and total_faces > 0:
                    return mask_arr, "UV All Faces"

        # 2. Özel çizilmiş maske görseli kontrolü
        mask_name = f"_ai_mask_{base_image.name}"
        mask_img = bpy.data.images.get(mask_name)
        if mask_img:
            raw = BlenderImageAdapter.image_to_numpy(mask_img)
            return MaskProcessor.normalize_mask(raw), "Custom Mask"

        return None, "None"
