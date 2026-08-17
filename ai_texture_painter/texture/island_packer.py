# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Island Packer ve Temporary AI Canvas Yöneticisi.

3D'de bitişik fakat UV haritasında birbirinden uzakta konumlanmış UV adacıklarını
(UV Islands) geçici bir AI Çalışma Tuvali'ne (Temporary AI Canvas) kompakt şekilde
yerleştirir (pack). AI üretimi sonrasında ise üretilen görseli her adacığın orijinal
UV koordinatlarına tersine dönüşümle (inverse mapping) ve dikişsiz kompozitleme ile
geri yerleştirir (unpack).
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
import numpy as np

from ..blender.selection_group import UVIsland
from .mask import MaskProcessor
from .composite import TextureCompositor
from .resolution import ResolutionManager
from ..core.logging import get_logger

logger = get_logger("texture.island_packer")


@dataclass
class IslandTransformMapping:
    """Tek bir adanın orijinal texture ile AI tuvali arasındaki konum ve ölçek eşlemesi."""

    island_id: int
    source_pixel_bbox: Tuple[int, int, int, int]  # (x_min, y_min, x_max, y_max)
    canvas_pixel_rect: Tuple[int, int, int, int]  # (dest_x_min, dest_y_min, dest_x_max, dest_y_max)
    original_crop_shape: Tuple[int, int]  # (crop_h, crop_w)
    packed_crop_shape: Tuple[int, int]  # (target_h, target_w)
    island_mask: np.ndarray  # Orijinal kırpılmış adacık maskesi (float32 [0..1])


@dataclass
class PackingManifest:
    """Geçici tuvalin tam yerleşim manifestosu ve geri dönüşüm parametreleri."""

    canvas_width: int
    canvas_height: int
    base_width: int
    base_height: int
    mappings: List[IslandTransformMapping] = field(default_factory=list)


