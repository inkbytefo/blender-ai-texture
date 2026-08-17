# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Projection Baker Engine.

3D Viewport kamera açısıyla üretilen 2D perspektifli görseli,
yüzey normalleri, açı sönümlemesi (angle falloff) ve UV barycentric interpolasyon
kullanarak modelin 2D UV doku atlasına dikişsiz şekilde aktarır (Project from View).
"""

from typing import Tuple, Optional
import numpy as np
import bpy
import bmesh
from bpy_extras import view3d_utils
from mathutils import Vector

from ..core.logging import get_logger
from ..texture.composite import TextureCompositor
from ..texture.mask import MaskProcessor

logger = get_logger("blender.projection_baker")


class ProjectionBaker:
    """2D Viewport çıktısını 3D modelin UV dokusuna geri projelendiren motor."""

    @staticmethod
    def _bilinear_sample(img: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """2D görüntüden sürekli (x, y) koordinatlarında bilinear örnekleme yapar."""
        h, w = img.shape[:2]
        x = np.clip(x, 0, w - 1)
        y = np.clip(y, 0, h - 1)

        x0 = np.floor(x).astype(np.int32)
        x1 = np.clip(x0 + 1, 0, w - 1)
        y0 = np.floor(y).astype(np.int32)
        y1 = np.clip(y0 + 1, 0, h - 1)

        wx = (x - x0)[..., np.newaxis]
        wy = (y - y0)[..., np.newaxis]

        top = img[y0, x0] * (1.0 - wx) + img[y0, x1] * wx
        bottom = img[y1, x0] * (1.0 - wx) + img[y1, x1] * wx

        return top * (1.0 - wy) + bottom * wy

    @staticmethod
    def dilate_texture_and_mask(
        buffer: np.ndarray, mask: np.ndarray, iterations: int = 3
    ) -> Tuple[np.ndarray, np.ndarray]:
        """UV dikiş çizgilerini kapatmak için maske ve renk tamponunu birlikte genişletir (Color Bleed).
        
        Sadece maskeyi genişletip rengi 0 bırakmak yerine, sınır piksellerine komşu renkleri yayar.
        """
        if iterations <= 0:
            return buffer.copy(), mask.copy()

        res_mask = mask.copy()
        res_buf = buffer.copy()

        for _ in range(iterations):
            new_mask = MaskProcessor.dilate_mask(res_mask, iterations=1)
            newly_covered = (new_mask > 0) & (res_mask == 0)

            if np.any(newly_covered):
                valid = (res_mask > 0).astype(np.float32)
                valid_pad = np.pad(valid, 1, mode='edge')

                neighbor_count = (
                    valid_pad[:-2, :-2] + valid_pad[:-2, 1:-1] + valid_pad[:-2, 2:] +
                    valid_pad[1:-1, :-2] +                        valid_pad[1:-1, 2:] +
                    valid_pad[2:, :-2] + valid_pad[2:, 1:-1] + valid_pad[2:, 2:]
                )
                neighbor_count = np.maximum(neighbor_count, 1e-5)

                for ch in range(res_buf.shape[-1]):
                    ch_pad = np.pad(res_buf[..., ch] * valid, 1, mode='edge')
                    ch_sum = (
                        ch_pad[:-2, :-2] + ch_pad[:-2, 1:-1] + ch_pad[:-2, 2:] +
                        ch_pad[1:-1, :-2] +                      ch_pad[1:-1, 2:] +
                        ch_pad[2:, :-2] + ch_pad[2:, 1:-1] + ch_pad[2:, 2:]
                    )
                    res_buf[newly_covered, ch] = (ch_sum / neighbor_count)[newly_covered]

            res_mask = new_mask

        return res_buf, res_mask

    @classmethod
    def project_view_to_uv(
        cls,
        context: bpy.types.Context,
        obj: bpy.types.Object,
        generated_viewport_img: np.ndarray,
        screen_mask: Optional[np.ndarray],
        original_texture: np.ndarray,
        screen_bbox: Optional[Tuple[int, int, int, int]] = None,
        feather_radius: int = 5,
        angle_falloff_power: float = 1.5,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Viewport çıktısını orijinal UV dokusuna yüksek çözünürlükle projekte eder ve birleştirir.

        Args:
            context: Blender Context
            obj: Aktif Mesh nesnesi
            generated_viewport_img: AI çıktısı (doğrudan yüksek çözünürlüklü veya tam ekran)
            screen_mask: (H_screen, W_screen) Ekran maskesi
            original_texture: (H_tex, W_tex, 4) Mevcut UV dokusu
            screen_bbox: AI çıktısının ekran üzerindeki (x, y, w, h) bounding box'ı
            feather_radius: Dikiş kenarı yumuşatma yarıçapı
            angle_falloff_power: Dik açılı kenarlarda esnemeyi önleyen güç faktörü

        Returns:
            (composited_texture_rgba, projected_uv_mask)
        """
        from .viewport_adapter import BlenderViewportAdapter

        _, region, rv3d = BlenderViewportAdapter.get_3d_viewport_region(context)
        if not region or not rv3d or not obj or obj.type != 'MESH':
            logger.error("Invalid context or object for projection baking")
            return original_texture.copy(), np.zeros(original_texture.shape[:2], dtype=np.float32)

        tex_h, tex_w = original_texture.shape[:2]

        me = obj.data
        bm = bmesh.new()

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(me)
        else:
            bm.from_mesh(me)

        bm.faces.ensure_lookup_table()
        uv_layer = bm.loops.layers.uv.active

        if not uv_layer:
            logger.error("Mesh does not have an active UV layer")
            if obj.mode != 'EDIT':
                bm.free()
            return original_texture.copy(), np.zeros((tex_h, tex_w), dtype=np.float32)

        matrix_world = obj.matrix_world

        # Kamera konumu ve bakış vektörü (Perspective vs Orthographic)
        cam_pos = rv3d.view_matrix.inverted().translation
        cam_view_mat = rv3d.view_matrix
        view_dir = Vector((-cam_view_mat[2][0], -cam_view_mat[2][1], -cam_view_mat[2][2])).normalized()
        normal_matrix = matrix_world.inverted().transposed().to_3x3()

        projected_buffer = np.zeros((tex_h, tex_w, 4), dtype=np.float32)
        projected_mask = np.zeros((tex_h, tex_w), dtype=np.float32)

        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            selected_faces = list(bm.faces)

        # Eğer ekran maskesi verilmemişse tamamını 1 kabul et
        if screen_mask is None:
            screen_mask_2ch = np.ones((region.height, region.width), dtype=np.float32)
        else:
            screen_mask_2ch = MaskProcessor.normalize_mask(screen_mask)

        # Derinlik sıralaması: Kameraya en yakın yüzeyleri önce işle (Front-to-back depth sorting)
        face_depth_list = []
        for face in selected_faces:
            face_center_world = matrix_world @ face.calc_center_median()
            if rv3d.is_perspective:
                dist = (face_center_world - cam_pos).length
            else:
                dist = -(face_center_world - cam_pos).dot(view_dir)
            face_depth_list.append((dist, face))

        face_depth_list.sort(key=lambda item: item[0])

        ai_h, ai_w = generated_viewport_img.shape[:2]
        has_bbox = screen_bbox is not None
        if has_bbox:
            bx, by, bw, bh = screen_bbox
            bw = max(1, bw)
            bh = max(1, bh)

        # Her yüzeyi UV üçgenlerine rasterize et
        for _, face in face_depth_list:
            face_normal_world = (normal_matrix @ face.normal).normalized()
            face_center_world = matrix_world @ face.calc_center_median()

            # Görüş açısı hesapla (cos theta)
            if rv3d.is_perspective:
                to_cam = (cam_pos - face_center_world).normalized()
                cos_theta = face_normal_world.dot(to_cam)
            else:
                cos_theta = face_normal_world.dot(-view_dir)

            # Kameraya ters bakan yüzeyleri atla (Backface culling)
            if cos_theta <= 0.01:
                continue

            # Açı sönümleme: Kameraya bakan yüzeylerde %100 tam opaklık (1.0) sağlar,
            # sadece aşırı dik açılarda (0.01 - 0.15) esnemeyi önlemek için yumuşakça sönümlenir.
            if cos_theta >= 0.15:
                angle_weight = 1.0
            else:
                angle_weight = float(np.clip((cos_theta - 0.01) / 0.14, 0.0, 1.0))

            loops = face.loops
            if len(loops) < 3:
                continue

            # Köşelerin hem ekran (x_s, y_s) hem de UV piksel (x_u, y_u) koordinatlarını al
            poly_screen_pts = []
            poly_uv_pts = []

            for loop in loops:
                vert_world = matrix_world @ loop.vert.co
                p2d = view3d_utils.location_3d_to_region_2d(region, rv3d, vert_world)
                if p2d is None:
                    break

                uv = loop[uv_layer].uv
                poly_screen_pts.append((p2d.x, p2d.y))
                # UV koordinatını piksel uzayına dönüştür (u: 0..W-1, v: 0..H-1)
                poly_uv_pts.append((uv.x * (tex_w - 1), uv.y * (tex_h - 1)))

            if len(poly_screen_pts) != len(loops):
                continue

            # N-gon poligonları üçgen fanına böl
            for i in range(1, len(loops) - 1):
                u0, v0 = poly_uv_pts[0]
                u1, v1 = poly_uv_pts[i]
                u2, v2 = poly_uv_pts[i + 1]

                sx0, sy0 = poly_screen_pts[0]
                sx1, sy1 = poly_screen_pts[i]
                sx2, sy2 = poly_screen_pts[i + 1]

                min_u = max(0, int(np.floor(min(u0, u1, u2))))
                max_u = min(tex_w - 1, int(np.ceil(max(u0, u1, u2))))
                min_v = max(0, int(np.floor(min(v0, v1, v2))))
                max_v = min(tex_h - 1, int(np.ceil(max(v0, v1, v2))))

                if min_u > max_u or min_v > max_v:
                    continue

                denom = (v1 - v2) * (u0 - u2) + (u2 - u1) * (v0 - v2)
                if abs(denom) < 1e-7:
                    continue

                xs = np.arange(min_u, max_u + 1)
                ys = np.arange(min_v, max_v + 1)
                U, V = np.meshgrid(xs, ys)

                w1 = ((v1 - v2) * (U - u2) + (u2 - u1) * (V - v2)) / denom
                w2 = ((v2 - v0) * (U - u2) + (u0 - u2) * (V - v2)) / denom
                w3 = 1.0 - w1 - w2

                inside = (w1 >= -0.01) & (w2 >= -0.01) & (w3 >= -0.01)
                if not np.any(inside):
                    continue

                # İçerideki piksellerin ekran koordinatlarını enterpole et
                screen_x = w1 * sx0 + w2 * sx1 + w3 * sx2
                screen_y = w1 * sy0 + w2 * sy1 + w3 * sy2

                valid_u = U[inside]
                valid_v = V[inside]
                valid_sx = screen_x[inside]
                valid_sy = screen_y[inside]

                # Ekran maskesini örnekle
                sampled_mask = cls._bilinear_sample(screen_mask_2ch[..., np.newaxis], valid_sx, valid_sy)[..., 0]

                # AI Görselini doğrudan en yüksek çözünürlükle örnekle
                if has_bbox:
                    valid_ai_x = ((valid_sx - bx) / bw) * (ai_w - 1)
                    valid_ai_y = ((valid_sy - by) / bh) * (ai_h - 1)
                    sampled_rgba = cls._bilinear_sample(generated_viewport_img, valid_ai_x, valid_ai_y)
                else:
                    sampled_rgba = cls._bilinear_sample(generated_viewport_img, valid_sx, valid_sy)

                final_weight = sampled_mask * angle_weight

                # Z-Buffer / Max-weight mantığı ile UV tamponuna aktar
                cur_mask = projected_mask[valid_v, valid_u]
                write_indices = final_weight > cur_mask

                if np.any(write_indices):
                    target_v = valid_v[write_indices]
                    target_u = valid_u[write_indices]
                    projected_mask[target_v, target_u] = final_weight[write_indices]
                    projected_buffer[target_v, target_u] = sampled_rgba[write_indices]

        if obj.mode != 'EDIT':
            bm.free()

        # UV Dikiş çizgilerini önlemek için renk yayılımlı seam dilation (Color Bleed)
        if np.any(projected_mask > 0):
            projected_buffer, projected_mask = cls.dilate_texture_and_mask(
                projected_buffer, projected_mask, iterations=3
            )

        # Orijinal doku ile maskeli harmanlama yap
        result_texture = TextureCompositor.composite_with_feather(
            original=original_texture,
            generated=projected_buffer,
            mask=projected_mask,
            feather_radius=feather_radius,
        )

        logger.info(
            "Completed Viewport -> UV projection bake (High-Res Direct)",
            projected_pixels=int(np.sum(projected_mask > 0)),
        )

        return result_texture, projected_mask
