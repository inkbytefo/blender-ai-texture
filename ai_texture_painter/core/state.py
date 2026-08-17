# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Global state management.

Addon'un çalışma durumunu, aktif generation bilgisini ve
history stack'ini yönetir. Thread-safe erişim için lock kullanır.
"""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional
import threading


# ──────────────────────────────────────────────
# State Enum'ları
# ──────────────────────────────────────────────

class StateStatus(Enum):
    """Addon'un genel çalışma durumu."""

    IDLE = auto()          # Hazır, işlem bekleniyor
    GENERATING = auto()    # AI generation devam ediyor
    PREVIEW = auto()       # Sonuç preview ediliyor
    ERROR = auto()         # Hata durumu


# ──────────────────────────────────────────────
# State Dataclass
# ──────────────────────────────────────────────

@dataclass
class TexturePainterState:
    """Addon'un global state'i.

    Bu sınıf addon'un tüm çalışma durumunu tutar.
    Phase 1'de temel yapı oluşturulur; pixel data alanları
    Phase 2'de aktif olarak kullanılacaktır.
    """

    # ── Genel durum ──
    status: StateStatus = StateStatus.IDLE

    # ── Aktif texture bilgisi ──
    active_image_name: str = ""         # Blender image adı
    active_mask_name: str = ""          # Mask image adı (varsa)

    # ── Generation bilgisi ──
    current_prompt: str = ""
    current_operation: str = ""         # "FILL", "REMOVE", "GENERATE"
    current_provider: str = ""

    # ── Sonuçlar ──
    # Phase 2'de np.ndarray olacak, şimdilik None
    original_pixels: Optional[object] = None
    variations: list = field(default_factory=list)
    selected_variation: int = 0
    preview_image_name: str = ""

    # ── Progress ──
    progress: float = 0.0              # 0.0 — 1.0
    progress_message: str = "Hazır"

    # ── Hata ──
    error_message: str = ""
    error_code: str = ""


# ──────────────────────────────────────────────
# Singleton State Manager
# ──────────────────────────────────────────────

class _StateManager:
    """Thread-safe state yönetimi.

    Singleton pattern ile tek bir global state sağlar.
    Background thread'den state güncellemesi yaparken
    lock kullanarak veri bütünlüğünü korur.
    """

    def __init__(self):
        self._state = TexturePainterState()
        self._lock = threading.Lock()

    @property
    def state(self) -> TexturePainterState:
        """Mevcut state'in kopyasını döndürmez — doğrudan erişim.

        NOT: Yazma işlemleri için update() kullanın.
        """
        return self._state

    def update(self, **kwargs) -> None:
        """State alanlarını thread-safe şekilde günceller.

        Args:
            **kwargs: Güncellenecek state alanları

        Örnek:
            state_manager.update(status=StateStatus.GENERATING, progress=0.5)
        """
        with self._lock:
            for key, value in kwargs.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)

    def reset(self) -> None:
        """State'i başlangıç değerlerine döndürür."""
        with self._lock:
            self._state = TexturePainterState()

    def set_error(self, message: str, code: str = "UNKNOWN") -> None:
        """Hata durumuna geçirir.

        Args:
            message: Kullanıcıya gösterilecek hata mesajı
            code: AIErrorCode değeri
        """
        with self._lock:
            self._state.status = StateStatus.ERROR
            self._state.error_message = message
            self._state.error_code = code
            self._state.progress = 0.0
            self._state.progress_message = f"Hata: {message}"

    def start_generation(self, prompt: str, operation: str, provider: str) -> None:
        """Generation başlatma durumuna geçirir.

        Args:
            prompt: Kullanılan prompt
            operation: İşlem türü (FILL, REMOVE, GENERATE)
            provider: Provider adı
        """
        with self._lock:
            self._state.status = StateStatus.GENERATING
            self._state.current_prompt = prompt
            self._state.current_operation = operation
            self._state.current_provider = provider
            self._state.progress = 0.0
            self._state.progress_message = "Hazırlanıyor..."
            self._state.error_message = ""
            self._state.error_code = ""
            self._state.variations = []
            self._state.selected_variation = 0

    def finish_generation(self) -> None:
        """Generation tamamlandı durumuna geçirir."""
        with self._lock:
            self._state.status = StateStatus.PREVIEW
            self._state.progress = 1.0
            self._state.progress_message = "Tamamlandı"

    def get_status(self) -> dict:
        """Thread-safe durum bilgisi döndürür.

        Returns:
            Durum sözlüğü (progress, status, message, error)
        """
        with self._lock:
            return {
                "status": self._state.status,
                "progress": self._state.progress,
                "message": self._state.progress_message,
                "error_message": self._state.error_message,
                "error_code": self._state.error_code,
                "variation_count": len(self._state.variations),
                "selected_variation": self._state.selected_variation,
            }


# ── Global singleton ──
_manager = _StateManager()


def get_state() -> TexturePainterState:
    """Global state nesnesini döndürür."""
    return _manager.state


def get_state_manager() -> _StateManager:
    """State manager'ı döndürür (thread-safe update için)."""
    return _manager


def reset_state() -> None:
    """Global state'i sıfırlar."""
    _manager.reset()
