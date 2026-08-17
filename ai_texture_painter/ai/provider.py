# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
AI Provider Abstract Base Class.

Tüm AI sağlayıcılarının (Mock, OpenAI, Flux, Gemini, Local vb.)
uygulaması gereken ortak arayüzü tanımlar.
"""

from abc import ABC, abstractmethod
from typing import Set, List

from .capabilities import Capability
from .request import AIRequest
from .response import AIResponse


class AIProvider(ABC):
    """AI provider temel sınıfı.

    Tüm sağlayıcılar bu sınıfı miras alarak `generate` metodunu ve
    desteklediği capability setini tanımlar.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider tekil sistem adı (küçük harflerle, ör: 'mock', 'flux', 'openai')."""
        pass

    @property
    @abstractmethod
    def display_name(self) -> str:
        """UI'da gösterilecek etiket adı (ör: 'Mock (Test)', 'Flux (Replicate)')."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> Set[Capability]:
        """Provider'ın desteklediği özellikler kümesi."""
        pass

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse:
        """İsteği işleyip sonuçları döndürür."""
        pass

    def validate_config(self) -> bool:
        """Provider için gerekli konfigürasyonun (ör: API anahtarı) geçerli olup olmadığını denetler."""
        return True

    def supports(self, capability: Capability) -> bool:
        """Belirli bir capability'nin bu provider tarafından desteklenip desteklenmediğini sorgular."""
        return capability in self.capabilities

    def get_models(self) -> List[str]:
        """Provider'ın sunduğu model isimleri listesini döndürür."""
        return []
