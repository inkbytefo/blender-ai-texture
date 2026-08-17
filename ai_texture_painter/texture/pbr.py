# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
PBR Texture Generator Module.

Saf NumPy kullanarak harici kütüphane bağımlılığı olmadan
Base Color dokusundan yüksek kaliteli Tangent-Space Normal Map (OpenGL standardı),
Roughness ve Height haritaları türetir.
"""

from typing import Optional
import numpy as np

from ..core.logging import get_logger

logger = get_logger("texture.pbr")


class PBRGenerator:
    """Saf NumPy ile PBR doku haritaları (Normal, Roughness, Height) üretim motoru."""

    @staticmethod
    def generate_height_map(
        rgb_image: np.ndarray,
        invert: bool = False,
        contrast: float = 1.0,
    ) -> np.ndarray:
        """Base Color görselinden standart fotometrik luma ağırlıklarıyla (H, W) Height Map üretir.

        Args:
            rgb_image: (H, W, 3) veya (H, W, 4) float32 [0.0 - 1.0] dizi
            invert: Yükseklik değerlerini tersle
            contrast: Kontrast çarpanı (1.0 = normal)

        Returns:
            (H, W) float32 [0.0 - 1.0] yükseklik haritası
        """
        arr = np.asarray(rgb_image, dtype=np.float32)
        if arr.ndim == 3 and arr.shape[-1] >= 3:
            # Standart Rec.709 Luma dönüşümü (0.2126 R + 0.7152 G + 0.0722 B)
            height = 0.2126 * arr[..., 0] + 0.7152 * arr[..., 1] + 0.0722 * arr[..., 2]
        elif arr.ndim == 2:
            height = arr.copy()
        else:
            height = arr[..., 0].copy()

        # Kontrast ayarı
        if contrast != 1.0:
            mean = np.mean(height)
            height = (height - mean) * contrast + mean

        height = np.clip(height, 0.0, 1.0)
        if invert:
            height = 1.0 - height

        return height.astype(np.float32)

    @staticmethod
    def generate_normal_map(
        source_image: np.ndarray,
        strength: float = 1.5,
        flip_y: bool = False,
    ) -> np.ndarray:
        """Görselden Sobel türev filtreleri ile Tangent-Space Normal Map (OpenGL RGBA) üretir.

        R: X ekseni sapması [0..1] (0.5 = düz)
        G: Y ekseni sapması [0..1] (0.5 = düz, Blender OpenGL standardı)
        B: Z ekseni (yüzey normali, genellikle 0.5..1.0 arası)
        A: 1.0 (opak)

        Args:
            source_image: (H, W, 4) veya (H, W) Base Color ya da Height haritası
            strength: Kabartma/derinlik gücü çarpanı (0.1 - 5.0)
            flip_y: DirectX vs OpenGL yeşil kanal yönelimi

        Returns:
            (H, W, 4) float32 [0.0 - 1.0] Tangent-Space Normal Map
        """
        # 1. Height map'e dönüştür
        if source_image.ndim == 3:
            h_map = PBRGenerator.generate_height_map(source_image)
        else:
            h_map = np.clip(source_image, 0.0, 1.0).astype(np.float32)

        h, w = h_map.shape[:2]

        # 2. Kenar taşmalarını önlemek için yansıtma dolgusu (pad with edge reflection)
        pad = np.pad(h_map, 1, mode='edge')

        # 3. Sobel Gradyan Filtreleri (X ve Y türevleri)
        # dx: [-1 0 1; -2 0 2; -1 0 1] / 8.0
        # dy: [-1 -2 -1; 0 0 0; 1 2 1] / 8.0
        dx = (
            (pad[:-2, 2:] + 2.0 * pad[1:-1, 2:] + pad[2:, 2:])
            - (pad[:-2, :-2] + 2.0 * pad[1:-1, :-2] + pad[2:, :-2])
        ) / 8.0

        dy = (
            (pad[2:, :-2] + 2.0 * pad[2:, 1:-1] + pad[2:, 2:])
            - (pad[:-2, :-2] + 2.0 * pad[:-2, 1:-1] + pad[:-2, 2:])
        ) / 8.0

        # Güç ölçekleme
        dx = dx * float(strength)
        dy = dy * float(strength)

        if flip_y:
            dy = -dy

        # 4. Yüzey normal vektörlerini oluştur: N = (-dx, -dy, 1.0)
        nz = np.ones_like(dx, dtype=np.float32)
        nx = -dx
        ny = -dy

        # Vektör normunu hesapla: length = sqrt(nx^2 + ny^2 + nz^2)
        length = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
        length = np.maximum(length, 1e-6)

        # Normalize et
        nx /= length
        ny /= length
        nz /= length

        # 5. [-1.0, 1.0] aralığından [0.0, 1.0] renk aralığına kodla
        r = (nx + 1.0) * 0.5
        g = (ny + 1.0) * 0.5
        b = (nz + 1.0) * 0.5
        a = np.ones((h, w), dtype=np.float32)

        normal_map = np.stack([r, g, b, a], axis=-1)
        return np.clip(normal_map, 0.0, 1.0).astype(np.float32)

    @staticmethod
    def generate_roughness_map(
        rgb_image: np.ndarray,
        invert: bool = False,
        base_roughness: float = 0.5,
        variance: float = 0.3,
    ) -> np.ndarray:
        """Base Color dokusunun parlaklık ve mikro-detaylarından Roughness haritası üretir.

        Args:
            rgb_image: (H, W, 4) float32 dizi
            invert: Tersle (Smoothness / Glossiness modu)
            base_roughness: Ortalama pürüzlülük (0.0 = ayna, 1.0 = mat)
            variance: Detay varyasyon genliği

        Returns:
            (H, W, 4) float32 Grayscale RGBA Roughness Map
        """
        luma = PBRGenerator.generate_height_map(rgb_image)
        mean_luma = np.mean(luma)

        # Detay dalgalanması
        diff = luma - mean_luma
        roughness = base_roughness + (diff * variance)

        if invert:
            roughness = 1.0 - roughness

        roughness = np.clip(roughness, 0.0, 1.0).astype(np.float32)

        # RGBA grayscale olarak paketle
        h, w = roughness.shape[:2]
        r = roughness
        g = roughness
        b = roughness
        a = np.ones((h, w), dtype=np.float32)

        return np.stack([r, g, b, a], axis=-1)
