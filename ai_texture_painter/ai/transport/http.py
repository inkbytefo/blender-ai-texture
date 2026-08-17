# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
HTTP Transport Layer.

Python standart urllib kütüphanesini kullanarak harici bağımlılık olmadan
JSON ve Multipart form-data HTTP POST isteklerini yürütür.
"""

import urllib.request
import urllib.error
import json
import ssl
import uuid
from typing import Dict, Any, Optional, Tuple

from ...core.logging import get_logger

logger = get_logger("ai.transport.http")


class HttpException(Exception):
    """HTTP istek hatası sınıfı."""

    def __init__(self, message: str, status_code: int = 0, error_code: str = "HTTP_ERROR", response_body: str = ""):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.response_body = response_body


class HttpClient:
    """JSON ve Multipart isteklerini yürüten evrensel HTTP istemcisi."""

    @staticmethod
    def _create_ssl_context() -> ssl.SSLContext:
        """Standart güvenli SSL context oluşturur."""
        try:
            return ssl.create_default_context()
        except Exception:
            return ssl._create_unverified_context()

    @classmethod
    def post_json(
        cls,
        url: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 60.0,
    ) -> Dict[str, Any]:
        """JSON gövdesi ile POST isteği gönderir ve yanıtı sözlük olarak döndürür."""
        req_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Blender-AITexturePainter/0.1.0",
        }
        if headers:
            req_headers.update(headers)

        payload_bytes = json.dumps(data).encode("utf-8")
        request = urllib.request.Request(url, data=payload_bytes, headers=req_headers, method="POST")
        ssl_ctx = cls._create_ssl_context()

        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ssl_ctx) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)

        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8", errors="ignore")
            logger.error("HTTP Error", status=e.code, reason=e.reason, body=raw_err[:200])

            err_code = "HTTP_ERROR"
            if e.code in (401, 403):
                err_code = "AUTH_ERROR"
                msg = "API anahtarı geçersiz veya yetkisiz istek (401/403)."
            elif e.code == 429:
                err_code = "RATE_LIMIT"
                msg = "İstek limiti aşıldı (Rate Limit 429). Lütfen biraz bekleyin."
            elif e.code == 404:
                err_code = "NOT_FOUND"
                msg = f"API uç noktası veya model bulunamadı (404): {url}"
            else:
                msg = f"Sunucu hatası ({e.code}): {e.reason}"

            # Eğer yanıt içinde açık bir hata mesajı varsa onu çıkar
            try:
                err_json = json.loads(raw_err)
                if "error" in err_json:
                    if isinstance(err_json["error"], dict) and "message" in err_json["error"]:
                        msg = f"{msg} -> {err_json['error']['message']}"
                    elif isinstance(err_json["error"], str):
                        msg = f"{msg} -> {err_json['error']}"
            except Exception:
                pass

            raise HttpException(msg, status_code=e.code, error_code=err_code, response_body=raw_err)

        except urllib.error.URLError as e:
            logger.error("Network connection error", reason=str(e.reason))
            raise HttpException(f"Bağlantı hatası: {e.reason}", status_code=0, error_code="NETWORK_ERROR")

        except Exception as e:
            logger.error("Unexpected request error", error=str(e))
            raise HttpException(f"Beklenmeyen istek hatası: {str(e)}", status_code=0, error_code="UNKNOWN")

    @classmethod
    def get_json(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ) -> Dict[str, Any]:
        """GET isteği gönderir ve JSON yanıtı döndürür (fal.ai queue polling vb. için)."""
        req_headers = {
            "User-Agent": "Blender-AITexturePainter/0.1.0",
        }
        if headers:
            req_headers.update(headers)

        request = urllib.request.Request(url, headers=req_headers, method="GET")
        ssl_ctx = cls._create_ssl_context()

        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ssl_ctx) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)

        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8", errors="ignore")
            logger.error("HTTP GET Error", status=e.code, reason=e.reason, body=raw_err[:200])
            raise HttpException(
                f"GET hatası ({e.code}): {e.reason}", status_code=e.code, error_code="HTTP_ERROR", response_body=raw_err
            )

        except urllib.error.URLError as e:
            raise HttpException(f"Bağlantı hatası: {e.reason}", status_code=0, error_code="NETWORK_ERROR")

    @classmethod
    def get_bytes(
        cls,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 30.0,
    ) -> bytes:
        """GET isteği ile ham bayt verisi indirir (görsel URL'lerinden indirmek için)."""
        req_headers = {
            "User-Agent": "Blender-AITexturePainter/0.1.0",
        }
        if headers:
            req_headers.update(headers)

        request = urllib.request.Request(url, headers=req_headers, method="GET")
        ssl_ctx = cls._create_ssl_context()

        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ssl_ctx) as response:
                return response.read()

        except urllib.error.HTTPError as e:
            raise HttpException(
                f"Dosya indirme hatası ({e.code})", status_code=e.code, error_code="HTTP_ERROR"
            )

        except urllib.error.URLError as e:
            raise HttpException(f"Bağlantı hatası: {e.reason}", status_code=0, error_code="NETWORK_ERROR")

    @classmethod
    def post_multipart(
        cls,
        url: str,
        fields: Dict[str, str],
        files: Dict[str, Tuple[str, bytes, str]],  # field_name -> (filename, bytes_data, content_type)
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 90.0,
    ) -> Dict[str, Any]:
        """Multipart/form-data ile dosya ve form alanlarını POST eder (OpenAI inpaint için)."""
        boundary = f"----AITextureBoundary{uuid.uuid4().hex}"
        body_parts = []

        # Form alanlarını ekle
        for field_name, value in fields.items():
            body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
            body_parts.append(
                f'Content-Disposition: form-data; name="{field_name}"\r\n\r\n'.encode("utf-8")
            )
            body_parts.append(f"{value}\r\n".encode("utf-8"))

        # Dosyaları ekle
        for field_name, (filename, file_bytes, content_type) in files.items():
            body_parts.append(f"--{boundary}\r\n".encode("utf-8"))
            body_parts.append(
                f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode("utf-8")
            )
            body_parts.append(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
            body_parts.append(file_bytes)
            body_parts.append(b"\r\n")

        body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))
        payload_bytes = b"".join(body_parts)

        req_headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "Blender-AITexturePainter/0.1.0",
        }
        if headers:
            req_headers.update(headers)

        request = urllib.request.Request(url, data=payload_bytes, headers=req_headers, method="POST")
        ssl_ctx = cls._create_ssl_context()

        try:
            with urllib.request.urlopen(request, timeout=timeout, context=ssl_ctx) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)

        except urllib.error.HTTPError as e:
            raw_err = e.read().decode("utf-8", errors="ignore")
            logger.error("HTTP Multipart Error", status=e.code, reason=e.reason, body=raw_err[:200])

            err_code = "HTTP_ERROR"
            if e.code in (401, 403):
                err_code = "AUTH_ERROR"
                msg = "API anahtarı geçersiz veya yetkisiz (401/403)."
            elif e.code == 429:
                err_code = "RATE_LIMIT"
                msg = "İstek limiti aşıldı (Rate Limit 429)."
            else:
                msg = f"Sunucu hatası ({e.code}): {e.reason}"

            try:
                err_json = json.loads(raw_err)
                if "error" in err_json and "message" in err_json["error"]:
                    msg = f"{msg} -> {err_json['error']['message']}"
            except Exception:
                pass

            raise HttpException(msg, status_code=e.code, error_code=err_code, response_body=raw_err)

        except urllib.error.URLError as e:
            raise HttpException(f"Bağlantı hatası: {e.reason}", status_code=0, error_code="NETWORK_ERROR")
