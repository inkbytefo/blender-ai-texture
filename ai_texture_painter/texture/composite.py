# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Texture Compositor Module.

Maske korumalı piksel birleştirme (compositing) motoru ve
korunan piksel (protected pixel) doğrulama garantisini sağlar.
"""

import numpy as np

from .mask import MaskProcessor
from ..core.logging import get_logger

logger = get_logger("texture.composite")


class TextureCompositor:
    """Mask-protected texture compositing engine."""

    @staticmethod
    def composite(
        original: np.ndarray,
        generated: np.ndarray,
        mask: np.ndarray,
    ) -> np.ndarray:
        """Maske korumalı birleştirme.

        Formül:
            result = original * (1.0 - mask) + generated * mask

        Args:
            original: (H, W, 4) float32 orijinal texture
            generated: (H, W, 4) float32 üretilen texture
            mask: (H, W) float32 [0.0 - 1.0] maske

        Returns:
            (H, W, 4) float32 birleştirilmiş görüntü
        """
        norm_mask = MaskProcessor.normalize_mask(mask)

        # Maskeyi 4 kanala genişlet (H, W, 4)
        mask_4ch = np.stack([norm_mask] * 4, axis=-1)

        # Compositing
        result = original * (1.0 - mask_4ch) + generated * mask_4ch

        return np.clip(result, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def composite_with_feather(
        original: np.ndarray,
        generated: np.ndarray,
        mask: np.ndarray,
        feather_radius: int = 5,
    ) -> np.ndarray:
        """Feather uygulanmış maske ile birleştirme yapar."""
        feathered_mask = MaskProcessor.apply_feather(mask, radius=feather_radius)
        return TextureCompositor.composite(original, generated, feathered_mask)

    @staticmethod
    def verify_protected_pixels(
        original: np.ndarray,
        result: np.ndarray,
        mask: np.ndarray,
        tolerance: float = 1e-5,
    ) -> bool:
        """Protected pixel doğrulaması.

        Mask <= tolerance olan alanlardaki orijinal piksellerin
        hiçbir şekilde bozulmadığını matematiksel olarak teyit eder.

        Args:
            original: Orijinal RGBA dizi
            result: Compositing sonrası oluşan RGBA dizi
            mask: Kullanılan maske
            tolerance: Tolerans eşiği

        Returns:
            True: Korunan pikseller eksiksiz korunmuş
            False: Korunan alanlarda piksel sapması var
        """
        norm_mask = MaskProcessor.normalize_mask(mask)
        protected_indices = norm_mask <= tolerance

        # Korunacak hiç piksel yoksa (tüm görüntü maskeliyse) geçerli say
        if not np.any(protected_indices):
            return True

        original_protected = original[protected_indices]
        result_protected = result[protected_indices]

        is_valid = np.allclose(original_protected, result_protected, atol=tolerance)

        if not is_valid:
            max_diff = np.max(np.abs(original_protected - result_protected))
            logger.error(
                "Protected pixel verification failed!",
                max_diff=float(max_diff),
            )

        return is_valid
