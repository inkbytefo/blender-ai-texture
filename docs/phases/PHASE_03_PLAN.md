# Phase 3 — AI Abstraction (Plan)

> **Durum**: Planlandı  
> **Tahmini Süre**: 3 hafta  
> **Bağımlılık**: Phase 2

---

## 3.1 Hedef

Provider interface, request/response modeli, capability sistemi ve **MockProvider** ile uçtan uca pipeline'ı test edebilir hale getirmek.

> **Önemli**: Gerçek AI provider bağlamadan önce MockProvider oluşturulmalıdır. Böylece tüm pipeline (mask → generation → composite → preview → apply) API key olmadan test edilebilir.

---

## 3.2 Milestone 3 Kriteri

```
✅ MockProvider ile fake generation yapılabiliyor
✅ UI'da desteklenmeyen özellikler otomatik gizleniyor (capability-aware UI)
✅ Request validation çalışıyor (prompt boş, mask eksik vb.)
✅ Tüm pipeline Mock ile uçtan uca çalışıyor:
   Mask → MockProvider → Composite → Preview → Apply
```

---

## 3.3 Oluşturulacak Dosyalar

```
ai_texture_painter/
├── ai/
│   ├── provider.py              ← [NEW] AIProvider abstract base class
│   ├── registry.py              ← [NEW] Provider registry (singleton)
│   ├── request.py               ← [NEW] AIRequest dataclass + validation
│   ├── response.py              ← [NEW] AIResponse dataclass
│   │
│   └── providers/
│       ├── __init__.py          ← [NEW]
│       └── mock.py              ← [NEW] MockProvider — test pattern üretimi
```

### Güncellenecek Dosyalar

```
├── ui/panels.py                 ← [MODIFY] Capability-aware UI (koşullu alan gösterimi)
├── operators/generate.py        ← [MODIFY] Provider üzerinden generation
├── __init__.py                  ← [MODIFY] Provider registry başlatma
```

---

## 3.4 Detaylı Görev Planı

| # | Görev | Dosya | Tahmini Süre | Öncelik |
|:--|:------|:------|:------------|:--------|
| 1 | AIProvider ABC | `ai/provider.py` | 2 gün | 🔴 Kritik |
| 2 | Capability enum (Phase 1'de mevcut) | `ai/capabilities.py` | — | ✅ Tamamlandı |
| 3 | AIRequest dataclass | `ai/request.py` | 2 gün | 🔴 Kritik |
| 4 | AIResponse dataclass | `ai/response.py` | 1 gün | 🔴 Kritik |
| 5 | ProviderRegistry singleton | `ai/registry.py` | 2 gün | 🔴 Kritik |
| 6 | MockProvider implementasyonu | `ai/providers/mock.py` | 3 gün | 🔴 Kritik |
| 7 | Request validation | `ai/request.py` | 2 gün | 🟡 Yüksek |
| 8 | Capability-aware UI | `ui/panels.py` | 2 gün | 🟡 Yüksek |
| 9 | Generate operator → provider entegrasyonu | `operators/generate.py` | 2 gün | 🔴 Kritik |

---

## 3.5 Kritik Tasarım

### AIProvider Interface

```python
class AIProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def capabilities(self) -> set[Capability]: ...

    @abstractmethod
    def generate(self, request: AIRequest) -> AIResponse: ...

    def supports(self, cap: Capability) -> bool:
        return cap in self.capabilities
```

### MockProvider Davranışı

- Checkerboard pattern veya gradient üretir (gerçek AI kullanmaz)
- Tüm capability'leri destekler
- `generate()` 1-2 saniye sleep ile gerçekçi gecikme simülasyonu
- Seed ile deterministic sonuçlar

---

*Önceki: [Phase 2 — Image Pipeline](./PHASE_02_PLAN.md) | Sonraki: [Phase 4 — First Real Provider](./PHASE_04_PLAN.md)*
