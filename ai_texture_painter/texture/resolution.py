# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Resolution Manager.

Texture ve AI generation çözünürlüklerini yönetir.
Maskeli alanın sınırlarını (bounding box) hesaplar, kırpar (crop),
boyutlandırır (resize) ve tam konumuna yerleştirir (place).
"""

from typing import Tuple
import numpy as np

from ..core.logging import get_logger

logger = get_logger("texture.resolution")


class ResolutionManager:
    """Çözünürlük, kırpma ve bölge konumlandırma yöneticisi."""

    # AI modellerinin desteklediği standart çözünürlükler
    SUPPORTED_SIZES = (512, 768, 1024, 1536, 2048)

    @staticmethod
    def get_mask_bounding_box(
        mask: np.ndarray, padding: int = 16
    ) -> Tuple[int, int, int, int]:
        """Maskeli alanın piksel koordinatlarındaki (x, y, w, h) bounding box'ını hesaplar.

        Args:
            mask: (H, W) float32 maske
            padding: Sınırların dışına eklenecek piksel payı

        Returns:
            (x, y, width, height) tuple
        """
        h, w = mask.shape[:2]
        active = mask > 0.01

        rows = np.any(active, axis=1)
        cols = np.any(active, axis=0)

        # Eğer hiç maskeli piksel yoksa tüm görüntüyü kapsa
        if not np.any(rows) or not np.any(cols):
            return (0, 0, w, h)

        row_indices = np.where(rows)[0]
        col_indices = np.where(cols)[0]

        rmin, rmax = int(row_indices[0]), int(row_indices[-1])
        cmin, cmax = int(col_indices[0]), int(col_indices[-1])

        # Padding ekle ve görüntü sınırları içinde tut
        rmin = max(0, rmin - padding)
        rmax = min(h - 1, rmax + padding)
        cmin = max(0, cmin - padding)
        cmax = min(w - 1, cmax + padding)

        box_w = max(1, cmax - cmin + 1)
        box_h = max(1, rmax - rmin + 1)

        return (cmin, rmin, box_w, box_h)

    @staticmethod
    def find_best_generation_size(
        region_w: int, region_h: int
    ) -> Tuple[int, int]:
        """Bölge ölçülerine en uygun AI üretim boyutunu belirler."""
        max_dim = max(region_w, region_h)
        for size in ResolutionManager.SUPPORTED_SIZES:
            if size >= max_dim:
                return (size, size)
        return (ResolutionManager.SUPPORTED_SIZES[-1], ResolutionManager.SUPPORTED_SIZES[-1])

    @staticmethod
    def crop_region(
        image: np.ndarray, bbox: Tuple[int, int, int, int]
    ) -> np.ndarray:
        """Verilen bounding box (x, y, w, h) alanını kırpar."""
        x, y, w, h = bbox
        return image[y : y + h, x : x + w].copy()

    @staticmethod
    def place_region(
        target: np.ndarray,
        region: np.ndarray,
        bbox: Tuple[int, int, int, int],
    ) -> np.ndarray:
        """Kırpılmış veya üretilmiş bölgeyi hedef imajın tam konumuna yerleştirir."""
        x, y, w, h = bbox
        result = target.copy()

        # Boyut uyuşmazlığı varsa bölgeyi (h, w) boyutuna resize et
        if region.shape[0] != h or region.shape[1] != w:
            region_resized = ResolutionManager.resize_image(region, w, h)
        else:
            region_resized = region

        result[y : y + h, x : x + w] = region_resized
        return result

    @staticmethod
    def resize_image(image: np.ndarray, new_w: int, new_h: int) -> np.ndarray:
        """Saf NumPy ile standart çift doğrusal (bilinear) interpolasyon ile görseli yeniden boyutlandırır.

        Args:
            image: (H, W, C) veya (H, W) float32 dizi
            new_w: Yeni genişlik
            new_h: Yeni yükseklik

        Returns:
            (new_h, new_w, C) boyutlandırılmış dizi
        """
        old_h, old_w = image.shape[:2]
        if old_h == new_h and old_w == new_w:
            return image.copy()

        # Koordinat ızgarası oluştur
        y = np.linspace(0, old_h - 1, new_h)
        x = np.linspace(0, old_w - 1, new_w)

        x_grid, y_grid = np.meshgrid(x, y)

        x0 = np.floor(x_grid).astype(np.int32)
        x1 = np.clip(x0 + 1, 0, old_w - 1)
        y0 = np.floor(y_grid).astype(np.int32)
        y1 = np.clip(y0 + 1, 0, old_h - 1)

        dx = x_grid - x0
        dy = y_grid - y0

        w00 = (1.0 - dx) * (1.0 - dy)
        w01 = (1.0 - dx) * dy
        w10 = dx * (1.0 - dy)
        w11 = dx * dy

        if image.ndim == 3:
            w00 = w00[..., np.newaxis]
            w01 = w01[..., np.newaxis]
            w10 = w10[..., np.newaxis]
            w11 = w11[..., np.newaxis]

        interpolated = (
            w00 * image[y0, x0]
            + w01 * image[y1, x0]
            + w10 * image[y0, x1]
            + w11 * image[y1, x1]
        )

        return interpolated.astype(image.dtype)
