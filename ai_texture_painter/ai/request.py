# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
AI Request Model.

Standartlaştırılmış AI üretim isteği veri modelini,
girdi doğrulamasını ve önbellek hash hesaplamasını içerir.
"""

from dataclasses import dataclass, field
import hashlib
import json
from typing import Optional, List
import numpy as np

from .capabilities import AIOperation, Capability


@dataclass
class AIRequest:
    """Standartlaştırılmış AI generation request veri modeli."""

    # ── Zorunlu Alanlar ──
    operation: AIOperation
    prompt: str
    width: int
    height: int

    # ── Opsiyonel Alanlar ──
    negative_prompt: str = ""
    source_image: Optional[np.ndarray] = None  # (H, W, 4) float32 [0-1]
    mask: Optional[np.ndarray] = None          # (H, W) float32 [0-1]
    reference_images: List[np.ndarray] = field(default_factory=list)

    # ── Parametreler ──
    seed: int = -1                             # -1 = random
    variation_count: int = 1                  # 1-8 arası
    strength: float = 0.75                    # 0.0 - 1.0
    seamless: bool = False
    preserve_unmasked: bool = True
    selection_context: str = ""                # 3D parça adı/bağlamı (ör. "Slider", "Barrel")
    island_count: int = 0                     # İşlenen UV adacık sayısı


    def validate(self) -> List[str]:
        """İstek parametrelerinin geçerliliğini denetler.

        Returns:
            Hata mesajları listesi (boş ise geçerli)
        """
        errors = []

        # 1. Prompt denetimi (REMOVE hariç zorunlu)
        if self.operation != AIOperation.REMOVE and not self.prompt.strip():
            errors.append("Prompt boş olamaz.")

        # 2. Boyut denetimi
        if self.width <= 0 or self.height <= 0:
            errors.append(f"Geçersiz boyut: {self.width}x{self.height}")

        # 3. Kaynak görsel ve Maske denetimi
        if self.operation in {AIOperation.FILL, AIOperation.REMOVE}:
            if self.mask is None:
                errors.append(f"{self.operation.name} işlemi için maske (mask) zorunludur.")
            if self.source_image is None:
                errors.append(f"{self.operation.name} işlemi için kaynak görsel (source_image) zorunludur.")

        if self.operation == AIOperation.EXPAND and self.source_image is None:
            errors.append("EXPAND işlemi için kaynak görsel (source_image) zorunludur.")

        # 4. Parametre sınır denetimleri
        if not (0.0 <= self.strength <= 1.0):
            errors.append(f"Strength 0.0 ile 1.0 arasında olmalıdır: {self.strength}")

        if not (1 <= self.variation_count <= 8):
            errors.append(f"Varyasyon sayısı 1 ile 8 arasında olmalıdır: {self.variation_count}")

        return errors

    def to_hash(self) -> str:
        """İsteğe özgü deterministik bir hash dizesi (16 karakter) üretir.

        Önbellek (cache) anahtarı olarak kullanılır.
        """
        payload = {
            "op": self.operation.name,
            "prompt": self.prompt.strip().lower(),
            "neg": self.negative_prompt.strip().lower(),
            "w": self.width,
            "h": self.height,
            "seed": self.seed,
            "strength": round(float(self.strength), 3),
            "seamless": self.seamless,
        }

        # Eğer maske varsa özet hash'ini ekle
        if self.mask is not None:
            payload["mask_mean"] = round(float(np.mean(self.mask)), 4)
            payload["mask_sum"] = round(float(np.sum(self.mask)), 2)

        data_str = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(data_str.encode("utf-8")).hexdigest()[:16]
