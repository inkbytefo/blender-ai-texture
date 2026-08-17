# Phase 2 — Image Pipeline (Plan)

> **Durum**: Planlandı  
> **Tahmini Süre**: 5 hafta  
> **Bağımlılık**: Phase 1 ✅

---

## 2.1 Hedef

Blender image'ları okunabiliyor, mask çıkarılabiliyor, compositing yapılabiliyor, preview gösterilebiliyor ve apply/cancel workflow'u çalışıyor.

> **Temel İlke**: "AI hiçbir zaman kullanıcının istemediği alanları değiştirmemelidir."

---

## 2.2 Milestone 2 Kriteri

```
✅ Image Editor'da aktif texture otomatik tespit ediliyor
✅ Brush ile boyanan mask doğru şekilde çıkarılıyor
✅ Bir test image, mask ile doğru şekilde composit ediliyor
✅ Mask dışı pikseller %100 korunuyor (protected pixel guarantee)
✅ Preview image gösterilebiliyor
✅ Apply ile texture güncellenebiliyor
✅ Cancel ile orijinale dönülebiliyor
```

---

## 2.3 Oluşturulacak / Güncellenecek Dosyalar

### Yeni Dosyalar

```
ai_texture_painter/
├── blender/
│   ├── image_adapter.py         ← [NEW] bpy.types.Image ↔ NumPy wrapper
│   ├── uv_adapter.py           ← [NEW] UV koordinat erişimi
│   └── material_adapter.py     ← [NEW] Material/texture node erişimi
│
├── texture/
│   ├── mask.py                  ← [NEW] Mask çıkarma, normalize, feather
│   ├── composite.py             ← [NEW] Mask-protected compositing engine
│   ├── resolution.py            ← [NEW] Resolution yönetimi ve crop/place
│   └── image_manager.py         ← [NEW] Preview image ve backup yönetimi
│
├── operators/
│   ├── apply.py                 ← [NEW] Apply operator
│   └── cancel.py                ← [NEW] Cancel operator
```

### Güncellenecek Dosyalar

```
├── operators/generate.py        ← [MODIFY] Gerçek pipeline entegrasyonu
├── ui/panels.py                 ← [MODIFY] Mask status, preview, apply/cancel UI
├── core/state.py                ← [MODIFY] Pixel data alanları aktif edilecek
```

---

## 2.4 Detaylı Görev Planı

| # | Görev | Dosya | Tahmini Süre | Öncelik |
|:--|:------|:------|:------------|:--------|
| 1 | Blender Image Adapter | `blender/image_adapter.py` | 3 gün | 🔴 Kritik |
| 2 | Aktif image tespiti | `blender/image_adapter.py` | 2 gün | 🔴 Kritik |
| 3 | Mask extraction (brush) | `texture/mask.py` | 3 gün | 🔴 Kritik |
| 4 | Mask normalization | `texture/mask.py` | 2 gün | 🔴 Kritik |
| 5 | Mask feather/dilate/erode | `texture/mask.py` | 2 gün | 🟡 Yüksek |
| 6 | Compositing engine | `texture/composite.py` | 3 gün | 🔴 Kritik |
| 7 | Protected pixel doğrulama | `texture/composite.py` | 2 gün | 🔴 Kritik |
| 8 | Resolution manager | `texture/resolution.py` | 3 gün | 🟡 Yüksek |
| 9 | Preview image yönetimi | `texture/image_manager.py` | 2 gün | 🔴 Kritik |
| 10 | Image backup / restore | `texture/image_manager.py` | 1 gün | 🔴 Kritik |
| 11 | Apply operator | `operators/apply.py` | 2 gün | 🔴 Kritik |
| 12 | Cancel operator | `operators/cancel.py` | 1 gün | 🔴 Kritik |
| 13 | UI: Mask status gösterimi | `ui/panels.py` | 1 gün | 🟡 Yüksek |
| 14 | UI: Apply/Cancel butonları | `ui/panels.py` | 1 gün | 🟡 Yüksek |
| 15 | Viewport güncelleme | `blender/material_adapter.py` | 2 gün | 🟡 Yüksek |

---

## 2.5 Kritik Teknik Detaylar

### Compositing Formülü

```python
result[pixel] = original[pixel] × (1 - mask[pixel]) + generated[pixel] × mask[pixel]
```

- Mask = 0 → piksel orijinalden gelir (protected)
- Mask = 1 → piksel AI çıktısından gelir (editable)
- Mask = 0.5 → %50 blend

### Mask Standardı

```
Format:    Grayscale (single channel)
Veri tipi: float32
Aralık:    0.0 — 1.0
Boyut:     Texture ile aynı çözünürlük
```

### NumPy Dönüşümü

```python
# Blender Image → NumPy
pixels = np.array(img.pixels[:]).reshape((height, width, 4))

# NumPy → Blender Image
img.pixels[:] = array.flatten()
img.update()
```

---

## 2.6 Test Planı

- Protected pixel doğrulaması (mask=0 olan pikseller değişmemeli)
- Compositing matematiksel doğruluk (bilinçli test input'ları ile)
- Mask normalization (farklı input format'larını test)
- Resolution crop/place round-trip (kırp → yerleştir → orijinal boyut)
- Apply/Cancel state geçişleri
- Preview image oluşturma/temizleme

---

*Önceki: [Phase 1 — Foundation](./PHASE_01_COMPLETE.md) | Sonraki: [Phase 3 — AI Abstraction](./PHASE_03_PLAN.md)*
