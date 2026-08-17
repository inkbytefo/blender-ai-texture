# 🎨 AI Texture Painter (Blender Extension)

<p align="center">
  <img src="https://img.shields.io/badge/Blender-4.2%2B%20%7C%205.x-E87D0D?style=for-the-badge&logo=blender&logoColor=white" alt="Blender Version">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python Version">
  <img src="https://img.shields.io/badge/Tests-39%20Passing-brightgreen?style=for-the-badge" alt="Tests">
  <img src="https://img.shields.io/badge/License-GPL--3.0-blue?style=for-the-badge" alt="License">
</p>

<p align="center">
  <b>Blender'dan hiç çıkmadan, 3D modellerinizi ve dokularınızı en güncel AI modelleriyle büyüleyin! ✨</b><br>
  <i>İster sıfırdan doku üretin, ister sadece 3D modelinizin seçtiğiniz bir yüzeyini akıllıca düzenleyin.</i>
</p>

---

## 👋 Merhaba 3D Sanatçısı & Geliştirici Dostum!

3D modelleme yaparken doku aramak, Photoshop ile Blender arasında mekik dokumak veya UV haritalarındaki dikiş izleriyle boğuşmak bazen gerçekten can sıkıcı olabiliyor, değil mi? 

İşte tam olarak bu yüzden **AI Texture Painter**'ı geliştirdik! Amacımız; en sevdiğin yapay zeka modellerini doğrudan Blender'ın **Image Editor** ve **3D Viewport** paneline getirmek ve yaratıcılığını ışık hızına çıkarmak.

---

## ✨ Neler Yapabilirsin? (Süper Güçlerin)

* 🎯 **3D Model Üzerinden Nokta Atışı Yüzey Boyama (UV Inpaint):**  
  Modelinde sadece bir yüzeyi mi değiştirmek istiyorsun? Edit Mode'da o yüzü seç, prompt'unu yaz ve **Generate**'e bas! Gelişmiş Barycentric UV motorumuz sadece seçtiğin alanı boyar, modelin geri kalan dokusuna tek bir piksel bile zarar vermez.

* ⚡ **Ultra Hızlı ve Akıcı Arayüz (60+ FPS):**  
  Ağır piksel hesaplamalarını panel çizim döngüsünden izole ettik. Blender'ın arayüzü yağ gibi akar, sıfır takılma yaşarsın.

* 🧠 **Dünyanın En Güçlü AI Sağlayıcıları ve Modelleri Elinin Altında:**  
  * **OpenRouter:** GPT Image 2, ByteDance Seedream 4.5, FLUX.2 Pro, FLUX.1 Schnell, Recraft V3, Gemini 2.5 Flash Image.
  * **fal.ai:** FLUX.2 [pro], FLUX.1 Kontext [pro], FLUX.1 [schnell] (4 adımda ultra hızlı!), FLUX.1 [dev], Nano Banana 2, GPT Image 2.
  * **OpenAI (ChatGPT):** Resmi GPT Image 2, GPT Image 1.5, GPT Image 1, GPT Image 1 Mini, DALL-E 3, DALL-E 2.
  * **Google:** Yeni nesil Nano Banana 2 (`gemini-3.1-flash-image`), Nano Banana 2 Lite, Nano Banana Pro, Gemini 2.5 Flash Image.
  * **Custom Model ID:** İstediğin herhangi bir özel model ID'sini tek tıkla kullanabilirsin.

* 🔄 **Sonsuz Geri Alma & Varyasyon Seçimi:**  
  Oluşturulan sonuçları beğenmedin mi? Tek tıkla `Cancel` de veya çoklu varyasyonlar (V1, V2, V3, V4) arasından en beğendiğini seçip `Apply` ile dokuna mühürle.

* 🔒 **Sıfır Dikiş İzi & Kusursuz Kenar Yumuşatma:**  
  Dahili UV Bleed (Dikiş payı) ve Gaussian Feathering algoritmaları sayesinde yapay zeka tarafından boyanan alanlar orijinal dokuyla kusursuzca kaynaşır.

---

## 🚀 Kolay Kurulum (Blender 4.2+ / 5.x)

Eklentimiz Blender'ın en yeni **Extension Manifest** standardına %100 uyumludur:

1. Bu depodaki hazır paketi indirin: [`dist/ai_texture_painter-0.1.0.zip`](dist/ai_texture_painter-0.1.0.zip) *(veya `python build_extension.py` komutuyla kendiniz derleyin)*.
2. Blender'ı açın ve üst menüden **Edit > Preferences > Get Extensions** sekmesine gidin.
3. Sağ üstteki dişli çark / açılır menüden ⚙️ **Install from Disk...** seçeneğine tıklayın.
4. İndirdiğiniz `.zip` dosyasını seçin.
5. İşte bu kadar! Eklenti anında kurulur ve sol alttan "Uninstall" butonuyla bile kolayca yönetilebilir.

