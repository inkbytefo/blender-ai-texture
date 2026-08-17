# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
AI Response Model.

Standartlaştırılmış AI üretim yanıtı veri modelini içerir.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any
import numpy as np


@dataclass
class AIResponse:
    """Standartlaştırılmış AI generation response veri modeli."""

    success: bool
    images: List[np.ndarray] = field(default_factory=list)  # (H, W, 4) float32 [0-1]
    provider_name: str = ""
    model_name: str = ""
    generation_time: float = 0.0
    seed_used: int = -1
    error_message: str = ""
    error_code: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def variation_count(self) -> int:
        """Üretilen varyasyon görsel sayısı."""
        return len(self.images)

    @property
    def has_error(self) -> bool:
        """Hata olup olmadığı."""
        return not self.success or bool(self.error_message)

    @classmethod
    def error(cls, message: str, code: str = "UNKNOWN", provider: str = "") -> "AIResponse":
        """Hata durumu için pratik factory metodu."""
        return cls(
            success=False,
            images=[],
            provider_name=provider,
            error_message=message,
            error_code=code,
        )
