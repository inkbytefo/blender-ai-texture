# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
fal.ai AI Provider.

fal.ai platformunun tüm görsel üretim ve düzenleme modellerini (FLUX.1 Kontext [pro],
FLUX.1 Schnell/Dev/Pro, Recraft V3, SD-XL, Inpaint ve özel modeller) tam şema uyumuyla destekler.
"""

import base64
import time
from typing import Set, List, Dict, Any, Optional
import numpy as np

from ..provider import AIProvider
from ..capabilities import Capability, AIOperation
from ..request import AIRequest
from ..response import AIResponse
from ..transport.http import HttpClient, HttpException
from ...utils.png import numpy_to_png_bytes, png_bytes_to_numpy, image_bytes_to_numpy
from ...core.config import get_addon_preferences
from ...core.logging import get_logger

logger = get_logger("ai.providers.fal")

FAL_RUN_BASE = "https://fal.run"
FAL_QUEUE_BASE = "https://queue.fal.run"

# Uzun süren modeller (GPT Image 2, FLUX Pro vb.) için 10 dakikaya (600 saniye) kadar tolerans
MAX_POLL_ATTEMPTS = 300
POLL_INTERVAL = 2.0


class FalAIProvider(AIProvider):
    """fal.ai platformu üzerindeki modeller için tam şema uyumlu sağlayıcı."""

    @property
    def name(self) -> str:
        return "fal_ai"

    @property
    def display_name(self) -> str:
        return "fal.ai"

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
            "fal-ai/flux-pro/kontext",
            "fal-ai/flux/schnell",
            "fal-ai/flux/dev",
            "fal-ai/flux-pro",
            "fal-ai/flux-lora/inpainting",
            "fal-ai/flux-pro/v1/fill",
            "fal-ai/recraft-v3",
            "CUSTOM",
        ]

    def _get_credentials(self) -> tuple[str, str]:
        """Preferences'tan fal.ai API anahtarını ve aktif model adını alır."""
        prefs = get_addon_preferences()
        if not prefs:
            return "", "fal-ai/flux-pro/kontext"

        api_key = getattr(prefs, "fal_api_key", "").strip()
        choice = getattr(prefs, "fal_model_choice", "fal-ai/flux-pro/kontext")

        if choice == "CUSTOM":
            custom_model = getattr(prefs, "fal_custom_model", "").strip()
            model = custom_model or "fal-ai/flux-pro/kontext"
        else:
            model = choice

        return api_key, model

    def validate_config(self) -> bool:
        api_key, _ = self._get_credentials()
        return bool(api_key)

    def _auth_headers(self, api_key: str) -> dict:
        """fal.ai Authorization header'ını oluşturur."""
        return {
            "Authorization": f"Key {api_key}",
            "Content-Type": "application/json",
        }

    def _is_inpaint_model(self, model: str) -> bool:
        """Model adının inpaint/fill tipi olup olmadığını denetler."""
        lower = model.lower()
        return "inpaint" in lower or "fill" in lower

    def _build_payload(self, request: AIRequest, model: str) -> dict:
        """AI isteğini seçili modelin resmi API şemasına dönüştürür."""
        num_images = min(max(1, request.variation_count), 4)

        # ── 1. Nano Banana 2 Şeması (fal-ai/nano-banana-2/edit) ──
        if "nano-banana" in model.lower():
            image_urls = []
            if request.source_image is not None:
                src_png = numpy_to_png_bytes(request.source_image)
                src_b64 = base64.b64encode(src_png).decode("utf-8")
                image_urls.append(f"data:image/png;base64,{src_b64}")

            payload: dict = {
                "prompt": request.prompt,
                "num_images": num_images,
                "aspect_ratio": "1:1",
                "output_format": "png",
                "safety_tolerance": "4",
                "resolution": "1K",
                "limit_generations": True,
            }
            if image_urls:
                payload["image_urls"] = image_urls
            if request.seed >= 0:
                payload["seed"] = request.seed
            return payload

        # ── 2. GPT Image 2 Edit Şeması (openai/gpt-image-2/edit) ──
        if "gpt-image-2/edit" in model.lower():
            image_urls = []
            if request.source_image is not None:
                src_png = numpy_to_png_bytes(request.source_image)
                src_b64 = base64.b64encode(src_png).decode("utf-8")
                image_urls.append(f"data:image/png;base64,{src_b64}")

            payload: dict = {
                "prompt": request.prompt,
                "image_urls": image_urls,
                "quality": "high",
                "num_images": num_images,
                "output_format": "png",
            }
            if request.mask is not None:
                mask_rgba = np.zeros((request.mask.shape[0], request.mask.shape[1], 4), dtype=np.float32)
                mask_rgba[..., :3] = request.mask[..., np.newaxis]
                mask_rgba[..., 3] = 1.0
                mask_png = numpy_to_png_bytes(mask_rgba)
                mask_b64 = base64.b64encode(mask_png).decode("utf-8")
                payload["mask_url"] = f"data:image/png;base64,{mask_b64}"

            if request.width and request.height:
                payload["image_size"] = {
                    "width": request.width,
                    "height": request.height,
                }
            return payload

        # ── 2. GPT Image 2 Text-to-Image Şeması (openai/gpt-image-2) ──
        if "gpt-image-2" in model.lower():
            payload = {
                "prompt": request.prompt,
                "quality": "high",
                "num_images": num_images,
                "output_format": "png",
            }
            if request.width and request.height:
                payload["image_size"] = {
                    "width": request.width,
                    "height": request.height,
                }
            return payload

        # ── 3. FLUX.1 Kontext [pro] Şeması (fal-ai/flux-pro/kontext) ──
        if "kontext" in model.lower():
            if request.source_image is not None:
                src_png = numpy_to_png_bytes(request.source_image)
                src_b64 = base64.b64encode(src_png).decode("utf-8")
                image_url = f"data:image/png;base64,{src_b64}"
            else:
                dummy = np.ones((request.height or 512, request.width or 512, 4), dtype=np.float32)
                src_png = numpy_to_png_bytes(dummy)
                src_b64 = base64.b64encode(src_png).decode("utf-8")
                image_url = f"data:image/png;base64,{src_b64}"

            payload: dict = {
                "prompt": request.prompt,
                "image_url": image_url,
                "guidance_scale": 3.5,
                "num_images": num_images,
                "output_format": "png",
                "safety_tolerance": "2",
                "aspect_ratio": "1:1",
            }
            if request.seed >= 0:
                payload["seed"] = request.seed
            return payload

        # ── 2. FLUX.2 [pro] Şeması (fal-ai/flux-2-pro) ──
        if "flux-2" in model.lower():
            payload = {
                "prompt": request.prompt,
                "output_format": "png",
                "safety_tolerance": "2",
                "enable_safety_checker": True,
            }
            if request.width and request.height:
                payload["image_size"] = {
                    "width": request.width,
                    "height": request.height,
                }
            if request.seed >= 0:
                payload["seed"] = request.seed
            return payload

        # ── 3. FLUX.1 [schnell] Şeması (fal-ai/flux/schnell) ──
        if "schnell" in model.lower():
            payload = {
                "prompt": request.prompt,
                "num_inference_steps": 4,
                "guidance_scale": 3.5,
                "num_images": num_images,
                "output_format": "png",
                "enable_safety_checker": True,
                "acceleration": "none",
            }
            if request.width and request.height:
                payload["image_size"] = {
                    "width": request.width,
                    "height": request.height,
                }
            if request.seed >= 0:
                payload["seed"] = request.seed
            return payload

        # ── 4. Standart FLUX / Recraft / SD / Inpaint Şeması ──
        payload = {
            "prompt": request.prompt,
            "output_format": "png",
            "num_images": num_images,
        }

        if request.negative_prompt:
            payload["negative_prompt"] = request.negative_prompt

        if request.width and request.height:
            payload["image_size"] = {
                "width": request.width,
                "height": request.height,
            }

        if request.seed >= 0:
            payload["seed"] = request.seed

        # Inpainting için görsel ve maske
        if self._is_inpaint_model(model) and request.source_image is not None and request.mask is not None:
            src_png = numpy_to_png_bytes(request.source_image)
            src_b64 = base64.b64encode(src_png).decode("utf-8")
            payload["image_url"] = f"data:image/png;base64,{src_b64}"

            mask_rgba = np.zeros((request.mask.shape[0], request.mask.shape[1], 4), dtype=np.float32)
            mask_rgba[..., :3] = request.mask[..., np.newaxis]
            mask_rgba[..., 3] = 1.0
            mask_png = numpy_to_png_bytes(mask_rgba)
            mask_b64 = base64.b64encode(mask_png).decode("utf-8")
            payload["mask_url"] = f"data:image/png;base64,{mask_b64}"

        elif request.source_image is not None and request.operation == AIOperation.FILL:
            src_png = numpy_to_png_bytes(request.source_image)
            src_b64 = base64.b64encode(src_png).decode("utf-8")
            payload["image_url"] = f"data:image/png;base64,{src_b64}"

        return payload

    def _extract_images_from_response(self, result_data: dict, headers: dict) -> List[np.ndarray]:
        """fal.ai yanıtından görsel URL'lerini indirir ve NumPy dizilerine çevirir."""
        images: List[np.ndarray] = []
        raw_images = result_data.get("images", [])

        if not raw_images and "output" in result_data:
            output = result_data["output"]
            if isinstance(output, dict) and "images" in output:
                raw_images = output["images"]
            elif isinstance(output, list):
                raw_images = output

        for img_item in raw_images:
            img_url = img_item.get("url") if isinstance(img_item, dict) else img_item
            if img_url:
                try:
                    img_bytes = HttpClient.get_bytes(img_url, headers={"Authorization": headers.get("Authorization", "")}, timeout=30.0)
                    img_arr = image_bytes_to_numpy(img_bytes)
                    images.append(img_arr)
                except Exception as dl_err:
                    logger.warning("Failed to parse fal.ai image", url=img_url, error=str(dl_err))

        return images

    def generate(self, request: AIRequest) -> AIResponse:
        """fal.ai API'si üzerinden doğrudan veya kuyruk çağrısı yapar."""
        start_time = time.time()
        api_key, model = self._get_credentials()

        if not api_key:
            return AIResponse.error(
                "fal.ai API Key eksik! Lütfen Settings veya Preferences altından fal.ai API anahtarınızı girin.",
                code="API_KEY_MISSING",
                provider=self.name,
            )

        headers = self._auth_headers(api_key)

        # Inpaint gerekiyorsa ve model inpaint/edit/kontext modeli değilse otomatik uygun modele yönlendir
        if request.operation in {AIOperation.FILL, AIOperation.REMOVE} and request.mask is not None:
            if "gpt-image-2" in model.lower() and "edit" not in model.lower():
                original_model = model
                model = "openai/gpt-image-2/edit"
                logger.info("Auto-switching to GPT Image 2 edit model", from_model=original_model, to_model=model)
            elif not self._is_inpaint_model(model) and "kontext" not in model.lower() and "edit" not in model.lower():
                original_model = model
                model = "fal-ai/flux-lora/inpainting"
                logger.info("Auto-switching to inpaint model", from_model=original_model, to_model=model)

        payload = self._build_payload(request, model)

        logger.info("Sending request to fal.ai", model=model, prompt=request.prompt[:50])

        try:
            # 1. Doğrudan fal.run ile dene (360 saniyeye kadar bekle)
            direct_url = f"{FAL_RUN_BASE}/{model}"
            try:
                response_data = HttpClient.post_json(direct_url, data=payload, headers=headers, timeout=360.0)
            except HttpException as http_ex:
                # 405/404/400/504 veya Queue gerektiren durumlarda kuyruk uç noktasına geç
                if http_ex.status_code in (405, 404, 400, 504, 408) or "queue" in str(http_ex).lower() or "timeout" in str(http_ex).lower():
                    logger.info("Direct call status, falling back to queue endpoint", status=http_ex.status_code, error=str(http_ex))
                    queue_url = f"{FAL_QUEUE_BASE}/{model}"
                    response_data = HttpClient.post_json(queue_url, data=payload, headers=headers, timeout=60.0)
                else:
                    raise
            except Exception as ex:
                if "timeout" in str(ex).lower() or "timed out" in str(ex).lower():
                    logger.info("Direct call timed out, trying queue endpoint", error=str(ex))
                    queue_url = f"{FAL_QUEUE_BASE}/{model}"
                    response_data = HttpClient.post_json(queue_url, data=payload, headers=headers, timeout=60.0)
                else:
                    raise

            # 2. Kuyruk yanıtıysa bekle (300 deneme * 2sn = 600 saniye / 10 dakika)
            if "status_url" in response_data or "request_id" in response_data:
                status_url = response_data.get("status_url")
                response_url = response_data.get("response_url")
                req_id = response_data.get("request_id", "")

                if not status_url and req_id:
                    status_url = f"{FAL_QUEUE_BASE}/{model}/requests/{req_id}/status"
                if not response_url and req_id:
                    response_url = f"{FAL_QUEUE_BASE}/{model}/requests/{req_id}"

                logger.info("fal.ai queued request, polling status", request_id=req_id, status_url=status_url)

                for attempt in range(MAX_POLL_ATTEMPTS):
                    try:
                        status_data = HttpClient.get_json(status_url, headers=headers, timeout=30.0)
                    except Exception as poll_err:
                        # Tekil ağ/gecikme hatasında hemen pes etme, bir sonraki döngüde tekrar dene
                        logger.warning("Status polling transient error", attempt=attempt, error=str(poll_err))
                        time.sleep(POLL_INTERVAL)
                        continue

                    st = status_data.get("status", "")

                    if st == "COMPLETED":
                        if "images" in status_data:
                            response_data = status_data
                        else:
                            response_data = HttpClient.get_json(response_url, headers=headers, timeout=60.0)
                        break

                    if st in ("FAILED", "CANCELLED"):
                        err_msg = status_data.get("error", "Kuyruk işlemi başarısız oldu.")
                        return AIResponse.error(f"fal.ai hatası: {err_msg}", code="FAL_FAILED", provider=self.name)

                    time.sleep(POLL_INTERVAL)
                else:
                    return AIResponse.error("fal.ai işlemi zaman aşımına uğradı (600 saniye aşıldı).", code="TIMEOUT", provider=self.name)

            # 3. Görselleri çıkar ve NumPy'a dönüştür
            images = self._extract_images_from_response(response_data, headers)

            if not images:
                return AIResponse.error(
                    f"fal.ai ({model}) geçerli bir görsel döndürmedi.",
                    code="EMPTY_RESPONSE",
                    provider=self.name,
                )

            gen_time = time.time() - start_time
            seed_used = response_data.get("seed", -1)

            logger.info(
                "fal.ai generation successful",
                model=model,
                image_count=len(images),
                duration=round(gen_time, 2),
                seed=seed_used,
            )

            meta = {"model": model, "fal_run": True}
            if "request_id" in response_data:
                meta["fal_request_id"] = response_data["request_id"]

            return AIResponse(
                success=True,
                images=images,
                provider_name=self.name,
                model_name=model,
                generation_time=gen_time,
                seed_used=seed_used,
                metadata=meta,
            )

        except HttpException as e:
            msg = str(e)
            if "401" in msg or "403" in msg:
                msg = "fal.ai API anahtarı geçersiz veya yetkisiz. fal.ai/dashboard/keys adresinden anahtarınızı kontrol edin."
            elif "404" in msg:
                msg = f"fal.ai model bulunamadı (404): '{model}'. Lütfen model ID'sini kontrol edin."
            return AIResponse.error(msg, code=e.error_code, provider=self.name)

        except Exception as e:
            logger.error("fal.ai generation error", error=str(e))
            return AIResponse.error(f"Beklenmeyen hata: {str(e)}", code="UNKNOWN", provider=self.name)
