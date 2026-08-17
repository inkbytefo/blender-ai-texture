# Phase 5 — Polish & MVP Release (Plan)

> **Durum**: Planlandı  
> **Tahmini Süre**: 5 hafta  
> **Bağımlılık**: Phase 4  
> **Sürüm**: v0.1.0

---

## 5.1 Hedef

Reference image desteği, variation sistemi, UX cilalama, ikinci provider ve **ilk yayınlanabilir MVP** sürümü.

---

## 5.2 MVP Release Kriteri

```
✅ 1.  Blender açılır
✅ 2.  Addon aktif edilir
✅ 3.  Image Editor'da texture açılır
✅ 4.  Kullanıcı mask oluşturur (brush ile boyar)
✅ 5.  AI Texture Painter paneli açılır
✅ 6.  Prompt girilir
✅ 7.  Generate tıklanır
✅ 8.  Provider request oluşturulur, background'da çalışır
✅ 9.  Progress bar güncellenir
✅ 10. Result alınır (1-8 variation)
✅ 11. Result preview edilir
✅ 12. Mask dışındaki orijinal pikseller %100 korunur
✅ 13. Kullanıcı variation seçer
✅ 14. Apply tıklar → Blender texture güncellenir
✅ 15. Material viewport'ta güncellenir
✅ 16. Undo ile geri alınabilir
```

---

## 5.3 Oluşturulacak / Güncellenecek Dosyalar

```
ai_texture_painter/
├── ai/
│   ├── providers/
│   │   └── openai.py            ← [NEW] İkinci provider (OpenAI veya Gemini)
│   └── cache.py                 ← [NEW] Generation cache sistemi
│
├── texture/
│   └── history.py               ← [NEW] Undo/redo state stack
│
├── operators/
│   ├── generate.py              ← [MODIFY] Variation support
│   ├── apply.py                 ← [MODIFY] History push
│   ├── select_variation.py      ← [NEW] Variation seçim operatörü
│   └── show_error.py            ← [NEW] Error dialog operatörü
│
├── ui/
│   ├── panels.py                ← [MODIFY] Results panel, variation grid
│   └── properties.py            ← [MODIFY] Reference image property
```

---

## 5.4 Detaylı Görev Planı

| # | Görev | Dosya | Tahmini Süre | Öncelik |
|:--|:------|:------|:------------|:--------|
| 1 | Reference image conditioning | `operators/generate.py` | 3 gün | 🟡 Yüksek |
| 2 | Variation sistemi (çoklu sonuç) | `operators/generate.py` | 3 gün | 🔴 Kritik |
| 3 | Variation grid UI | `ui/panels.py` | 3 gün | 🔴 Kritik |
| 4 | Variation seçim operatörü | `operators/select_variation.py` | 1 gün | 🔴 Kritik |
| 5 | History/Undo stack | `texture/history.py` | 3 gün | 🟡 Yüksek |
| 6 | Cache sistemi | `ai/cache.py` | 3 gün | 🟢 Normal |
| 7 | Error dialog UX | `operators/show_error.py` | 2 gün | 🟡 Yüksek |
| 8 | İkinci provider impl | `ai/providers/openai.py` | 5 gün | 🟢 Normal |
| 9 | Kapsamlı test + bug fix | — | 10 gün | 🔴 Kritik |
| 10 | Kullanıcı kılavuzu yazımı | `docs/` | 3 gün | 🟡 Yüksek |

---

## 5.5 Sürüm Yayın Planı

1. **v0.1.0-alpha** → İç test (tüm Phase 1-5 tamamlandığında)
2. **v0.1.0-beta** → Sınırlı kullanıcı testi
3. **v0.1.0** → MVP Release
   - GitHub Release
   - Extensions Platform submission
   - Kullanıcı dokümantasyonu

---

*Önceki: [Phase 4 — First Real Provider](./PHASE_04_PLAN.md) | Sonraki: [Phase 6 — 3D Integration](./PHASE_06_PLAN.md)*
