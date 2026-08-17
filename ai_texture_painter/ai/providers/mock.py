# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Mock AI Provider.

Harici API bağımlılığı olmadan eklentinin tüm üretim, varyasyon,
inpaint ve çözünürlük özelliklerini test etmek için procedural
sentetik doku üreten test sağlayıcısıdır.
"""

import time
from typing import Set, List
import numpy as np

from ..provider import AIProvider
from ..capabilities import Capability, AIOperation
from ..request import AIRequest
from ..response import AIResponse
from ...core.logging import get_logger

logger = get_logger("ai.providers.mock")


class MockProvider(AIProvider):
    """Test ve çevrimdışı geliştirme amaçlı Mock AI Provider."""

    @property
    def name(self) -> str:
        return "mock"

    @property
    def display_name(self) -> str:
        return "Mock Provider (Test)"

    @property
    def capabilities(self) -> Set[Capability]:
        return {
            Capability.TEXT_TO_IMAGE,
            Capability.IMAGE_TO_IMAGE,
            Capability.INPAINT,
            Capability.OUTPAINT,
            Capability.REFERENCE_IMAGE,
            Capability.VARIATIONS,
            Capability.MASK,
            Capability.NEGATIVE_PROMPT,
            Capability.SEED_CONTROL,
            Capability.STRENGTH_CONTROL,
            Capability.SEAMLESS,
        }

    def get_models(self) -> List[str]:
        return ["mock-synthetic-v1", "mock-procedural-pbr"]

    def generate(self, request: AIRequest) -> AIResponse:
        """İsteğe göre sentetik procedural test dokuları üretir."""
        start_time = time.time()
        logger.info(
            "Mock generation started",
            op=request.operation.name,
            prompt=request.prompt,
            size=f"{request.width}x{request.height}",
            variations=request.variation_count,
        )

        # İstek doğrulama
        errors = request.validate()
        if errors:
            return AIResponse.error(
                message="; ".join(errors),
                code="INVALID_REQUEST",
                provider=self.name,
            )

        base_seed = request.seed if request.seed >= 0 else int(time.time() * 1000) % 100000
        images: List[np.ndarray] = []

        w, h = request.width, request.height

        for v_idx in range(request.variation_count):
            var_seed = (base_seed + v_idx * 1337) % (2**31 - 1)
            rng = np.random.RandomState(var_seed)

            # 1. Procedural desen oluştur
            y, x = np.mgrid[:h, :w]
            freq = 0.02 + (v_idx * 0.01)

            # Dalga / damar deseni
            wave = np.sin(x * freq + rng.uniform(0, 3.14)) * np.cos(y * freq + rng.uniform(0, 3.14))
            wave = (wave + 1.0) / 2.0  # [0.0, 1.0]

            # Gürültü ekle
            noise = rng.uniform(0.0, 0.4, (h, w))
            pattern = np.clip(wave * 0.7 + noise * 0.3, 0.0, 1.0)

            # Renk paleti seçimi (prompt içeriğine göre basit renk tonlama)
            prompt_lower = request.prompt.lower()
            if "leather" in prompt_lower or "deri" in prompt_lower:
                base_color = np.array([0.25, 0.15, 0.08], dtype=np.float32)
            elif "wood" in prompt_lower or "ahsap" in prompt_lower or "ahşap" in prompt_lower:
                base_color = np.array([0.45, 0.28, 0.12], dtype=np.float32)
            elif "metal" in prompt_lower or "gold" in prompt_lower:
                base_color = np.array([0.65, 0.55, 0.25], dtype=np.float32)
            elif "stone" in prompt_lower or "rock" in prompt_lower or "tas" in prompt_lower:
                base_color = np.array([0.40, 0.40, 0.42], dtype=np.float32)
            else:
                # Rastgele zengin ton
                base_color = rng.uniform(0.2, 0.8, 3).astype(np.float32)

            rgb = np.clip(pattern[..., np.newaxis] * base_color * 2.0, 0.0, 1.0)
            alpha = np.ones((h, w, 1), dtype=np.float32)
            generated_img = np.concatenate([rgb, alpha], axis=-1).astype(np.float32)

            # Eğer inpaint veya image-to-image ise ve kaynak görsel varsa strength ile birleştir
            if request.source_image is not None and request.source_image.shape[:2] == (h, w):
                strength = float(request.strength)
                generated_img = (
                    request.source_image * (1.0 - strength) + generated_img * strength
                )

            images.append(generated_img)

        gen_time = time.time() - start_time
        logger.info(
            "Mock generation completed",
            duration=round(gen_time, 3),
            variations_produced=len(images),
        )

        return AIResponse(
            success=True,
            images=images,
            provider_name=self.name,
            model_name="mock-procedural-pbr",
            generation_time=gen_time,
            seed_used=base_seed,
            metadata={"mock": True, "variations": len(images)},
        )
