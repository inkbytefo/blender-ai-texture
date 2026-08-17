# 08 — Geliştirme Kılavuzu

> Kodlama kuralları, proje yapısı, Git workflow, test stratejisi ve CI/CD.

---

## 8.1 Geliştirme Ortamı

### Gereksinimler

| Araç | Sürüm | Amaç |
|:-----|:------|:-----|
| **Blender** | 5.2 LTS | Ana geliştirme ve test ortamı |
| **Python** | 3.13 (Blender bundled) | Addon kodu |
| **Git** | 2.40+ | Versiyon kontrolü |
| **VS Code / IDE** | Güncel | Kod editörü |
| **fake-bpy-module** | 5.x uyumlu | IDE otomatik tamamlama |

### IDE Kurulumu

```bash
# fake-bpy-module ile IDE desteği
pip install fake-bpy-module-latest

# VS Code ayarları
# .vscode/settings.json
{
    "python.analysis.extraPaths": [
        "path/to/blender/scripts/modules"
    ],
    "python.analysis.typeCheckingMode": "basic"
}
```

### Blender'da Addon Test Etme

```bash
# Extension olarak yükleme (development mode)
# Blender → Preferences → Extensions → Install from Disk

# Veya symlink ile geliştirme
# Windows:
mklink /D "%APPDATA%\Blender\5.2\extensions\ai_texture_painter" "C:\Dev\InkbytefoProjects\aiimagegenerator\ai_texture_painter"

# Linux/Mac:
ln -s /path/to/dev/ai_texture_painter ~/.config/blender/5.2/extensions/ai_texture_painter
```

### Hızlı Reload

```python
# Blender scripting console'da addon'u yeniden yükle
import importlib
import ai_texture_painter
importlib.reload(ai_texture_painter)

# Veya Blender → Preferences → Extensions → Reload
```

---

## 8.2 Kodlama Kuralları

### 10 Temel Kural

| # | Kural | Açıklama |
|:--|:------|:---------|
| 1 | **Mevcut olmayan sistemi varsayma** | Proje boşsa önce minimal working addon oluştur |
| 2 | **Büyük kod yazmaktan kaçın** | Her aşamadan sonra sistem çalışır durumda kalmalı |
| 3 | **AI provider kodunu UI'ya gömme** | Katmanlı mimariyi koru |
| 4 | **Compositing'i provider'dan ayır** | Texture işleme bağımsız olmalı |
| 5 | **Protected pixel garantisini local'de uygula** | Provider'a güvenme |
| 6 | **API key hard-code etme** | Environment variable veya preferences |
| 7 | **Main-thread kurallarını ihlal etme** | bpy = sadece main thread |
| 8 | **Mock provider olmadan AI UI geliştirme** | MockProvider first |
| 9 | **Kod tekrarını azalt ama erken abstraction yapma** | YAGNI |
| 10 | **Her önemli karar için documentation ekle** | Karar logları |

### Python Style Guide

```python
# ── Naming Conventions ──

# Modüller: snake_case
import ai_texture_painter.texture.composite

# Sınıflar: PascalCase
class TextureCompositor:
    pass

# Blender sınıfları: ADDON_OT/PT/MT_ prefix
class AITEXTURE_OT_generate(bpy.types.Operator):
    pass

class AITEXTURE_PT_main_panel(bpy.types.Panel):
    pass

# Fonksiyonlar ve değişkenler: snake_case
def apply_feather(mask: np.ndarray, radius: int) -> np.ndarray:
    pass

# Sabitler: UPPER_SNAKE_CASE
MAX_TEXTURE_SIZE = 8192
DEFAULT_GENERATION_SIZE = 1024

# ── Type Hints ──
# Python 3.13 type hints kullan
def get_pixels(image_name: str) -> np.ndarray:
    pass

def composite(
    original: np.ndarray,
    generated: np.ndarray,
    mask: np.ndarray,
) -> np.ndarray:
    pass

# ── Docstrings ──
def extract_mask(context) -> np.ndarray:
    """Image Editor'daki aktif mask'ı çıkarır.
    
    Args:
        context: Blender context
    
    Returns:
        Normalized grayscale mask (0.0-1.0)
    
    Raises:
        ValueError: Mask bulunamadığında
    """
    pass
```

