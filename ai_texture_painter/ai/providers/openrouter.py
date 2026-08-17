# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
OpenRouter AI Image Provider.

OpenRouter'ın resmi Image API'si (https://openrouter.ai/api/v1/images) üzerinden
GPT Image 2, Seedream 4.5, FLUX.2 Pro, Gemini 2.5 Flash Image, Recraft V3 ve
tüm OpenRouter görsel modelleriyle entegrasyonu sağlar.
"""

import base64
import time
import urllib.request
from typing import Set, List
import numpy as np

from ..provider import AIProvider
from ..capabilities import Capability, AIOperation
from ..request import AIRequest
from ..response import AIResponse
from ..transport.http import HttpClient, HttpException
from ...utils.png import numpy_to_png_bytes, png_bytes_to_numpy
from ...core.config import get_addon_preferences
from ...core.logging import get_logger

logger = get_logger("ai.providers.openrouter")


class OpenRouterProvider(AIProvider):
    """OpenRouter özel Image API sağlayıcısı."""

    @property
    def name(self) -> str:
        return "openrouter"

    @property
    def display_name(self) -> str:
        return "OpenRouter"

    @property
    def capabilities(self) -> Set[Capability]:
        return {
            Capability.TEXT_TO_IMAGE,
            Capability.IMAGE_TO_IMAGE,
            Capability.INPAINT,
            Capability.REFERENCE_IMAGE,
            Capability.VARIATIONS,
            Capability.MASK,
            Capability.STRENGTH_CONTROL,
            Capability.SEED_CONTROL,
            Capability.NEGATIVE_PROMPT,
        }

    def get_models(self) -> List[str]:
        return [
            "openai/gpt-image-2",
            "bytedance-seed/seedream-4.5",
            "black-forest-labs/flux.2-pro",
            "black-forest-labs/flux-1-schnell",
            "google/gemini-2.5-flash-image",
            "recraft/recraft-v3",
            "CUSTOM",
        ]

    def _get_credentials(self) -> tuple[str, str, str, str]:
        """Preferences'tan API anahtarı, Base URL, Model ve Kalite ayarlarını alır."""
        prefs = get_addon_preferences()
        api_key = getattr(prefs, "openrouter_api_key", "").strip() if prefs else ""
        base_url = getattr(prefs, "openrouter_base_url", "https://openrouter.ai/api/v1").strip() if prefs else "https://openrouter.ai/api/v1"
        choice = getattr(prefs, "openrouter_model_choice", "openai/gpt-image-2") if prefs else "openai/gpt-image-2"
        quality = getattr(prefs, "openrouter_quality", "high") if prefs else "high"

        if choice == "CUSTOM":
            model = getattr(prefs, "openrouter_custom_model", "").strip() if prefs else ""
            model = model or "openai/gpt-image-2"
        else:
            model = choice

        base_url = base_url.rstrip("/")
        return api_key, base_url, model, quality

    def validate_config(self) -> bool:
        api_key, _, _, _ = self._get_credentials()
        return bool(api_key)

    def generate(self, request: AIRequest) -> AIResponse:
        """İsteği OpenRouter Image API formatına dönüştürüp gönderir."""
        start_time = time.time()
        api_key, base_url, model, quality = self._get_credentials()

        if not api_key:
            return AIResponse.error(
                "OpenRouter API Anahtarı ayarlanmamış! Lütfen Preferences > Extensions altından anahtarınızı girin.",
                code="API_KEY_MISSING",
                provider=self.name,
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/inkbytefo/blender-ai-texture",
            "X-Title": "AI Texture Painter for Blender",
        }

        url = f"{base_url}/images"
        size_str = f"{request.width}x{request.height}"

        payload = {
            "model": model,
            "prompt": request.prompt,
            "n": min(request.variation_count, 4),
            "size": size_str,
            "quality": quality,
            "output_format": "png",
        }

        # Image-to-Image / Reference Image / Inpainting desteği
        if request.source_image is not None and request.operation in {AIOperation.IMAGE_TO_IMAGE, AIOperation.FILL, AIOperation.REMOVE}:
            src_png = numpy_to_png_bytes(request.source_image)
            src_b64 = base64.b64encode(src_png).decode("utf-8")
            payload["input_references"] = [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{src_b64}",
                    },
                }
            ]

        logger.info("Sending image generation request to OpenRouter", url=url, model=model, size=size_str)

        try:
            response_data = HttpClient.post_json(url, data=payload, headers=headers, timeout=360.0)

            images: List[np.ndarray] = []
            data_items = response_data.get("data", [])

            for item in data_items:
                if "b64_json" in item:
                    b64_str = item["b64_json"]
                    img_bytes = base64.b64decode(b64_str)
                    img_arr = png_bytes_to_numpy(img_bytes)
                    images.append(img_arr)
                elif "url" in item:
                    img_url = item["url"]
                    with urllib.request.urlopen(img_url, timeout=30.0) as img_resp:
                        img_bytes = img_resp.read()
                        img_arr = png_bytes_to_numpy(img_bytes)
                        images.append(img_arr)

            if not images:
                return AIResponse.error(
                    "OpenRouter geçerli bir görsel döndürmedi.",
                    code="EMPTY_RESPONSE",
                    provider=self.name,
                )

            gen_time = time.time() - start_time
            usage_info = response_data.get("usage", {})

            return AIResponse(
                success=True,
                images=images,
                provider_name=self.name,
                model_name=model,
                generation_time=gen_time,
                metadata={
                    "base_url": base_url,
                    "cost": usage_info.get("cost"),
                    "total_tokens": usage_info.get("total_tokens"),
                },
            )

        except HttpException as e:
            logger.error("OpenRouter HTTP Error", error=str(e), status_code=e.status_code)
            return AIResponse.error(str(e), code=e.error_code, provider=self.name)
        except Exception as e:
            logger.error("OpenRouter generation failed", error=str(e))
            return AIResponse.error(f"Beklenmeyen hata: {str(e)}", code="UNKNOWN", provider=self.name)
