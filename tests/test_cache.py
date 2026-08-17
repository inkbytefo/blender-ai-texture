# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""Unit tests for GenerationCache module."""

import numpy as np
import pytest

from ai_texture_painter.ai.cache import GenerationCache
from ai_texture_painter.ai.response import AIResponse


class TestGenerationCache:
    def setup_method(self):
        """Her testten önce önbelleği temizle."""
        GenerationCache.clear()

    def teardown_method(self):
        """Test bitiminde önbelleği temizle."""
        GenerationCache.clear()

    def test_cache_put_and_get(self):
        """Önbelleğe yazma ve geri okuma testi."""
        req_hash = "testhash12345678"
        sample_img = np.ones((64, 64, 4), dtype=np.float32) * 0.42

        orig_resp = AIResponse(
            success=True,
            images=[sample_img],
            provider_name="test_prov",
            model_name="test_model",
            seed_used=999,
        )

        GenerationCache.put(req_hash, orig_resp)

        cached_resp = GenerationCache.get(req_hash)
        assert cached_resp is not None
        assert cached_resp.success is True
        assert len(cached_resp.images) == 1
        assert cached_resp.images[0].shape == (64, 64, 4)
        assert cached_resp.provider_name == "test_prov"
        assert cached_resp.seed_used == 999
        np.testing.assert_allclose(cached_resp.images[0], sample_img)

    def test_cache_miss(self):
        """Var olmayan hash için None dönmesi testi."""
        assert GenerationCache.get("nonexistent_hash") is None

    def test_cache_clear(self):
        """Önbellek temizleme testi."""
        req_hash = "cleartest12345"
        sample_img = np.zeros((32, 32, 4), dtype=np.float32)
        resp = AIResponse(success=True, images=[sample_img], provider_name="p", model_name="m", seed_used=1)

        GenerationCache.put(req_hash, resp)
        assert GenerationCache.get(req_hash) is not None

        cleared_count = GenerationCache.clear()
        assert cleared_count >= 1
        assert GenerationCache.get(req_hash) is None