### Import Sırası

```python
# 1. Standard library
import os
import time
import threading
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

# 2. Third-party (wheel olarak bundled)
import numpy as np
import httpx

# 3. Blender API
import bpy
import bmesh
from mathutils import Vector, Matrix

# 4. Local imports
from ..core.config import get_config
from ..core.logging import get_logger
from ..ai.provider import AIProvider
from ..texture.composite import TextureCompositor
```

---

## 8.3 Git Workflow

### Branch Stratejisi

```mermaid
gitgraph
    commit id: "init"
    branch develop
    checkout develop
    commit id: "Phase 1 start"
    
    branch feature/addon-skeleton
    checkout feature/addon-skeleton
    commit id: "manifest.toml"
    commit id: "register/unregister"
    checkout develop
    merge feature/addon-skeleton
    
    branch feature/mask-system
    checkout feature/mask-system
    commit id: "mask extraction"
    commit id: "mask normalization"
    checkout develop
    merge feature/mask-system
    
    branch feature/compositing
    checkout feature/compositing
    commit id: "compositor"
    commit id: "protected pixels"
    checkout develop
    merge feature/compositing
    
    checkout main
    merge develop tag: "v0.1.0-alpha"
```

### Branch İsimlendirme

```
main                          # Kararlı sürüm
develop                       # Geliştirme dalı
feature/addon-skeleton        # Yeni özellik
feature/mask-system
feature/ai-provider-flux
bugfix/compositing-edge-case  # Hata düzeltme
hotfix/api-key-leak           # Acil düzeltme
release/v0.1.0                # Sürüm hazırlığı
```

### Commit Mesajları

```
feat: add mask extraction from Image Editor brush
fix: protect pixels outside mask boundary
refactor: extract compositing logic to separate module
docs: update API reference for AIRequest model
test: add unit tests for mask normalization
chore: bundle httpx wheel for Windows
perf: optimize pixel compositing with numpy vectorization
```

### .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
*.egg-info/
dist/
build/
*.egg

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Blender
*.blend1
*.blend2

# Secrets
.env
*.key
api_keys.json

# Cache
.cache/
*.npz

# Temporary
tmp/
temp/

# Build artifacts
*.zip
releases/
```

---

## 8.4 Test Stratejisi

### Test Piramidi

```
         ┌──────────┐
         │  Manual   │  ← Blender'da elle test
         │  Testing  │
         ├──────────┤
         │ Integration│  ← Provider + Blender API
         │   Tests   │
         ├──────────┤
         │          │
         │  Unit    │  ← Mask, compositing, request
         │  Tests   │
         │          │
         └──────────┘
```

### Unit Tests

```python
# tests/test_composite.py

import numpy as np
import pytest
from ai_texture_painter.texture.composite import TextureCompositor

