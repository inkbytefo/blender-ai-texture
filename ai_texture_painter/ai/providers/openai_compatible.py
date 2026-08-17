# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
OpenAI-Compatible AI Provider.

OpenAI (DALL-E 3, DALL-E 2, GPT-Image), OpenRouter, Together AI,
LocalAI, Ollama ve diğer OpenAI uyumlu REST API servisleriyle entegrasyonu sağlar.
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

logger = get_logger("ai.providers.openai_compatible")


class OpenAICompatibleProvider(AIProvider):
    """OpenAI ve uyumlu servisler (OpenRouter, Together, LocalAI) için sağlayıcı."""

    @property
    def name(self) -> str:
        return "openai_compatible"

    @property
    def display_name(self) -> str:
        return "OpenAI Compatible"

    @property
    def capabilities(self) -> Set[Capability]:
        return {
            Capability.TEXT_TO_IMAGE,
            Capability.IMAGE_TO_IMAGE,
            Capability.INPAINT,
            Capability.VARIATIONS,
            Capability.MASK,
            Capability.STRENGTH_CONTROL,
        }

    def get_models(self) -> List[str]:
        return [
            "gpt-image-2",
            "gpt-image-1.5",
            "gpt-image-1",
            "gpt-image-1-mini",
            "dall-e-3",
            "dall-e-2",
            "gpt-4o",
            "CUSTOM",
        ]

    def _get_credentials(self) -> tuple[str, str, str]:
        """Preferences'tan API anahtarı, Base URL ve model adını alır."""
        prefs = get_addon_preferences()
        api_key = getattr(prefs, "openai_api_key", "").strip() if prefs else ""
        base_url = getattr(prefs, "openai_base_url", "https://api.openai.com/v1").strip() if prefs else "https://api.openai.com/v1"
        choice = getattr(prefs, "openai_model_choice", "gpt-image-2") if prefs else "gpt-image-2"

        if choice == "CUSTOM":
            model = getattr(prefs, "openai_custom_model", "").strip() if prefs else ""
            model = model or "gpt-image-2"
        else:
            model = choice

        base_url = base_url.rstrip("/")
        return api_key, base_url, model

    def validate_config(self) -> bool:
        api_key, _, _ = self._get_credentials()
        return bool(api_key)

    def generate(self, request: AIRequest) -> AIResponse:
        """İsteği OpenAI API formatına dönüştürüp gönderir."""
        start_time = time.time()
        api_key, base_url, model = self._get_credentials()

        if not api_key:
            return AIResponse.error(
                "OpenAI API Anahtarı ayarlanmamış! Lütfen Preferences > Extensions altından anahtarınızı girin.",
                code="API_KEY_MISSING",
                provider=self.name,
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
        }

        # İstenen çözünürlüğü hazırla (örn: 1024x1024)
        size_str = f"{request.width}x{request.height}"
        is_gpt_image = "gpt-image" in model.lower()

        try:
            # 1. Inpainting / Edit işlemi (/v1/images/edits)
            if request.operation in {AIOperation.FILL, AIOperation.REMOVE} and request.source_image is not None and request.mask is not None:
                url = f"{base_url}/images/edits"
                logger.info("Sending inpainting request to OpenAI edits endpoint", url=url, model=model)

                # Kaynak ve maskeyi PNG baytlarına çevir
                src_png = numpy_to_png_bytes(request.source_image)

                # Maskede alfa kanalı ekle (RGBA)
                mask_rgba = np.zeros((request.mask.shape[0], request.mask.shape[1], 4), dtype=np.float32)
                # Maskenin 1 olduğu yerlerde Alpha = 0.0 (şeffaf/düzenlenecek), 0 olduğu yerlerde Alpha = 1.0 (opak)
                mask_rgba[..., :3] = request.mask[..., np.newaxis]
                mask_rgba[..., 3] = 1.0 - np.clip(request.mask, 0.0, 1.0)
                mask_png = numpy_to_png_bytes(mask_rgba)

                fields = {
                    "prompt": request.prompt or "fill area seamlessly",
                    "n": str(min(request.variation_count, 4) if model != "dall-e-3" else 1),
                    "size": size_str,
                    "response_format": "b64_json",
                    "model": model,
                }
                if is_gpt_image:
                    fields["quality"] = "high"

                files = {
                    "image": ("image.png", src_png, "image/png"),
                    "mask": ("mask.png", mask_png, "image/png"),
                }

                response_data = HttpClient.post_multipart(url, fields=fields, files=files, headers=headers, timeout=360.0)

            # 2. Text-to-Image işlemi (/v1/images/generations)
            else:
                url = f"{base_url}/images/generations"
                logger.info("Sending generation request to OpenAI", url=url, model=model)

                payload = {
                    "prompt": request.prompt,
                    "model": model,
                    "n": min(request.variation_count, 4) if model != "dall-e-3" else 1,
                    "size": size_str,
                    "response_format": "b64_json",
                }
                if is_gpt_image:
                    payload["quality"] = "high"

                response_data = HttpClient.post_json(url, data=payload, headers=headers, timeout=360.0)

            # Dönen veriyi parse et
            images: List[np.ndarray] = []
            data_items = response_data.get("data", [])

            for item in data_items:
                if "b64_json" in item:
                    b64_str = item["b64_json"]
                    img_bytes = base64.b64decode(b64_str)
                    img_arr = png_bytes_to_numpy(img_bytes)
                    images.append(img_arr)
                elif "url" in item:
                    # URL dönmüşse indir
                    img_url = item["url"]
                    with urllib.request.urlopen(img_url, timeout=30.0) as img_resp:
                        img_bytes = img_resp.read()
                        img_arr = png_bytes_to_numpy(img_bytes)
                        images.append(img_arr)

            if not images:
                return AIResponse.error(
                    "OpenAI geçerli bir görsel döndürmedi.",
                    code="EMPTY_RESPONSE",
                    provider=self.name,
                )

            gen_time = time.time() - start_time
            return AIResponse(
                success=True,
                images=images,
                provider_name=self.name,
                model_name=model,
                generation_time=gen_time,
                metadata={"base_url": base_url},
            )

        except HttpException as e:
            return AIResponse.error(str(e), code=e.error_code, provider=self.name)
        except Exception as e:
            logger.error("OpenAI generation failed", error=str(e))
            return AIResponse.error(f"Beklenmeyen hata: {str(e)}", code="UNKNOWN", provider=self.name)
