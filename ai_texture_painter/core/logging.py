# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Structured logging sistemi.

API key ve secret değerleri otomatik olarak maskelenir.
Blender console'a [AI_TEXTURE.modül] formatında çıktı verir.
"""

import logging
from typing import Any

# ──────────────────────────────────────────────
# Sabitler
# ──────────────────────────────────────────────

LOG_PREFIX = "AI_TEXTURE"

# Bu kelimeler log argümanlarında bulunursa değerleri maskelenir
_SENSITIVE_KEYS = frozenset({
    "api_key",
    "api-key",
    "apikey",
    "secret",
    "token",
    "password",
    "authorization",
    "bearer",
    "credential",
})

# Modül seviyesinde log level (preferences'tan güncellenir)
_current_level = logging.INFO


# ──────────────────────────────────────────────
# Logger sınıfı
# ──────────────────────────────────────────────

class AITextureLogger:
    """Addon için structured, güvenli logger.

    Kullanım:
        logger = get_logger("ai.provider")
        logger.info("Request started", provider="flux", resolution="1024x1024")
        logger.error("Failed", error_code="TIMEOUT")
    """

    def __init__(self, module_name: str):
        self._name = f"{LOG_PREFIX}.{module_name}"
        self._logger = logging.getLogger(self._name)

        # Handler zaten ekliyse tekrar ekleme
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "[%(levelname)s] %(name)s: %(message)s"
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)

        self._logger.setLevel(_current_level)

    # ── Public log metodları ──

    def info(self, message: str, **kwargs: Any) -> None:
        """INFO seviyesinde log."""
        self._log(logging.INFO, message, **kwargs)

    def debug(self, message: str, **kwargs: Any) -> None:
        """DEBUG seviyesinde log."""
        self._log(logging.DEBUG, message, **kwargs)

    def warning(self, message: str, **kwargs: Any) -> None:
        """WARNING seviyesinde log."""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        """ERROR seviyesinde log."""
        self._log(logging.ERROR, message, **kwargs)

    # ── İç yardımcı ──

    def _log(self, level: int, message: str, **kwargs: Any) -> None:
        """Sanitize edilmiş structured log."""
        sanitized = _sanitize_kwargs(kwargs)
        extra_str = " ".join(f"{k}={v}" for k, v in sanitized.items())
        full_message = f"{message} {extra_str}".strip()
        self._logger.log(level, full_message)


# ──────────────────────────────────────────────
# Modül-seviye fonksiyonlar
# ──────────────────────────────────────────────

def get_logger(module_name: str) -> AITextureLogger:
    """Modül adına göre logger oluşturur.

    Args:
        module_name: Modül yolu (ör: "ai.provider", "texture.mask")

    Returns:
        AITextureLogger instance
    """
    return AITextureLogger(module_name)


def set_log_level(level_name: str) -> None:
    """Global log seviyesini ayarlar.

    Args:
        level_name: "DEBUG", "INFO", "WARNING", veya "ERROR"
    """
    global _current_level

    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
    }

    _current_level = level_map.get(level_name.upper(), logging.INFO)

    # Mevcut tüm AI_TEXTURE logger'larını güncelle
    for name, logger in logging.Logger.manager.loggerDict.items():
        if isinstance(logger, logging.Logger) and name.startswith(LOG_PREFIX):
            logger.setLevel(_current_level)


# ──────────────────────────────────────────────
# Güvenlik
# ──────────────────────────────────────────────

def _sanitize_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    """Log argümanlarından hassas verileri maskeler.

    API key, token, password gibi argümanların değerlerini
    '***REDACTED***' ile değiştirir.
    """
    sanitized = {}
    for key, value in kwargs.items():
        key_lower = key.lower().replace("-", "_")
        if any(sensitive in key_lower for sensitive in _SENSITIVE_KEYS):
            sanitized[key] = "***REDACTED***"
        else:
            sanitized[key] = value
    return sanitized
