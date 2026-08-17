# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Provider Registry Module.

AI sağlayıcılarının merkezi kaydını, sorgulanmasını ve
aktif provider'ın seçilmesini yöneten singleton sınıfı içerir.
"""

from typing import Dict, Optional, List
import threading

from .provider import AIProvider
from .capabilities import Capability
from ..core.logging import get_logger
from ..core.config import get_addon_preferences

logger = get_logger("ai.registry")


class ProviderRegistry:
    """Tüm AI provider sınıflarını tutan singleton kayıt defteri."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ProviderRegistry, cls).__new__(cls)
                cls._instance._providers: Dict[str, AIProvider] = {}
            return cls._instance

    def register(self, provider: AIProvider) -> None:
        """Yeni bir provider kaydeder."""
        key = provider.name.lower()
        self._providers[key] = provider
        logger.info("AI Provider registered", provider=provider.name, display_name=provider.display_name)

    def get(self, name: str) -> Optional[AIProvider]:
        """İsme göre provider döndürür."""
        return self._providers.get(name.lower())

    def get_active(self) -> AIProvider:
        """Kullanıcı tercihlerinde seçili olan aktif provider'ı döndürür.

        Eğer seçili provider bulunamazsa varsayılan olarak 'mock' döner.
        """
        prefs = get_addon_preferences()
        provider_key = getattr(prefs, "active_provider", "MOCK").lower() if prefs else "mock"

        provider = self.get(provider_key)
        if provider is None:
            # Fallback to mock
            provider = self.get("mock")

        if provider is None:
            raise RuntimeError("Hiçbir AI Provider (Mock dahil) kayıtlı değil!")

        return provider

    def list_providers(self) -> List[AIProvider]:
        """Kayıtlı tüm provider'ların listesini döndürür."""
        return list(self._providers.values())

    def get_providers_for_capability(self, capability: Capability) -> List[AIProvider]:
        """Belirli bir capability'yi destekleyen provider'ları filtreler."""
        return [p for p in self._providers.values() if p.supports(capability)]

    def clear(self) -> None:
        """Tüm kayıtları temizler (testler için)."""
        self._providers.clear()


# ── Global singleton erişim fonksiyonları ──

def get_registry() -> ProviderRegistry:
    """ProviderRegistry singleton nesnesini döndürür."""
    return ProviderRegistry()


def get_active_provider() -> AIProvider:
    """Aktif AI sağlayıcısını döndürür."""
    return ProviderRegistry().get_active()
