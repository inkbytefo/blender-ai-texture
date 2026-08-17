# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Generation Cache Module.

Aynı prompt ve parametrelerle yapılan isteklerin sonuçlarını diskte
sıkıştırılmış NumPy (.npz) formatında saklar ve gereksiz API harcamalarını önler.
"""

import os
import tempfile
import time
from typing import Optional, List
import numpy as np

from .response import AIResponse
from ..core.config import get_addon_preferences
from ..core.logging import get_logger

logger = get_logger("ai.cache")


class GenerationCache:
    """Disk tabanlı AI generation önbellek motoru."""

    _cache_dir: Optional[str] = None

    @classmethod
    def get_cache_dir(cls) -> str:
        """Önbellek klasör yolunu döndürür ve yoksa oluşturur."""
        if cls._cache_dir is None:
            base_dir = os.path.join(tempfile.gettempdir(), "ai_texture_painter_cache")
            os.makedirs(base_dir, exist_ok=True)
            cls._cache_dir = base_dir
        return cls._cache_dir

    @classmethod
    def is_enabled(cls) -> bool:
        """Kullanıcı tercihlerinde önbelleğin aktif olup olmadığını denetler."""
        prefs = get_addon_preferences()
        return getattr(prefs, "cache_enabled", True) if prefs else True

    @classmethod
    def get(cls, request_hash: str) -> Optional[AIResponse]:
        """Önbellekte hash'e karşılık gelen yanıt varsa döndürür."""
        if not cls.is_enabled() or not request_hash:
            return None

        file_path = os.path.join(cls.get_cache_dir(), f"{request_hash}.npz")
        if not os.path.exists(file_path):
            return None

        try:
            with np.load(file_path, allow_pickle=False) as data:
                count = int(data["count"])
                images: List[np.ndarray] = [data[f"img_{i}"] for i in range(count)]
                provider_name = str(data["provider_name"])
                model_name = str(data["model_name"])
                seed_used = int(data["seed_used"])

            logger.info("Cache hit", hash=request_hash, variations=len(images))
            return AIResponse(
                success=True,
                images=images,
                provider_name=provider_name,
                model_name=model_name,
                generation_time=0.01,
                seed_used=seed_used,
                metadata={"cache_hit": True},
            )

        except Exception as e:
            logger.warning("Failed to read cache file", file=file_path, error=str(e))
            return None

    @classmethod
    def put(cls, request_hash: str, response: AIResponse) -> None:
        """Başarılı bir yanıtı önbelleğe kaydeder."""
        if not cls.is_enabled() or not request_hash or not response.success or not response.images:
            return

        file_path = os.path.join(cls.get_cache_dir(), f"{request_hash}.npz")
        try:
            save_dict = {
                "count": len(response.images),
                "provider_name": response.provider_name or "",
                "model_name": response.model_name or "",
                "seed_used": response.seed_used,
                "timestamp": time.time(),
            }
            for i, img in enumerate(response.images):
                save_dict[f"img_{i}"] = img.astype(np.float32)

            np.savez_compressed(file_path, **save_dict)
            logger.info("Saved to cache", hash=request_hash, count=len(response.images))

        except Exception as e:
            logger.warning("Failed to write cache file", error=str(e))

    @classmethod
    def clear(cls) -> int:
        """Tüm önbellek dosyalarını temizler ve silinen dosya sayısını döndürür."""
        cache_dir = cls.get_cache_dir()
        count = 0
        if os.path.exists(cache_dir):
            for fname in os.listdir(cache_dir):
                if fname.endswith(".npz"):
                    try:
                        os.remove(os.path.join(cache_dir, fname))
                        count += 1
                    except Exception:
                        pass
        logger.info("Cache cleared", files_removed=count)
        return count

    @classmethod
    def get_cache_size_mb(cls) -> float:
        """Önbelleğin diskte kapladığı toplam boyutu (MB) hesaplar."""
        cache_dir = cls.get_cache_dir()
        total_bytes = 0
        if os.path.exists(cache_dir):
            for fname in os.listdir(cache_dir):
                if fname.endswith(".npz"):
                    try:
                        total_bytes += os.path.getsize(os.path.join(cache_dir, fname))
                    except Exception:
                        pass
        return round(total_bytes / (1024.0 * 1024.0), 2)
