# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""Unit tests for AI Abstraction layer and MockProvider."""

import numpy as np
import pytest

from ai_texture_painter.ai.capabilities import AIOperation, Capability
from ai_texture_painter.ai.request import AIRequest
from ai_texture_painter.ai.response import AIResponse
from ai_texture_painter.ai.registry import ProviderRegistry, get_registry
from ai_texture_painter.ai.providers.mock import MockProvider


class TestAIRequest:
    def test_valid_request(self):
        """Geçerli bir istekte hata dönmemelidir."""
        req = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="worn brown leather texture",
            width=512,
            height=512,
        )
        assert req.validate() == []

    def test_empty_prompt_validation(self):
        """GENERATE işleminde boş prompt hata vermeli."""
        req = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="   ",
            width=512,
            height=512,
        )
        errors = req.validate()
        assert any("Prompt boş olamaz" in e for e in errors)

    def test_fill_missing_mask_validation(self):
        """FILL işleminde maske eksikse hata vermeli."""
        req = AIRequest(
            operation=AIOperation.FILL,
            prompt="repair wood crack",
            width=512,
            height=512,
            source_image=np.zeros((512, 512, 4), dtype=np.float32),
            mask=None,
        )
        errors = req.validate()
        assert any("maske (mask) zorunludur" in e for e in errors)

    def test_deterministic_hash(self):
        """Aynı parametreli iki istek aynı hash'i üretmelidir."""
        r1 = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="rusty metal plate",
            width=512,
            height=512,
            seed=42,
        )
        r2 = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="rusty metal plate",
            width=512,
            height=512,
            seed=42,
        )
        assert r1.to_hash() == r2.to_hash()


class TestProviderRegistry:
    def test_register_and_get(self):
        """Registry'ye ekleme ve alma testi."""
        reg = ProviderRegistry()
        mock = MockProvider()
        reg.register(mock)

        assert reg.get("mock") == mock
        assert reg.get("MOCK") == mock
        assert mock in reg.list_providers()

    def test_filter_by_capability(self):
        """Capability filtreleme testi."""
        reg = ProviderRegistry()
        mock = MockProvider()
        reg.register(mock)

        inpaint_providers = reg.get_providers_for_capability(Capability.INPAINT)
        assert mock in inpaint_providers


class TestMockProvider:
    def test_mock_capabilities(self):
        """MockProvider capability denetimi."""
        mock = MockProvider()
        assert mock.supports(Capability.TEXT_TO_IMAGE)
        assert mock.supports(Capability.INPAINT)
        assert mock.supports(Capability.VARIATIONS)
        assert mock.supports(Capability.SEED_CONTROL)

    def test_generate_text_to_image(self):
        """MockProvider text-to-image üretim testi."""
        mock = MockProvider()
        req = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="dark wood texture",
            width=256,
            height=256,
            variation_count=1,
            seed=123,
        )
        res = mock.generate(req)

        assert res.success is True
        assert len(res.images) == 1
        assert res.images[0].shape == (256, 256, 4)
        assert res.images[0].dtype == np.float32
        assert res.images[0].min() >= 0.0
        assert res.images[0].max() <= 1.0

    def test_generate_multiple_variations(self):
        """MockProvider çoklu varyasyon üretim testi."""
        mock = MockProvider()
        req = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="gold metal surface",
            width=128,
            height=128,
            variation_count=4,
            seed=500,
        )
        res = mock.generate(req)

        assert res.success is True
        assert len(res.images) == 4
        # Varyasyonlar birbirinden farklı olmalı
        assert not np.allclose(res.images[0], res.images[1])
        assert not np.allclose(res.images[1], res.images[2])

    def test_inpaint_generation(self):
        """MockProvider inpaint üretim testi."""
        mock = MockProvider()
        src = np.full((128, 128, 4), 0.2, dtype=np.float32)
        mask = np.zeros((128, 128), dtype=np.float32)
        mask[32:96, 32:96] = 1.0

        req = AIRequest(
            operation=AIOperation.FILL,
            prompt="bright marble inlay",
            width=128,
            height=128,
            source_image=src,
            mask=mask,
            strength=0.8,
        )
        res = mock.generate(req)

        assert res.success is True
        assert len(res.images) == 1
        assert res.images[0].shape == (128, 128, 4)
