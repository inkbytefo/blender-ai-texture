# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""Unit tests for OpenAI-Compatible and Google Gemini providers with mock HTTP responses."""

import base64
from unittest.mock import patch, MagicMock
import numpy as np
import pytest

from ai_texture_painter.ai.capabilities import AIOperation
from ai_texture_painter.ai.request import AIRequest
from ai_texture_painter.ai.providers.openai_compatible import OpenAICompatibleProvider
from ai_texture_painter.ai.providers.gemini import GeminiProvider
from ai_texture_painter.ai.transport.http import HttpClient, HttpException
from ai_texture_painter.utils.png import numpy_to_png_bytes


class TestOpenAICompatibleProvider:
    def test_missing_api_key(self):
        """API anahtarı eksik olduğunda hata yanıtı dönmelidir."""
        provider = OpenAICompatibleProvider()
        req = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="brick wall",
            width=512,
            height=512,
        )
        with patch.object(provider, "_get_credentials", return_value=("", "https://api.openai.com/v1", "dall-e-3")):
            response = provider.generate(req)
            assert response.success is False
            assert response.error_code == "API_KEY_MISSING"

    @patch("ai_texture_painter.ai.transport.http.HttpClient.post_json")
    def test_generate_text_to_image_success(self, mock_post_json):
        """OpenAI /images/generations endpointi ile başarılı üretim testi."""
        provider = OpenAICompatibleProvider()
        req = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="brick wall",
            width=256,
            height=256,
        )

        # Sahte PNG çıktısı oluştur ve base64 yap
        sample_img = np.ones((256, 256, 4), dtype=np.float32)
        b64_sample = base64.b64encode(numpy_to_png_bytes(sample_img)).decode("utf-8")

        mock_post_json.return_value = {
            "data": [{"b64_json": b64_sample}]
        }

        with patch.object(provider, "_get_credentials", return_value=("sk-test-key", "https://api.openai.com/v1", "dall-e-3")):
            response = provider.generate(req)
            assert response.success is True
            assert len(response.images) == 1
            assert response.images[0].shape == (256, 256, 4)

    @patch("ai_texture_painter.ai.transport.http.HttpClient.post_multipart")
    def test_inpaint_multipart_success(self, mock_post_multipart):
        """OpenAI /images/edits endpointi ile inpaint multipart yükleme testi."""
        provider = OpenAICompatibleProvider()
        src = np.ones((128, 128, 4), dtype=np.float32)
        mask = np.zeros((128, 128), dtype=np.float32)
        mask[32:96, 32:96] = 1.0

        req = AIRequest(
            operation=AIOperation.FILL,
            prompt="golden ornaments",
            width=128,
            height=128,
            source_image=src,
            mask=mask,
        )

        sample_img = np.full((128, 128, 4), 0.9, dtype=np.float32)
        b64_sample = base64.b64encode(numpy_to_png_bytes(sample_img)).decode("utf-8")

        mock_post_multipart.return_value = {
            "data": [{"b64_json": b64_sample}]
        }

        with patch.object(provider, "_get_credentials", return_value=("sk-test-key", "https://api.openai.com/v1", "dall-e-2")):
            response = provider.generate(req)
            assert response.success is True
            assert len(response.images) == 1
            assert response.images[0].shape == (128, 128, 4)


class TestGeminiProvider:
    def test_missing_api_key(self):
        """API anahtarı eksik olduğunda hata yanıtı dönmelidir."""
        provider = GeminiProvider()
        req = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="futuristic metal panel",
            width=512,
            height=512,
        )
        with patch.object(provider, "_get_credentials", return_value=("", "imagen-3.0-generate-002")):
            response = provider.generate(req)
            assert response.success is False
            assert response.error_code == "API_KEY_MISSING"

    @patch("ai_texture_painter.ai.transport.http.HttpClient.post_json")
    def test_gemini_imagen3_success(self, mock_post_json):
        """Google Imagen 3 predict REST endpointi ile başarılı yanıt çözme testi."""
        provider = GeminiProvider()
        req = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="futuristic metal panel",
            width=256,
            height=256,
            variation_count=2,
        )

        sample_img1 = np.ones((256, 256, 4), dtype=np.float32) * 0.3
        sample_img2 = np.ones((256, 256, 4), dtype=np.float32) * 0.7
        b64_1 = base64.b64encode(numpy_to_png_bytes(sample_img1)).decode("utf-8")
        b64_2 = base64.b64encode(numpy_to_png_bytes(sample_img2)).decode("utf-8")

        mock_post_json.return_value = {
            "predictions": [
                {"bytesBase64Encoded": b64_1},
                {"bytesBase64Encoded": b64_2},
            ]
        }

        with patch.object(provider, "_get_credentials", return_value=("AIzaSyFakeKey", "imagen-3.0-generate-002")):
            response = provider.generate(req)
            assert response.success is True
            assert len(response.images) == 2
            assert response.images[0].shape == (256, 256, 4)
            assert response.images[1].shape == (256, 256, 4)


class TestFalAIProvider:
    def test_missing_api_key(self):
        """fal.ai API anahtarı eksik olduğunda hata yanıtı dönmelidir."""
        from ai_texture_painter.ai.providers.fal_ai import FalAIProvider
        provider = FalAIProvider()
        req = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="wooden planks",
            width=512,
            height=512,
        )
        with patch.object(provider, "_get_credentials", return_value=("", "fal-ai/flux/dev")):
            response = provider.generate(req)
            assert response.success is False
            assert response.error_code == "API_KEY_MISSING"

    @patch("ai_texture_painter.ai.transport.http.HttpClient.get_bytes")
    @patch("ai_texture_painter.ai.transport.http.HttpClient.get_json")
    @patch("ai_texture_painter.ai.transport.http.HttpClient.post_json")
    def test_fal_queue_generation_success(self, mock_post_json, mock_get_json, mock_get_bytes):
        """fal.ai queue submit -> poll -> download akışının tam başarılı testi."""
        from ai_texture_painter.ai.providers.fal_ai import FalAIProvider
        provider = FalAIProvider()
        req = AIRequest(
            operation=AIOperation.GENERATE,
            prompt="wooden planks",
            width=256,
            height=256,
            variation_count=1,
        )

        # 1. Submit -> request_id
        mock_post_json.return_value = {"request_id": "test-req-123"}

        # 2. Poll status -> COMPLETED
        mock_get_json.side_effect = [
            {"status": "COMPLETED"},
            {"images": [{"url": "https://v3.fal.media/test_img.png", "width": 256, "height": 256}], "seed": 42, "request_id": "test-req-123"},
        ]

        # 3. Download image bytes
        sample_img = np.ones((256, 256, 4), dtype=np.float32) * 0.6
        mock_get_bytes.return_value = numpy_to_png_bytes(sample_img)

        with patch.object(provider, "_get_credentials", return_value=("fal-test-key", "fal-ai/flux/dev")):
            response = provider.generate(req)
            assert response.success is True
            assert len(response.images) == 1
            assert response.images[0].shape == (256, 256, 4)
            assert response.seed_used == 42
            assert response.model_name == "fal-ai/flux/dev"
            assert response.metadata.get("fal_request_id") == "test-req-123"

class TestHttpClient:
    def test_http_exception_properties(self):
        """HttpException sınıfının durum ve hata kodlarını tutmasını test et."""
        exc = HttpException("Yetkisiz", status_code=401, error_code="AUTH_ERROR")
        assert exc.status_code == 401
        assert exc.error_code == "AUTH_ERROR"
        assert str(exc) == "Yetkisiz"