class TestTextureCompositor:
    
    def test_basic_compositing(self):
        """Temel compositing: mask=1 alanlar generated'dan gelir"""
        original = np.zeros((4, 4, 4), dtype=np.float32)
        generated = np.ones((4, 4, 4), dtype=np.float32)
        mask = np.ones((4, 4), dtype=np.float32)
        
        result = TextureCompositor.composite(original, generated, mask)
        
        np.testing.assert_array_almost_equal(result, generated)
    
    def test_protected_pixels(self):
        """Mask=0 alanlar orijinalden korunur"""
        original = np.full((4, 4, 4), 0.5, dtype=np.float32)
        generated = np.ones((4, 4, 4), dtype=np.float32)
        mask = np.zeros((4, 4), dtype=np.float32)
        
        result = TextureCompositor.composite(original, generated, mask)
        
        np.testing.assert_array_almost_equal(result, original)
    
    def test_partial_mask(self):
        """Kısmi mask: doğru interpolasyon"""
        original = np.zeros((4, 4, 4), dtype=np.float32)
        generated = np.ones((4, 4, 4), dtype=np.float32)
        mask = np.full((4, 4), 0.5, dtype=np.float32)
        
        result = TextureCompositor.composite(original, generated, mask)
        
        expected = np.full((4, 4, 4), 0.5, dtype=np.float32)
        np.testing.assert_array_almost_equal(result, expected)
    
    def test_protected_pixel_verification(self):
        """Protected pixel doğrulaması çalışır"""
        original = np.random.rand(10, 10, 4).astype(np.float32)
        generated = np.random.rand(10, 10, 4).astype(np.float32)
        mask = np.zeros((10, 10), dtype=np.float32)
        mask[3:7, 3:7] = 1.0
        
        result = TextureCompositor.composite(original, generated, mask)
        
        assert TextureCompositor.verify_protected_pixels(
            original, result, mask
        )


class TestMaskOperations:
    
    def test_normalize_range(self):
        """Mask 0-1 aralığında normalize edilir"""
        from ai_texture_painter.texture.mask import normalize_mask
        
        raw_mask = np.array([[0, 128, 255]], dtype=np.uint8)
        normalized = normalize_mask(raw_mask)
        
        assert normalized.min() >= 0.0
        assert normalized.max() <= 1.0
        assert normalized.dtype == np.float32
    
    def test_feather_smooths_edges(self):
        """Feather mask kenarlarını yumuşatır"""
        from ai_texture_painter.texture.mask import apply_feather
        
        mask = np.zeros((20, 20), dtype=np.float32)
        mask[5:15, 5:15] = 1.0
        
        feathered = apply_feather(mask, radius=3)
        
        # Orijinal sert kenar: 0→1 geçişi 1 pixel
        # Feathered: gradual geçiş
        assert feathered[5, 4] > 0.0  # Kenar yumuşamış
        assert feathered[5, 4] < 1.0  # Ama tam beyaz değil


class TestAIRequest:
    
    def test_validation_requires_prompt(self):
        """FILL operation için prompt gerekli"""
        from ai_texture_painter.ai.request import AIRequest, AIOperation
        
        request = AIRequest(
            operation=AIOperation.FILL,
            prompt="",
            width=1024,
            height=1024,
        )
        
        errors = request.validate()
        assert any("Prompt" in e for e in errors)
    
    def test_validation_requires_mask_for_fill(self):
        """FILL operation için mask gerekli"""
        from ai_texture_painter.ai.request import AIRequest, AIOperation
        
        request = AIRequest(
            operation=AIOperation.FILL,
            prompt="test",
            width=1024,
            height=1024,
            mask=None,
        )
        
        errors = request.validate()
        assert any("mask" in e.lower() for e in errors)
    
    def test_request_hash_deterministic(self):
        """Aynı request aynı hash üretir"""
        from ai_texture_painter.ai.request import AIRequest, AIOperation
        
        r1 = AIRequest(
            operation=AIOperation.FILL,
            prompt="test",
            width=1024, height=1024,
            seed=42,
        )
        r2 = AIRequest(
            operation=AIOperation.FILL,
            prompt="test",
            width=1024, height=1024,
            seed=42,
        )
        
        assert r1.to_hash() == r2.to_hash()
```

### Visual Tests

```python
# tests/test_visual.py

