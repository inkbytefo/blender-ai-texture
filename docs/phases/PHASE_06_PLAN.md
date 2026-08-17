# Phase 6 — 3D Integration (Plan)

> **Durum**: Planlandı  
> **Tahmini Süre**: 6 hafta  
> **Bağımlılık**: Phase 5 (MVP)  
> **Sürüm**: v0.2.0

---

## 6.1 Hedef

3D viewport'tan face seçimi → otomatik UV mapping → texture generation. Kullanıcının UV layout bilmesine gerek kalmadan 3D'den doğrudan texture düzenleyebilmesi.

---

## 6.2 Milestone 6 Kriteri

```
✅ 3D viewport'ta face seçimi yapılabiliyor
✅ Seçili face'ler UV üzerinde mask'a dönüştürülüyor
✅ 3D'den başlatılan generation doğru texture bölgesini güncelliyor
✅ Kullanıcı UV layout bilmek zorunda kalmıyor
✅ 3D Viewport context (depth, normal) generation'a aktarılabiliyor
```

---

## 6.3 Oluşturulacak Dosyalar

```
ai_texture_painter/
├── blender/
│   ├── uv_adapter.py            ← [MODIFY] Face → UV mask dönüşümü
│   ├── viewport_adapter.py      ← [NEW] Viewport render, depth, normal capture
│   └── mesh_adapter.py          ← [NEW] Mesh/face selection erişimi
│
├── texture/
│   └── uv_mask.py               ← [NEW] UV-space mask oluşturma (rasterize)
│
├── operators/
│   ├── generate_3d.py           ← [NEW] 3D viewport'tan generation başlatma
│   └── paint_from_view.py       ← [NEW] Viewport'tan direkt paint (V2)
│
├── ui/
│   └── panels_3d.py             ← [NEW] 3D Viewport N-panel
```

---

## 6.4 Detaylı Görev Planı

| # | Görev | Tahmini Süre | Öncelik |
|:--|:------|:------------|:--------|
| 1 | Selected faces detection (bmesh) | 3 gün | 🟡 Yüksek |
| 2 | UV koordinat extraction | 5 gün | 🟡 Yüksek |
| 3 | Face selection → UV-space mask rasterization | 5 gün | 🟡 Yüksek |
| 4 | Viewport context capture (depth, normal) | 7 gün | 🟢 Normal |
| 5 | UV bounding box → texture region mapping | 5 gün | 🟡 Yüksek |
| 6 | Paint from view (3D → 2D projection) | 10 gün | 🟡 Yüksek |
| 7 | 3D Viewport panel | 3 gün | 🟡 Yüksek |
| 8 | Integration test (3D → 2D pipeline) | 5 gün | 🟡 Yüksek |

---

## 6.5 Kritik Teknik Zorluklar

### Face → UV Mask Rasterization

```
3D Viewport: Kullanıcı face seçer
    ↓
bmesh: Seçili face'lerin UV koordinatları
    ↓
UV → Pixel: UV koordinatlarını texture pixel'lerine map'le
    ↓
Rasterize: UV poligonlarını mask'a doldur
    ↓
Mask: Standart float32 (0-1) mask
    ↓
Compositing pipeline'a gönder
```

### Paint from View Yaklaşımı

1. Viewport'u render et (OpenGL veya Workbench)
2. Render sonucunu texture space'e project et
3. UV mapping ile doğru texture bölgesine yerleştir
4. Compositing pipeline ile birleştir

> Bu özellik teknik olarak en zorlayıcı kısımdır. MVP sonrası iteratif geliştirme önerilir.

---

*Önceki: [Phase 5 — MVP Release](./PHASE_05_PLAN.md) | Sonraki: [Phase 7 — Advanced Features](./PHASE_07_PLAN.md)*
