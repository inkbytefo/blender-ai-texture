# 📚 AI Texture Painter — Proje Dokümantasyonu

> **Blender AI Texture Painter** eklentisinin profesyonel proje dokümantasyonu.
> Hedef Platform: **Blender 5.0+ (5.2 LTS önerilen)**
> Son Güncelleme: 13 Ağustos 2026

---

## 📖 Dokümantasyon İndeksi

| # | Dosya | Açıklama |
|:--|:------|:---------|
| 01 | [Proje Genel Bakış](./01-PROJECT_OVERVIEW.md) | Vizyon, hedefler, pazar analizi, rakip karşılaştırması |
| 02 | [Mimari Tasarım](./02-ARCHITECTURE.md) | Modül yapısı, veri akışı, tasarım kararları |
| 03 | [Blender Entegrasyonu](./03-BLENDER_INTEGRATION.md) | Blender 5.x API, Extensions Platform, threading |
| 04 | [AI Provider Sistemi](./04-AI_PROVIDER_SYSTEM.md) | Provider abstraction, capability, request/response |
| 05 | [Texture Pipeline](./05-TEXTURE_PIPELINE.md) | Mask, compositing, resolution, PBR roadmap |
| 06 | [Kullanıcı Deneyimi](./06-USER_EXPERIENCE.md) | Workflow, UI tasarım, error handling |
| 07 | [Yol Haritası](./07-ROADMAP.md) | Fazlar, milestone'lar, tahmini süreler |
| 08 | [Geliştirme Kılavuzu](./08-DEVELOPMENT_GUIDE.md) | Kodlama kuralları, Git workflow, test stratejisi |
| 09 | [API Referansı](./09-API_REFERENCE.md) | Veri modelleri, interface'ler, enum tanımları |
| 10 | [Güvenlik ve Dağıtım](./10-SECURITY_AND_DEPLOYMENT.md) | API key güvenliği, lisanslama, dağıtım |

---

## 🎯 Hızlı Başlangıç

Bu proje, Blender'ın 2D Image Editor / Texture Paint / UV workflow'unu **AI destekli profesyonel bir texture editing ortamına** dönüştüren bir Blender Add-on'dur.

### Temel Özellikler

- 🎨 **AI Texture Fill** — Maskeli bölgelere AI ile texture üretimi
- 🧹 **AI Remove** — İstenmeyen alanları AI ile temizleme
- 🔄 **Variations** — Çoklu sonuç üretimi ve seçim
- 🖼️ **Reference Image** — Referans görselle yönlendirme
- 🛡️ **Protected Pixels** — Mask dışı alanlar asla değişmez
- 🔌 **Multi-Provider** — OpenAI, Flux, Gemini, Local AI desteği

### Hedef Blender Sürümü

```
Minimum: Blender 5.0
Önerilen: Blender 5.2 LTS (Temmuz 2026)
Maksimum: Blender 5.3+ (uyumluluk planlanıyor)
Python: 3.13
```

---

## 📁 Proje Yapısı (Hedef)

```
aiimagegenerator/
├── docs/                          ← Bu dokümantasyon
│   ├── README.md
│   ├── 01-PROJECT_OVERVIEW.md
│   ├── 02-ARCHITECTURE.md
│   ├── ...
│   └── 10-SECURITY_AND_DEPLOYMENT.md
│
├── ai_texture_painter/            ← Ana addon kodu
│   ├── __init__.py
│   ├── blender_manifest.toml
│   ├── core/
│   ├── ai/
│   ├── texture/
│   ├── blender/
│   ├── operators/
│   ├── ui/
│   └── utils/
│
├── tests/                         ← Test dosyaları
├── AI_Texture_Painter_PROJECT_SPEC.md
├── .gitignore
└── README.md
```

---

## 📋 Orijinal Spesifikasyon

Projenin temel spesifikasyonu: [AI_Texture_Painter_PROJECT_SPEC.md](../AI_Texture_Painter_PROJECT_SPEC.md)

---

## 📝 Lisans

Bu proje GPL-3.0-or-later lisansı altında geliştirilecektir (Blender Extensions Platform gereksinimi).

---

*Dokümantasyon, Inkbytefo Projects tarafından oluşturulmuştur.*
