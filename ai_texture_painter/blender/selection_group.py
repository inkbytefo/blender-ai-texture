# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Selection Group ve 3D -> UV Island Resolver.

3D Viewport'ta seçilen yüzeyleri (faces) analiz eder, UV adacıklarını (UV Islands)
ayrıştırır ve 3D'de bitişik olup UV'de ayrık olan parçalar arasındaki komşuluk
ilişkisini (3D Adjacency Graph) kurar.
"""

from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Set, Optional
import numpy as np
import bpy
import bmesh

from ..core.logging import get_logger

logger = get_logger("blender.selection_group")


@dataclass
class UVIsland:
    """Tek bir ayrık UV adacığını temsil eder."""

    island_id: int
    face_indices: List[int] = field(default_factory=list)
    uv_loops: List[List[Tuple[float, float]]] = field(default_factory=list)
    uv_bbox: Tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0)  # u_min, v_min, u_max, v_max
    center_3d: Optional[Tuple[float, float, float]] = None
    normal_3d: Optional[Tuple[float, float, float]] = None

    @property
    def width_uv(self) -> float:
        return max(0.0, self.uv_bbox[2] - self.uv_bbox[0])

    @property
    def height_uv(self) -> float:
        return max(0.0, self.uv_bbox[3] - self.uv_bbox[1])

    @property
    def area_uv(self) -> float:
        return self.width_uv * self.height_uv


@dataclass
class SelectionGroup:
    """3D Viewport seçimi ve bağlı UV adacıkları kümesi."""

    name: str
    face_indices: List[int] = field(default_factory=list)
    islands: List[UVIsland] = field(default_factory=list)
    # island_id -> [neighbor_island_ids] (3D meşte bitişik olup UV'de ayrık olanlar)
    adjacency_3d: Dict[int, List[int]] = field(default_factory=dict)

    @property
    def island_count(self) -> int:
        return len(self.islands)

    @property
    def total_faces(self) -> int:
        return len(self.face_indices)


class SelectionGroupResolver:
    """Mesh seçimlerinden SelectionGroup ve UVIsland çıkaran analiz motoru."""

    @classmethod
    def resolve_from_mesh(
        cls,
        obj: bpy.types.Object,
        group_name: str = "3D Selection",
    ) -> Optional[SelectionGroup]:
        """Aktif mesh ve Edit Mode seçiminden UV adacıklarını ve 3D komşuluklarını ayrıştırır."""
        if not obj or obj.type != 'MESH':
            return None

        me = obj.data
        bm = bmesh.new()

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(me)
        else:
            bm.from_mesh(me)

        bm.faces.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()

        uv_layer = bm.loops.layers.uv.active
        if not uv_layer:
            if obj.mode != 'EDIT':
                bm.free()
            logger.warning("No active UV layer found on mesh", object=obj.name)
            return None

        selected_bm_faces = [f for f in bm.faces if f.select]
        if not selected_bm_faces:
            if obj.mode != 'EDIT':
                bm.free()
            return None

        selected_indices = [f.index for f in selected_bm_faces]

        # 1. UV Adacıklarını (UV Islands) Kümele
        # İki yüzey, paylaştıkları 3D kenar boyunca UV koordinatları da örtüşüyorsa aynı adacıktadır.
        islands_faces = cls._cluster_uv_islands(selected_bm_faces, uv_layer)

        # 2. Her adacık için UV koordinatlarını, Bounding Box'ı ve 3D merkez/normalleri hesapla
        uv_islands: List[UVIsland] = []
        face_to_island: Dict[int, int] = {}

        for idx, face_list in enumerate(islands_faces):
            island_face_indices = [f.index for f in face_list]
            for f_idx in island_face_indices:
                face_to_island[f_idx] = idx

            island_uv_loops: List[List[Tuple[float, float]]] = []
            all_u: List[float] = []
            all_v: List[float] = []
            center_accum = np.zeros(3, dtype=np.float64)
            normal_accum = np.zeros(3, dtype=np.float64)

            for f in face_list:
                f_uvs = [(loop[uv_layer].uv.x, loop[uv_layer].uv.y) for loop in f.loops]
                island_uv_loops.append(f_uvs)
                for u, v in f_uvs:
                    all_u.append(u)
                    all_v.append(v)

                center_accum += np.array(f.calc_center_median(), dtype=np.float64)
                normal_accum += np.array(f.normal, dtype=np.float64)

            count = max(1, len(face_list))
            avg_center = tuple(center_accum / count)
            norm_len = np.linalg.norm(normal_accum)
            avg_normal = tuple(normal_accum / norm_len) if norm_len > 1e-6 else (0.0, 0.0, 1.0)

            u_min = max(0.0, min(all_u)) if all_u else 0.0
            v_min = max(0.0, min(all_v)) if all_v else 0.0
            u_max = min(1.0, max(all_u)) if all_u else 1.0
            v_max = min(1.0, max(all_v)) if all_v else 1.0

            island = UVIsland(
                island_id=idx,
                face_indices=island_face_indices,
                uv_loops=island_uv_loops,
                uv_bbox=(u_min, v_min, u_max, v_max),
                center_3d=(float(avg_center[0]), float(avg_center[1]), float(avg_center[2])),
                normal_3d=(float(avg_normal[0]), float(avg_normal[1]), float(avg_normal[2])),
            )
            uv_islands.append(island)

        # 3. 3D Adjacency Graph: 3D meşte kenar paylaşan ancak farklı UV adalarında olanları bağla
        adjacency_3d: Dict[int, Set[int]] = {i.island_id: set() for i in uv_islands}

        for f in selected_bm_faces:
            isl_a = face_to_island.get(f.index)
            if isl_a is None:
                continue
            for edge in f.edges:
                for other_face in edge.link_faces:
                    if other_face.select and other_face.index != f.index:
                        isl_b = face_to_island.get(other_face.index)
                        if isl_b is not None and isl_a != isl_b:
                            adjacency_3d[isl_a].add(isl_b)
                            adjacency_3d[isl_b].add(isl_a)

        adj_dict = {k: sorted(list(v)) for k, v in adjacency_3d.items()}

        if obj.mode != 'EDIT':
            bm.free()

        selection_group = SelectionGroup(
            name=group_name,
            face_indices=selected_indices,
            islands=uv_islands,
            adjacency_3d=adj_dict,
        )

        logger.info(
            "Resolved 3D Selection Group",
            faces=len(selected_indices),
            islands=len(uv_islands),
            adjacent_pairs=sum(len(v) for v in adj_dict.values()) // 2,
        )

        return selection_group

    @staticmethod
    def _cluster_uv_islands(
        faces: List[bmesh.types.BMFace],
        uv_layer: bmesh.types.BMLayerItem,
        uv_eps: float = 1e-4,
    ) -> List[List[bmesh.types.BMFace]]:
        """Seçili yüzeyleri paylaşılan UV dikiş/kenar sürekliliğine göre adacıklara (islands) gruplar."""
        unvisited: Set[int] = {f.index for f in faces}
        face_map: Dict[int, bmesh.types.BMFace] = {f.index: f for f in faces}
        islands: List[List[bmesh.types.BMFace]] = []

        # Hızlı komşuluk araması için kenar loop haritası
        # (3D edge index) -> list of (face_index, [(u1, v1), (u2, v2)])
        edge_uv_map: Dict[int, List[Tuple[int, Tuple[float, float], Tuple[float, float]]]] = {}

        for f in faces:
            for loop in f.loops:
                edge = loop.edge
                v_start = loop.vert
                v_end = loop.link_loop_next.vert
                uv_start = (loop[uv_layer].uv.x, loop[uv_layer].uv.y)
                uv_end = (loop.link_loop_next[uv_layer].uv.x, loop.link_loop_next[uv_layer].uv.y)

                if edge.index not in edge_uv_map:
                    edge_uv_map[edge.index] = []
                edge_uv_map[edge.index].append((f.index, uv_start, uv_end))

        # BFS ile adacık yayılımı
        while unvisited:
            seed_idx = next(iter(unvisited))
            unvisited.remove(seed_idx)

            queue = [seed_idx]
            current_island = [face_map[seed_idx]]

            while queue:
                curr_idx = queue.pop(0)
                curr_face = face_map[curr_idx]

                for loop in curr_face.loops:
                    edge = loop.edge
                    curr_uv_start = (loop[uv_layer].uv.x, loop[uv_layer].uv.y)
                    curr_uv_end = (loop.link_loop_next[uv_layer].uv.x, loop.link_loop_next[uv_layer].uv.y)

                    for other_idx, other_uv_start, other_uv_end in edge_uv_map.get(edge.index, []):
                        if other_idx in unvisited:
                            # UV dikiş kontrolü: İki yüzey bu kenarda UV uzayında birleşiyor mu?
                            # (Ters yönde ya da aynı yönde uyuşuyor mu)
                            d1 = (curr_uv_start[0] - other_uv_end[0])**2 + (curr_uv_start[1] - other_uv_end[1])**2
                            d2 = (curr_uv_end[0] - other_uv_start[0])**2 + (curr_uv_end[1] - other_uv_start[1])**2
                            match_rev = (d1 < uv_eps**2) and (d2 < uv_eps**2)

                            d3 = (curr_uv_start[0] - other_uv_start[0])**2 + (curr_uv_start[1] - other_uv_start[1])**2
                            d4 = (curr_uv_end[0] - other_uv_end[0])**2 + (curr_uv_end[1] - other_uv_end[1])**2
                            match_same = (d3 < uv_eps**2) and (d4 < uv_eps**2)

                            if match_rev or match_same:
                                unvisited.remove(other_idx)
                                queue.append(other_idx)
                                current_island.append(face_map[other_idx])

            islands.append(current_island)

        return islands
