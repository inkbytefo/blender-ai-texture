# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Image Manager Module.

Önizleme (preview) görselleri oluşturma, orijinal texture yedeğini tutma,
Apply ile kalıcı hale getirme ve Cancel ile orijinale dönme iş akışını yönetir.
"""

from typing import Optional
import numpy as np
import bpy

from ..blender.image_adapter import BlenderImageAdapter
from ..core.state import get_state_manager, StateStatus
from ..core.logging import get_logger

logger = get_logger("texture.image_manager")


class ImageManager:
    """Preview, backup ve texture durum yöneticisi."""

    PREVIEW_PREFIX = "_ai_preview_"

    @classmethod
    def get_preview_image_name(cls, base_name: str) -> str:
        """Preview imajının Blender içindeki adını döndürür."""
        return f"{cls.PREVIEW_PREFIX}{base_name}"

    @classmethod
    def backup_original(cls, image: bpy.types.Image) -> np.ndarray:
        """Orijinal texture verisini NumPy dizisi olarak yedekler ve state'e kaydeder."""
        pixels = BlenderImageAdapter.image_to_numpy(image)
        state_mgr = get_state_manager()
        state_mgr.update(
            active_image_name=image.name,
            original_pixels=pixels.copy(),
        )
        logger.info("Texture backed up", image=image.name, shape=str(pixels.shape))
        return pixels

    @classmethod
    def create_or_update_preview(
        cls, base_image: bpy.types.Image, result_pixels: np.ndarray
    ) -> bpy.types.Image:
        """Composited sonucu gösteren preview imajını oluşturur veya günceller."""
        preview_name = cls.get_preview_image_name(base_image.name)
        h, w = result_pixels.shape[:2]

        preview_img = BlenderImageAdapter.get_or_create_image(preview_name, w, h, alpha=True)
        BlenderImageAdapter.numpy_to_image(result_pixels, preview_img)

        state_mgr = get_state_manager()
        state_mgr.update(
            preview_image_name=preview_name,
            status=StateStatus.PREVIEW,
        )

        logger.info("Preview image updated", name=preview_name)
        return preview_img

    @classmethod
    def apply_to_original(
        cls, base_image: bpy.types.Image, result_pixels: np.ndarray
    ) -> None:
        """Preview sonucunu kalıcı olarak ana texture'a yazar ve durumu sıfırlar."""
        BlenderImageAdapter.numpy_to_image(result_pixels, base_image)

        # State'i temizle
        state_mgr = get_state_manager()
        state_mgr.update(
            status=StateStatus.IDLE,
            original_pixels=None,
            preview_image_name="",
            variations=[],
        )

        # Preview imajını sil
        preview_name = cls.get_preview_image_name(base_image.name)
        preview_img = bpy.data.images.get(preview_name)
        if preview_img:
            bpy.data.images.remove(preview_img)

        logger.info("Changes applied to original image", image=base_image.name)

    @classmethod
    def cancel_and_restore(cls, base_image: Optional[bpy.types.Image] = None) -> None:
        """Önizleme durumunu iptal eder ve varsa orijinal dokuyu geri yükler."""
        state = get_state_manager().state

        # Eğer orijinal yedek varsa ve görsel verilmişse geri yükle
        if base_image and state.original_pixels is not None:
            BlenderImageAdapter.numpy_to_image(state.original_pixels, base_image)

        # Preview imajını sil
        if state.preview_image_name:
            preview_img = bpy.data.images.get(state.preview_image_name)
            if preview_img:
                bpy.data.images.remove(preview_img)

        # State'i sıfırla
        get_state_manager().reset()
        logger.info("Operation cancelled, state restored")

    @classmethod
    def cleanup_all_previews(cls) -> None:
        """Tüm `_ai_preview_` ile başlayan geçici imajları temizler."""
        for img in list(bpy.data.images):
            if img.name.startswith(cls.PREVIEW_PREFIX):
                bpy.data.images.remove(img)
