# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Google Gemini / Imagen AI Provider.

Google AI Studio API'si ile Imagen (imagen-3.0-generate-002 vb.) ve
Gemini multimodal modelleri üzerinden görsel üretimi sağlar.
Kullanıcının dilediği model ID'sini serbestçe girmesini destekler.
"""

import base64
import time
from typing import Set, List
import numpy as np

from ..provider import AIProvider
from ..capabilities import Capability
from ..request import AIRequest
from ..response import AIResponse
from ..transport.http import HttpClient, HttpException
from ...utils.png import png_bytes_to_numpy, numpy_to_png_bytes
from ...core.config import get_addon_preferences
from ...core.logging import get_logger

logger = get_logger("ai.providers.gemini")


class GeminiProvider(AIProvider):
    """Google Gemini & Imagen resmi REST API sağlayıcısı."""

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def display_name(self) -> str:
        return "Google Gemini / Imagen"

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
            "gemini-3.1-flash-image",
            "gemini-3.1-flash-lite-image",
            "gemini-3-pro-image",
            "gemini-2.5-flash-image",
            "CUSTOM",
        ]

    def _get_credentials(self) -> tuple[str, str]:
        """Preferences'tan Google API anahtarını ve model adını alır."""
        prefs = get_addon_preferences()
        api_key = getattr(prefs, "gemini_api_key", "").strip() if prefs else ""
        choice = getattr(prefs, "gemini_model_choice", "gemini-2.5-flash-image") if prefs else "gemini-2.5-flash-image"

        if choice == "CUSTOM":
            model = getattr(prefs, "gemini_custom_model", "").strip() if prefs else ""
            model = model or "gemini-2.5-flash-image"
        else:
            model = choice

        return api_key, model

    def validate_config(self) -> bool:
        api_key, _ = self._get_credentials()
        return bool(api_key)

    def generate(self, request: AIRequest) -> AIResponse:
        """Kullanıcının girdiği model ID'sine göre uygun Google REST API uç noktasını çağırır."""
        start_time = time.time()
        api_key, model = self._get_credentials()

        if not api_key:
            return AIResponse.error(
                "Google Gemini API Anahtarı eksik! Lütfen Settings veya Preferences altından anahtarınızı girin.",
                code="API_KEY_MISSING",
                provider=self.name,
            )

        headers = {
            "x-goog-api-key": api_key,
        }

        full_prompt = request.prompt
        if request.negative_prompt:
            full_prompt = f"{full_prompt}, avoid: {request.negative_prompt}"

        # ── 1. Imagen Modelleri (:predict uç noktası) ──
        is_imagen = "imagen" in model.lower()

        if is_imagen:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict"
            sample_count = min(max(1, request.variation_count), 4)
            payload = {
                "instances": [
                    {
                        "prompt": full_prompt,
                    }
                ],
                "parameters": {
                    "sampleCount": sample_count,
                    "aspectRatio": "1:1",
                    "personGeneration": "allow_adult",
                }
            }
        else:
            # ── 2. Gemini Multimodal / GenerateContent Modelleri ──
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            parts = [{"text": full_prompt}]

            # Eğer kaynak görsel varsa multimodal part olarak ekle
            if request.source_image is not None:
                src_png_b64 = base64.b64encode(numpy_to_png_bytes(request.source_image)).decode("utf-8")
                parts.append({
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": src_png_b64,
                    }
                })

            payload = {
                "contents": [
                    {
                        "parts": parts
                    }
                ]
            }

        logger.info("Sending request to Google API", model=model, url=url, is_imagen=is_imagen)

        try:
            response_data = HttpClient.post_json(url, data=payload, headers=headers, timeout=360.0)

            images: List[np.ndarray] = []

            # ── A. Imagen Yanıt Formatı (predictions) ──
            if "predictions" in response_data:
                for pred in response_data["predictions"]:
                    b64_data = pred.get("bytesBase64Encoded") or pred.get("image", {}).get("imageBytes")
                    if b64_data:
                        img_bytes = base64.b64decode(b64_data)
                        img_arr = png_bytes_to_numpy(img_bytes)
                        images.append(img_arr)

            # ── B. Gemini Multimodal Yanıt Formatı (candidates -> content -> parts -> inlineData) ──
            if "candidates" in response_data:
                for cand in response_data.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        inline = part.get("inlineData") or part.get("inline_data")
                        if inline and "data" in inline:
                            img_bytes = base64.b64decode(inline["data"])
                            img_arr = png_bytes_to_numpy(img_bytes)
                            images.append(img_arr)

            if not images:
                # Eğer model sadece metin döndürdüyse bilgilendir
                text_out = ""
                try:
                    for cand in response_data.get("candidates", []):
                        for part in cand.get("content", {}).get("parts", []):
                            if "text" in part:
                                text_out += part["text"][:100] + " "
                except Exception:
                    pass

                if text_out:
                    return AIResponse.error(
                        f"Seçilen model ('{model}') görsel yerine metin yanıtı döndürdü: '{text_out.strip()}'. "
                        f"Görsel üretimi için lütfen model olarak 'imagen-3.0-generate-002' kullanın.",
                        code="TEXT_ONLY_RESPONSE",
                        provider=self.name,
                    )

                return AIResponse.error(
                    f"'{model}' modelinden görsel verisi alınamadı.",
                    code="EMPTY_RESPONSE",
                    provider=self.name,
                )

            gen_time = time.time() - start_time
            logger.info("Google generation successful", model=model, image_count=len(images), duration=round(gen_time, 2))

            return AIResponse(
                success=True,
                images=images,
                provider_name=self.name,
                model_name=model,
                generation_time=gen_time,
                metadata={"google_api": True, "model": model},
            )

        except HttpException as e:
            msg = str(e)
            if "404" in msg:
                msg = (
                    f"Model bulunamadı (404: {model}). "
                    f"Google AI Studio'da görsel üretimi için 'imagen-3.0-generate-002' modelini deneyin."
                )
            elif "400" in msg:
                msg = f"Geçersiz istek (400): {msg}. API anahtarınızı ve model adını ({model}) kontrol edin."
            return AIResponse.error(msg, code=e.error_code, provider=self.name)

        except Exception as e:
            logger.error("Google generation error", error=str(e))
            return AIResponse.error(f"Beklenmeyen hata: {str(e)}", code="UNKNOWN", provider=self.name)
