# Phase 4 — First Real Provider (Plan)

> **Durum**: Planlandı  
> **Tahmini Süre**: 3 hafta  
> **Bağımlılık**: Phase 3

---

## 4.1 Hedef

En az bir gerçek AI provider (Flux veya OpenAI) ile çalışan generation. Background threading ile Blender UI donmadan generation yapılabilmesi.

---

## 4.2 Milestone 4 Kriteri

```
✅ Gerçek AI provider ile texture generation çalışıyor
✅ Generation sırasında Blender UI donmuyor (threading)
✅ Progress bar güncelleniyor
✅ Hata durumları kullanıcıya gösteriliyor (timeout, auth, network)
✅ API key preferences'tan okunuyor
✅ Extension wheel olarak httpx bundle ediliyor
```

---

## 4.3 Oluşturulacak Dosyalar

```
ai_texture_painter/
├── ai/
│   ├── transport/
│   │   ├── __init__.py          ← [NEW]
│   │   └── http.py              ← [NEW] httpx tabanlı HTTP client
│   │
│   └── providers/
│       └── flux.py              ← [NEW] Flux/Replicate provider (veya openai.py)
│
├── operators/
│   └── generate.py              ← [MODIFY] Background threading ekleme
│
├── wheels/                      ← [NEW] httpx + bağımlılık wheel dosyaları
│   ├── httpx-0.27.x-py3-none-any.whl
│   ├── httpcore-1.x.x-py3-none-any.whl
│   └── ... (diğer bağımlılıklar)
│
├── blender_manifest.toml        ← [MODIFY] wheels listesi ekleme
```

---

## 4.4 Detaylı Görev Planı

| # | Görev | Dosya | Tahmini Süre | Öncelik |
|:--|:------|:------|:------------|:--------|
| 1 | HTTP transport layer | `ai/transport/http.py` | 3 gün | 🔴 Kritik |
| 2 | Wheel bundling (httpx + deps) | `wheels/` | 2 gün | 🔴 Kritik |
| 3 | Manifest güncelleme | `blender_manifest.toml` | 0.5 gün | 🔴 Kritik |
| 4 | Background threading | `operators/generate.py` | 3 gün | 🔴 Kritik |
| 5 | Progress reporting (timer) | `operators/generate.py` | 2 gün | 🟡 Yüksek |
| 6 | First provider impl | `ai/providers/flux.py` | 5 gün | 🔴 Kritik |
| 7 | Error handling (network) | `ai/transport/http.py` | 2 gün | 🟡 Yüksek |
| 8 | Error UX (popup) | `operators/generate.py` | 1 gün | 🟡 Yüksek |
| 9 | Integration test | — | 3 gün | 🟡 Yüksek |

---

## 4.5 Kritik Teknik Detaylar

### Threading Pattern

```python
# 1. Operator.execute() → background thread başlat
# 2. threading.Thread → HTTP request (bpy kullanMAZ)
# 3. bpy.app.timers.register → polling callback (main thread)
# 4. Timer callback → state kontrol → UI güncelle
# 5. Tamamlandığında → preview image güncelle
```

### Provider Seçimi

İlk gerçek provider olarak **Flux (Replicate API)** önerilir:
- Inpaint desteği güçlü
- API basit ve iyi dökümante
- Maliyet-performans dengesi uygun
- Mask desteği doğrudan mevcut

Alternatif: **OpenAI GPT-Image-1** (DALL-E 3 inpaint)

---

*Önceki: [Phase 3 — AI Abstraction](./PHASE_03_PLAN.md) | Sonraki: [Phase 5 — MVP Release](./PHASE_05_PLAN.md)*