class IslandPacker:
    """UV adacıklarını 2D bin-packing ile AI tuvaline yerleştiren ve geri açan motor."""

    @classmethod
    def rasterize_island_mask(
        cls,
        island: UVIsland,
        width: int,
        height: int,
    ) -> np.ndarray:
        """Verilen UV adacığının poligonlarını (height, width) ikili maskesine rasterize eder."""
        bool_mask = np.zeros((height, width), dtype=bool)

        for face_uvs in island.uv_loops:
            if len(face_uvs) < 3:
                continue

            pixel_pts = [
                (u * (width - 1), v * (height - 1))
                for u, v in face_uvs
            ]

            p0 = pixel_pts[0]
            for i in range(1, len(pixel_pts) - 1):
                p1 = pixel_pts[i]
                p2 = pixel_pts[i + 1]
                cls._rasterize_triangle(p0, p1, p2, width, height, bool_mask)

        return bool_mask.astype(np.float32)

    @staticmethod
    def _rasterize_triangle(
        v0: Tuple[float, float],
        v1: Tuple[float, float],
        v2: Tuple[float, float],
        width: int,
        height: int,
        mask: np.ndarray,
    ) -> None:
        """2D üçgeni barycentric koordinatlarla maskeye rasterize eder."""
        x0, y0 = v0
        x1, y1 = v1
        x2, y2 = v2

        min_x = max(0, int(np.floor(min(x0, x1, x2))))
        max_x = min(width - 1, int(np.ceil(max(x0, x1, x2))))
        min_y = max(0, int(np.floor(min(y0, y1, y2))))
        max_y = min(height - 1, int(np.ceil(max(y0, y1, y2))))

        if min_x > max_x or min_y > max_y:
            return

        denom = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(denom) < 1e-8:
            return

        xs = np.arange(min_x, max_x + 1)
        ys = np.arange(min_y, max_y + 1)
        X, Y = np.meshgrid(xs, ys)

        w1 = ((y1 - y2) * (X - x2) + (x2 - x1) * (Y - y2)) / denom
        w2 = ((y2 - y0) * (X - x2) + (x0 - x2) * (Y - y2)) / denom
        w3 = 1.0 - w1 - w2

        inside = (w1 >= -0.001) & (w2 >= -0.001) & (w3 >= -0.001)
        mask[min_y : max_y + 1, min_x : max_x + 1] |= inside

    @classmethod
    def pack_islands(
        cls,
        base_image: np.ndarray,
        islands: List[UVIsland],
        target_canvas_size: Tuple[int, int] = (1024, 1024),
        padding: int = 16,
        bleed_pixels: int = 2,
    ) -> Tuple[np.ndarray, np.ndarray, PackingManifest]:
        """Seçili UV adalarını hedef AI tuvaline paketler.

        Args:
            base_image: Orijinal texture NumPy matrisi (H, W, 4)
            islands: Ayrıştırılmış UV adacıkları listesi
            target_canvas_size: Hedef AI tuval boyutu (canvas_w, canvas_h)
            padding: Adacıklar arası güvenlik payı (piksel)
            bleed_pixels: UV dikiş çizgisi payı

        Returns:
            (packed_canvas, packed_mask, PackingManifest)
        """
        base_h, base_w = base_image.shape[:2]
        canvas_w, canvas_h = target_canvas_size

        packed_canvas = np.zeros((canvas_h, canvas_w, 4), dtype=np.float32)
        packed_mask = np.zeros((canvas_h, canvas_w), dtype=np.float32)
        manifest = PackingManifest(
            canvas_width=canvas_w,
            canvas_height=canvas_h,
            base_width=base_w,
            base_height=base_h,
            mappings=[],
        )

        if not islands:
            return packed_canvas, packed_mask, manifest

        # 1. Her ada için piksel maskesini ve kırpılmış bölgesini çıkar
        island_crops: List[Dict] = []
        total_crop_area = 0

        for isl in islands:
            full_mask = cls.rasterize_island_mask(isl, base_w, base_h)
            if bleed_pixels > 0 and np.any(full_mask > 0):
                full_mask = MaskProcessor.dilate_mask(full_mask, iterations=bleed_pixels)

            # Piksel koordinatları cinsinden bounding box
            active_y, active_x = np.where(full_mask > 0)
            if len(active_y) == 0:
                # Boş ada
                continue

            x_min = max(0, int(np.min(active_x)) - padding)
            y_min = max(0, int(np.min(active_y)) - padding)
            x_max = min(base_w, int(np.max(active_x)) + padding + 1)
            y_max = min(base_h, int(np.max(active_y)) + padding + 1)

            cropped_img = base_image[y_min:y_max, x_min:x_max].copy()
            cropped_msk = full_mask[y_min:y_max, x_min:x_max].copy()
            crop_h, crop_w = cropped_img.shape[:2]

            total_crop_area += crop_w * crop_h
            island_crops.append({
                "island": isl,
                "bbox": (x_min, y_min, x_max, y_max),
                "image": cropped_img,
                "mask": cropped_msk,
                "w": crop_w,
                "h": crop_h,
            })

        if not island_crops:
            return packed_canvas, packed_mask, manifest

        # 2. Shelf Bin Packing Algoritması
        # Adacıkları yüksekliklerine göre büyükten küçüğe sırala
        island_crops.sort(key=lambda item: item["h"], reverse=True)

        # Ölçeklendirme faktörünü hesapla (tuvale sığmasını garantilemek için)
        scale_factor = 1.0
        # Güvenlik katsayısı: tuval alanının %75'ini hedefle
        target_usable_area = (canvas_w - 2 * padding) * (canvas_h - 2 * padding) * 0.75
        if total_crop_area > target_usable_area:
            scale_factor = np.sqrt(target_usable_area / max(1.0, float(total_crop_area)))
            scale_factor = min(1.0, scale_factor)

        # Shelf Layout yerleşimi
        current_x = padding
        current_y = padding
        shelf_h = 0

        for item in island_crops:
            target_w = max(8, int(item["w"] * scale_factor))
            target_h = max(8, int(item["h"] * scale_factor))

            # Satıra sığıyor mu?
            if current_x + target_w + padding > canvas_w:
                # Yeni satıra (rafa) geç
                current_x = padding
                current_y += shelf_h + padding
                shelf_h = 0

            # Tuvalin dikey sınırını aşıyor mu?
            if current_y + target_h + padding > canvas_h:
                # Ek ölçek küçültme ile sığdır
                avail_h = max(8, canvas_h - current_y - padding)
                avail_w = max(8, canvas_w - current_x - padding)
                target_w = min(target_w, avail_w)
                target_h = min(target_h, avail_h)

            dest_x_min = current_x
            dest_y_min = current_y
            dest_x_max = current_x + target_w
            dest_y_max = current_y + target_h

            # Görseli ve maskeyi hedef boyuta yeniden ölçeklendir
            res_img = ResolutionManager.resize_image(item["image"], target_w, target_h)
            res_msk = ResolutionManager.resize_image(item["mask"], target_w, target_h)

            packed_canvas[dest_y_min:dest_y_max, dest_x_min:dest_x_max] = res_img
            packed_mask[dest_y_min:dest_y_max, dest_x_min:dest_x_max] = np.maximum(
                packed_mask[dest_y_min:dest_y_max, dest_x_min:dest_x_max],
                res_msk,
            )

            mapping = IslandTransformMapping(
                island_id=item["island"].island_id,
                source_pixel_bbox=item["bbox"],
                canvas_pixel_rect=(dest_x_min, dest_y_min, dest_x_max, dest_y_max),
                original_crop_shape=(item["h"], item["w"]),
                packed_crop_shape=(target_h, target_w),
                island_mask=item["mask"],
            )
            manifest.mappings.append(mapping)

            current_x += target_w + padding
            shelf_h = max(shelf_h, target_h)

        logger.info(
            "Packed UV islands into temporary AI canvas",
            islands=len(manifest.mappings),
            canvas_size=(canvas_w, canvas_h),
            scale=round(float(scale_factor), 3),
        )

        return packed_canvas, packed_mask, manifest

    @classmethod
    def unpack_and_composite(
        cls,
        packed_generated: np.ndarray,
        manifest: PackingManifest,
        original_base: np.ndarray,
        feather_radius: int = 4,
        blend_mode: str = "NORMAL",
        opacity: float = 1.0,
    ) -> np.ndarray:
        """AI tuvalinden üretilen görseli adacık bazlı tersine dönüştürüp orijinal UV haritasına birleştirir.

        Args:
            packed_generated: AI tarafından üretilen tam tuval görseli (canvas_h, canvas_w, 4)
            manifest: Paketleme manifestosu
            original_base: Orijinal texture matrisi (base_h, base_w, 4)
            feather_radius: Dikiş kenarı yumuşatma yarıçapı
            blend_mode: Karışım modu
            opacity: Opaklık oranı [0..1]

        Returns:
            Orijinal boyutta kompozit edilmiş sonuç texture (base_h, base_w, 4)
        """
        output = original_base.copy()

        for mapping in manifest.mappings:
            dx_min, dy_min, dx_max, dy_max = mapping.canvas_pixel_rect
            sx_min, sy_min, sx_max, sy_max = mapping.source_pixel_bbox
            orig_h, orig_w = mapping.original_crop_shape

            # 1. Tuvalden adacık çıktısını kırp
            gen_patch = packed_generated[dy_min:dy_max, dx_min:dx_max]
            if gen_patch.shape[0] == 0 or gen_patch.shape[1] == 0:
                continue

            # 2. Orijinal kırpma boyutuna geri ölçeklendir
            res_patch = ResolutionManager.resize_image(gen_patch, orig_w, orig_h)

            # 3. Orijinal kırpılmış bölgeyi al
            orig_crop = original_base[sy_min:sy_max, sx_min:sx_max].copy()

            # 4. Maske ile yumuşak geçişli (feathered) kompozitleme yap
            comp_crop = TextureCompositor.composite_with_feather(
                original=orig_crop,
                generated=res_patch,
                mask=mapping.island_mask,
                feather_radius=feather_radius,
            )

            # 5. Sonucu ana görseldeki yerine geri yerleştir
            output[sy_min:sy_max, sx_min:sx_max] = comp_crop

        logger.info(
            "Unpacked and composited islands to original UV layout",
            islands=len(manifest.mappings),
        )

        return output
