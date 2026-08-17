# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Texture History (Undo / Redo) Module.

Doku üzerinde yapılan tüm Apply işlemlerini bağımsız bir durum yığınında (state stack)
tutar, çok adımlı Undo/Redo imkanı ve bellek koruması sağlar.
"""

from dataclasses import dataclass
import time
from typing import List, Optional
import numpy as np

from ..core.logging import get_logger

logger = get_logger("texture.history")


@dataclass
class HistoryEntry:
    """Tek bir geçmiş adımını temsil eden veri modeli."""

    label: str
    pixels: np.ndarray        # (H, W, 4) float32
    timestamp: float
    operation: str
    prompt: str


class HistoryManager:
    """Çok adımlı Undo/Redo geçmiş yöneticisi (Singleton)."""

    _instance = None
    MAX_HISTORY: int = 15  # Bellek sınırlandırması

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HistoryManager, cls).__new__(cls)
            cls._instance._stack: List[HistoryEntry] = []
            cls._instance._index: int = -1
        return cls._instance

    def push(self, label: str, pixels: np.ndarray, operation: str = "FILL", prompt: str = "") -> None:
        """Yeni bir doku durumunu geçmiş yığınına ekler."""
        # Mevcut index'ten sonraki ileri adımları (redo branch) sil
        if self._index < len(self._stack) - 1:
            self._stack = self._stack[: self._index + 1]

        entry = HistoryEntry(
            label=label,
            pixels=pixels.copy(),
            timestamp=time.time(),
            operation=operation,
            prompt=prompt,
        )

        self._stack.append(entry)

        # Maksimum geçmiş sınırını uygula (en eskiyi çıkar)
        if len(self._stack) > self.MAX_HISTORY:
            self._stack.pop(0)

        self._index = len(self._stack) - 1
        logger.info("History state pushed", label=label, index=self._index, total=len(self._stack))

    def undo(self) -> Optional[HistoryEntry]:
        """Bir adım geri alır ve önceki durumu döndürür."""
        if self.can_undo:
            self._index -= 1
            entry = self._stack[self._index]
            logger.info("History undo", index=self._index, label=entry.label)
            return entry
        return None

    def redo(self) -> Optional[HistoryEntry]:
        """Bir adım ileri alır ve sonraki durumu döndürür."""
        if self.can_redo:
            self._index += 1
            entry = self._stack[self._index]
            logger.info("History redo", index=self._index, label=entry.label)
            return entry
        return None

    @property
    def can_undo(self) -> bool:
        """Geri alınabilecek önceki bir adım var mı?"""
        return self._index > 0

    @property
    def can_redo(self) -> bool:
        """İleri alınabilecek bir adım var mı?"""
        return self._index < len(self._stack) - 1

    @property
    def current_entry(self) -> Optional[HistoryEntry]:
        """Mevcut aktif geçmiş adımını döndürür."""
        if 0 <= self._index < len(self._stack):
            return self._stack[self._index]
        return None

    def clear(self) -> None:
        """Tüm geçmişi ve belleği temizler."""
        self._stack.clear()
        self._index = -1
        logger.info("History cleared")

    def get_memory_usage_mb(self) -> float:
        """Geçmiş yığınının RAM'de kapladığı toplam boyutu (MB) hesaplar."""
        total_bytes = sum(entry.pixels.nbytes for entry in self._stack)
        return round(total_bytes / (1024.0 * 1024.0), 2)


def get_history_manager() -> HistoryManager:
    """HistoryManager singleton nesnesini döndürür."""
    return HistoryManager()
