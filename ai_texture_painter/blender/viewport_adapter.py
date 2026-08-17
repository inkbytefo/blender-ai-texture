# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Blender Viewport Adapter.

3D Viewport ekran yakalama, OpenGL snapshot alma, seçili yüzeylerin
dünya koordinatlarını 2D ekran koordinatlarına izdüşürme (screen-space projection)
ve normal açı/backface filtreleme işlemlerini yürütür.
"""

from typing import Optional, Tuple, List
import numpy as np
import bpy
import bmesh
from bpy_extras import view3d_utils
from mathutils import Vector

from ..core.logging import get_logger
from .image_adapter import BlenderImageAdapter

logger = get_logger("blender.viewport_adapter")


class BlenderViewportAdapter:
    """3D Viewport verisi, kamera ve ekran izdüşüm adapter katmanı."""

    @staticmethod
    def get_3d_viewport_region(context: bpy.types.Context) -> Tuple[Optional[bpy.types.Area], Optional[bpy.types.Region], Optional[bpy.types.RegionView3D]]:
        """Aktif 3D Viewport alanını, bölgesini ve 3D görünüm verisini bulur."""
        # 1. Mevcut context'ten dene
        if context.area and context.area.type == 'VIEW_3D':
            area = context.area
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            rv3d = area.spaces.active.region_3d if area.spaces.active else None
            return area, region, rv3d

        # 2. Ekrandaki ilk VIEW_3D alanını ara
        screen = getattr(context, "screen", None)
        if screen:
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    region = next((r for r in area.regions if r.type == 'WINDOW'), None)
                    rv3d = area.spaces.active.region_3d if area.spaces.active else None
                    return area, region, rv3d

        return None, None, None

    @classmethod
    def capture_viewport_image(cls, context: bpy.types.Context) -> Optional[np.ndarray]:
        """3D Viewport ekranının anlık render görüntüsünü RGBA float32 NumPy dizisi olarak yakalar."""
        area, region, rv3d = cls.get_3d_viewport_region(context)
        if not area or not region or not rv3d:
            logger.error("3D Viewport region not found for capture")
            return None

        # Geçici render ayarları ile OpenGL viewport render'ı al
        scene = context.scene
        orig_res_x = scene.render.resolution_x
        orig_res_y = scene.render.resolution_y
        orig_res_pct = scene.render.resolution_percentage

        w, h = max(64, region.width), max(64, region.height)

        try:
            temp_img_name = "__ai_viewport_snapshot__"
            if temp_img_name in bpy.data.images:
                bpy.data.images.remove(bpy.data.images[temp_img_name])

            scene.render.resolution_x = w
            scene.render.resolution_y = h
            scene.render.resolution_percentage = 100

            # OpenGL render'ı çağır
            with context.temp_override(area=area, region=region):
                bpy.ops.render.opengl(view_context=True)

            # Render sonucunu oku
            render_result = bpy.data.images.get("Render Result")
            if render_result:
                pixels = BlenderImageAdapter.image_to_numpy(render_result)
                from ..texture.resolution import ResolutionManager
                if pixels.shape[0] != h or pixels.shape[1] != w:
                    pixels = ResolutionManager.resize_image(pixels, w, h)
                logger.info("Captured viewport snapshot successfully", shape=pixels.shape)
                return pixels

            logger.warning("Render Result not found after opengl render")
            return np.ones((h, w, 4), dtype=np.float32)

        except Exception as e:
            logger.error("Failed to capture viewport", error=str(e))
            return np.ones((h, w, 4), dtype=np.float32)

        finally:
            scene.render.resolution_x = orig_res_x
            scene.render.resolution_y = orig_res_y
            scene.render.resolution_percentage = orig_res_pct

    @classmethod
    def capture_screen_selection_mask(
        cls,
        context: bpy.types.Context,
        obj: bpy.types.Object,
        width: int,
        height: int,
        cull_backfaces: bool = True,
    ) -> Tuple[np.ndarray, int]:
        """Seçili 3D yüzeyleri viewport ekran düzlemine izdüşürerek 2D ekran maskesi üretir.

        Args:
            context: Blender context
            obj: Aktif Mesh nesnesi
            width: Ekran genişliği
            height: Ekran yüksekliği
            cull_backfaces: Kameraya ters bakan yüzeyleri ele

        Returns:
            (screen_mask_float32, selected_face_count)
        """
        _, region, rv3d = cls.get_3d_viewport_region(context)
        if not region or not rv3d or not obj or obj.type != 'MESH':
            return np.ones((height, width), dtype=np.float32), 0

        me = obj.data
        bm = bmesh.new()

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(me)
        else:
            bm.from_mesh(me)

        bm.faces.ensure_lookup_table()
        matrix_world = obj.matrix_world

        # Kamera konumu ve bakış yönü (Perspective vs Orthographic)
        cam_pos = rv3d.view_matrix.inverted().translation
        cam_view_mat = rv3d.view_matrix
        view_dir = Vector((-cam_view_mat[2][0], -cam_view_mat[2][1], -cam_view_mat[2][2])).normalized()
        normal_matrix = matrix_world.inverted().transposed().to_3x3()

        selected_faces = [f for f in bm.faces if f.select]
        if not selected_faces:
            selected_faces = list(bm.faces)

        bool_mask = np.zeros((height, width), dtype=bool)
        valid_face_count = 0

        for face in selected_faces:
            face_normal_world = (normal_matrix @ face.normal).normalized()
            face_center_world = matrix_world @ face.calc_center_median()

            # Backface culling kontrolü
            if cull_backfaces:
                if rv3d.is_perspective:
                    to_cam = (cam_pos - face_center_world).normalized()
                    dot = face_normal_world.dot(to_cam)
                else:
                    dot = face_normal_world.dot(-view_dir)

                if dot <= 0.02:
                    continue

            pixel_pts = []
            for loop in face.loops:
                vert_world = matrix_world @ loop.vert.co
                p2d = view3d_utils.location_3d_to_region_2d(region, rv3d, vert_world)
                if p2d is not None:
                    pixel_pts.append((p2d.x, p2d.y))

            if len(pixel_pts) < 3:
                continue

            valid_face_count += 1

            from .uv_adapter import BlenderUVAdapter
            p0 = pixel_pts[0]
            for i in range(1, len(pixel_pts) - 1):
                p1 = pixel_pts[i]
                p2 = pixel_pts[i + 1]
                BlenderUVAdapter._rasterize_triangle(p0, p1, p2, width, height, bool_mask)

        if obj.mode != 'EDIT':
            bm.free()

        mask_float = bool_mask.astype(np.float32)

        if np.any(mask_float > 0):
            from ..texture.mask import MaskProcessor
            mask_float = MaskProcessor.dilate_mask(mask_float, iterations=2)

        logger.info(
            "Created screen selection mask",
            valid_faces=valid_face_count,
            active_pixels=int(np.sum(mask_float > 0)),
        )

        return mask_float, valid_face_count