---

## 🛠️ Nasıl Kullanılır? (Adım Adım)

### 1. API Anahtarını Gir
* Blender'da **Image Editor** (Görsel Düzenleyici) penceresini açın.
* Sağ taraftaki **N-Panel**'den **AI Texture** sekmesine tıklayın.
* **Settings & AI Setup** altından dilediğiniz sağlayıcıyı (**OpenRouter**, **fal.ai**, **OpenAI** veya **Google Gemini**) seçip API Key'inizi yapıştırın.

### 2. Doku Oluşturma (Text-to-Texture)
* Yeni bir doku açın veya mevcut bir dokuyu seçin.
* Prompt kutusuna hayal ettiğiniz dokuyu yazın (Örn: *"stylized medieval cobblestone texture, seamless diffuse map, hand painted style"*).
* **GENERATE PREVIEW** butonuna basın. Birkaç saniye içinde dokunuz hazır!

### 3. Sadece Seçili Yüzeyi Boyama (3D Inpaint)
* 3D Viewport'ta modelinizi seçip **Edit Mode**'a (`Tab`) geçin.
* Dokusunu değiştirmek istediğiniz yüzeyi/yüzeyleri seçin.
* N-Panel'de `Mask: 3D/UV Selection (Active in Edit Mode)` uyarısını göreceksiniz.
* Prompt'unuza eklemek istediğiniz detayı yazın (Örn: *"rusty metal lock with scratches"*).
* **GENERATE PREVIEW** dediğinizde sadece o yüzey güncellenir!

---

## 🤖 Desteklenen Model Kataloğu

| Sağlayıcı | Model Adı | Endpoint ID | En İyi Kullanım Alanı |
|---|---|---|---|
| **OpenRouter** | **GPT Image 2** | `openai/gpt-image-2` | Üst düzey tipografi, yüksek detaylı dokular |
| **OpenRouter** | **Seedream 4.5** | `bytedance-seed/seedream-4.5` | ByteDance yüksek çözünürlüklü fotogerçekçi dokular |
| **OpenRouter** | **FLUX.2 [pro]** | `black-forest-labs/flux.2-pro` | En yüksek FLUX kalite standardı |
| **OpenRouter** | **Recraft V3** | `recraft/recraft-v3` | Profesyonel grafik, illüstrasyon ve tasarım |
| **fal.ai** | **FLUX.2 [pro]** | `fal-ai/flux-2-pro` | En yüksek kalite, sıralı doku düzenleme |
| **fal.ai** | **FLUX.1 Kontext [pro]** | `fal-ai/flux-pro/kontext` | Referans görselle bağlamsal düzenleme |
| **fal.ai** | **FLUX.1 [schnell]** | `fal-ai/flux/schnell` | Ultra hızlı (4 adım), ekonomik prototipleme |
| **fal.ai** | **GPT Image 2 Edit** | `openai/gpt-image-2/edit` | Nokta atışı inpainting ve bölgesel tamirat |
| **fal.ai** | **Nano Banana 2** | `fal-ai/nano-banana-2/edit` | Google'ın en yeni SOTA çok modlu görsel modeli |
| **OpenAI** | **GPT Image 2** | `gpt-image-2` | Resmi OpenAI API ile doğrudan ultra detaylı üretim |
| **Google** | **Nano Banana 2** | `gemini-3.1-flash-image` | Doğrudan Google AI Studio API üzerinden üretim |
| **Google** | **Nano Banana Pro** | `gemini-3-pro-image` | En yüksek Google detay seviyesi |

---

## 🧪 Geliştirici & Test Rehberi

Eklenti, harici kütüphane bağımlılığı olmadan saf Python ve NumPy ile yazılmıştır.

```bash
# Depoyu klonlayın
git clone https://github.com/inkbytefo/blender-ai-texture.git
cd blender-ai-texture

# Birim testlerini çalıştırın (39 test)
pytest tests/ -v

# Eklenti zip paketini derleyin
python build_extension.py
```

---

## 🤝 Katkıda Bulunma & Destek

Fikirlerin, geri bildirimlerin veya çekeceğin bir Pull Request bizim için çok değerli!
* Bir hata mı buldun? [Issues](https://github.com/inkbytefo/blender-ai-texture/issues) sekmesinden bize hemen haber ver.
* Yeni bir model mi eklemek istiyorsun? PR göndermekten çekinme!

---

<p align="center">
  Geliştirici: <b>Inkbytefo</b> • Sevgi ve yapay zeka ile üretildi ❤️🎨
</p>
