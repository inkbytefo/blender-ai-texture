# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Blender UV Adapter.

Mesh UV layer verilerini, bmesh loop koordinatlarını, seçili face'lerin
UV bounding box ve koordinatlarını çıkarır ve seçili yüzeylerden 2D piksel maskesi üretir.
"""

from typing import Optional, List, Tuple
import numpy as np
import bpy
import bmesh

from ..core.logging import get_logger

logger = get_logger("blender.uv_adapter")


class BlenderUVAdapter:
    """Blender UV ve Mesh API adapter katmanı."""

    @staticmethod
    def get_active_uv_layer_name(obj: bpy.types.Object) -> Optional[str]:
        """Mesh üzerindeki aktif UV katmanının adını döndürür."""
        if obj and obj.type == 'MESH' and obj.data.uv_layers:
            active_layer = obj.data.uv_layers.active
            return active_layer.name if active_layer else obj.data.uv_layers[0].name
        return None

    @staticmethod
    def get_selected_faces_uvs(
        obj: bpy.types.Object,
    ) -> List[List[Tuple[float, float]]]:
        """Seçili yüzeylerin (faces) UV koordinat listelerini döndürür."""
        if not obj or obj.type != 'MESH':
            return []

        me = obj.data
        bm = bmesh.new()

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(me)
        else:
            bm.from_mesh(me)

        bm.faces.ensure_lookup_table()
        uv_layer = bm.loops.layers.uv.active

        if not uv_layer:
            if obj.mode != 'EDIT':
                bm.free()
            return []

        selected_uvs = []
        for face in bm.faces:
            if face.select:
                face_uvs = [(loop[uv_layer].uv.x, loop[uv_layer].uv.y) for loop in face.loops]
                selected_uvs.append(face_uvs)

        if obj.mode != 'EDIT':
            bm.free()

        return selected_uvs

    @staticmethod
    def get_uv_bounding_box(
        selected_uvs: List[List[Tuple[float, float]]],
    ) -> Optional[Tuple[float, float, float, float]]:
        """Seçili UV'lerin (u_min, v_min, u_max, v_max) sınırlarını hesaplar."""
        if not selected_uvs:
            return None

        all_u = [u for face in selected_uvs for u, _ in face]
        all_v = [v for face in selected_uvs for _, v in face]

        if not all_u or not all_v:
            return None

        return (
            max(0.0, min(all_u)),
            max(0.0, min(all_v)),
            min(1.0, max(all_u)),
            min(1.0, max(all_v)),
        )

    @staticmethod
    def _rasterize_triangle(
        v0: Tuple[float, float],
        v1: Tuple[float, float],
        v2: Tuple[float, float],
        width: int,
        height: int,
        mask: np.ndarray,
    ) -> None:
        """Barycentric koordinatlarıyla tek bir 2D üçgeni maske matrisine rasterize eder."""
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

        # 0.5 piksel tolerans ile üçgen içi noktaları bul
        inside = (w1 >= -0.001) & (w2 >= -0.001) & (w3 >= -0.001)
        mask[min_y : max_y + 1, min_x : max_x + 1] |= inside

    @classmethod
    def create_mask_from_uv_selection(
        cls,
        obj: bpy.types.Object,
        width: int,
        height: int,
        bleed_pixels: int = 2,
    ) -> Optional[Tuple[np.ndarray, int]]:
        """Seçili yüzeylerin UV poligonlarını (H, W) piksel maskesine rasterize eder.

        Args:
            obj: Aktif Blender Mesh nesnesi
            width: Hedef doku genişliği (W)
            height: Hedef doku yüksekliği (H)
            bleed_pixels: UV dikiş çizgilerini önlemek için dikiş payı (genişletme pikseli)

        Returns:
            (mask_float32, face_count) veya seçili yüzey yoksa None
        """
        selected_uvs = cls.get_selected_faces_uvs(obj)
        if not selected_uvs:
            return None

        bool_mask = np.zeros((height, width), dtype=bool)

        for face_uvs in selected_uvs:
            if len(face_uvs) < 3:
                continue

            # UV -> Piksel koordinatı dönüşümü
            # Blender Image pikselinde (0,0) sol alt köşedir (u=0, v=0)
            pixel_pts = [
                (u * (width - 1), v * (height - 1))
                for u, v in face_uvs
            ]

            # Çokgeni (n-gon veya quad) üçgen fanına bölerek rasterize et
            p0 = pixel_pts[0]
            for i in range(1, len(pixel_pts) - 1):
                p1 = pixel_pts[i]
                p2 = pixel_pts[i + 1]
                cls._rasterize_triangle(p0, p1, p2, width, height, bool_mask)

        mask_float = bool_mask.astype(np.float32)

        # UV dikiş payı (dilation / seam bleed)
        if bleed_pixels > 0 and np.any(mask_float > 0):
            from ..texture.mask import MaskProcessor
            mask_float = MaskProcessor.dilate_mask(mask_float, iterations=bleed_pixels)

        logger.info(
            "Created UV selection mask",
            selected_faces=len(selected_uvs),
            active_pixels=int(np.sum(mask_float > 0)),
        )

        return mask_float, len(selected_uvs)