class TestVisualCompositing:
    
    def test_visual_compositing_result(self):
        """Görsel compositing sonucu beklenen ile eşleşir"""
        # Test fixtures
        original = load_test_image("test_original.png")
        mask = load_test_image("test_mask.png", grayscale=True)
        generated = load_test_image("test_generated.png")
        expected = load_test_image("test_expected_result.png")
        
        result = TextureCompositor.composite(original, generated, mask)
        
        # Piksel farkı toleransı
        diff = np.abs(result - expected)
        assert diff.max() < 0.01, f"Max pixel diff: {diff.max()}"
```

### Test Çalıştırma

```bash
# Unit testleri çalıştır (Blender dışında)
python -m pytest tests/ -v

# Blender içinde integration test
blender --background --python tests/run_blender_tests.py

# Coverage raporu
python -m pytest tests/ --cov=ai_texture_painter --cov-report=html
```

---

## 8.5 Logging

### Structured Logging

```python
# core/logging.py

import logging
import time

class AITextureLogger:
    """Addon için structured logging"""
    
    PREFIX = "AI_TEXTURE"
    
    def __init__(self, module_name: str):
        self.logger = logging.getLogger(f"{self.PREFIX}.{module_name}")
        self._setup_handler()
    
    def _setup_handler(self):
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '[%(levelname)s] %(name)s: %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def info(self, message: str, **kwargs):
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.info(f"{message} {extra}".strip())
    
    def error(self, message: str, **kwargs):
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.error(f"{message} {extra}".strip())
    
    def debug(self, message: str, **kwargs):
        extra = " ".join(f"{k}={v}" for k, v in kwargs.items())
        self.logger.debug(f"{message} {extra}".strip())

def get_logger(module_name: str) -> AITextureLogger:
    return AITextureLogger(module_name)
```

### Log Kullanımı

```python
logger = get_logger("ai.provider")

logger.info("AI request started",
    provider="flux",
    operation="inpaint",
    resolution="1024x1024")

logger.info("Generation completed",
    time_seconds=2.3,
    variation_count=4)

logger.error("Generation failed",
    provider="openai",
    error_code="TIMEOUT",
    retry=True)
```

### Log Güvenlik Kuralları

```
✅ LOG: provider name, operation, resolution, timing
✅ LOG: error codes, error messages
✅ LOG: cache hits/misses
❌ ASLA LOG: API keys, API secrets
❌ ASLA LOG: kullanıcı prompt içeriği (gizlilik)
❌ ASLA LOG: image pixel data
```

---

## 8.6 Proje Yapılandırması

### pyproject.toml (Test & Linting)

```toml
[project]
name = "ai-texture-painter"
version = "0.1.0"
requires-python = ">=3.13"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]

[tool.ruff]
line-length = 88
target-version = "py313"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP"]
ignore = ["E501"]  # Line too long

[tool.mypy]
python_version = "3.13"
ignore_missing_imports = true
```

---

## 8.7 Dependency Yönetimi

### Bundled Wheels

```bash
# Wheels indirme (cross-platform)
pip download httpx --dest wheels/ --python-version 3.13 --only-binary=:all:

# Veya Blender Extension Builder kullanarak
# pyproject.toml'da bağımlılıkları tanımla, otomatik bundle et
```

### Bağımlılık Listesi

| Paket | Sürüm | Amaç | Platform |
|:------|:------|:-----|:---------|
| `httpx` | 0.27+ | Async HTTP client | any |
| `httpcore` | 1.0+ | httpx dependency | any |
| `anyio` | 4.4+ | httpx dependency | any |
| `certifi` | 2024+ | SSL certificates | any |
| `h11` | 0.14+ | HTTP/1.1 parser | any |
| `idna` | 3.7+ | Domain name parsing | any |
| `sniffio` | 1.3+ | Async library detection | any |

### Built-in (Blender ile gelen)

- `numpy` — Pixel manipülasyon
- `mathutils` — Vektör/matris işlemleri
- `bmesh` — Mesh veri erişimi
- `bpy` — Blender Python API

---

*Sonraki bölüm: [09 — API Referansı](./09-API_REFERENCE.md)*
