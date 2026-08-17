# Blender AI Texture Painter — Project Specification

## 1. Proje Özeti

Bu proje, Blender'ın mevcut 2D Image Editor / Texture Paint / UV workflow'unu AI destekli profesyonel bir texture editing ortamına dönüştüren bir Blender Add-on'dur.

Ana hedef:

> Kullanıcının Blender'da 3D modeli boyarken Photoshop 2026 seviyesindeki generative AI iş akışlarını doğrudan texture/UV ve 3D viewport bağlamında kullanabilmesi.

Proje sıfırdan geliştirilecektir. Şu anda mevcut kod tabanı, mimari veya çalışan prototip varsayılmamalıdır.

Addon yalnızca "AI ile resim üretme" aracı değildir. Blender'ın UV, texture, material, viewport ve mümkün olduğunda geometry context bilgisini AI generation/editing pipeline'ına dahil eden bir **AI Texture Painting Environment** olmalıdır.

---

# 2. Temel Hedefler

## Birincil hedefler

1. Blender Image Editor içinde AI destekli generative editing.
2. UV texture üzerinde maskeli AI generation/editing.
3. 3D viewport'taki seçili yüzeyleri AI işlemlerine bağlama.
4. Mevcut texture'ın yalnızca seçilen bölgelerini değiştirme.
5. Non-destructive workflow.
6. Undo/redo ve variation sistemi.
7. Reference image desteği.
8. Farklı AI sağlayıcılarını tek bir abstraction altında destekleme.
9. Local AI ve remote API kullanımına uygun mimari.
10. PBR texture workflow'una genişleyebilme.

## Tasarım ilkesi

AI hiçbir zaman kullanıcının istemediği alanları değiştirmemelidir.

Özellikle texture editing sırasında:

- maskelenmeyen pikseller korunmalı,
- mevcut texture mümkün olduğunca korunmalı,
- generated result kontrollü şekilde composite edilmelidir.

---

# 3. Kullanıcı Deneyimi

Ana workflow:

```text
3D Model
   ↓
Texture / UV seçimi
   ↓
Mask oluşturma
   ↓
Prompt
   ↓
Reference Image (opsiyonel)
   ↓
AI Generate / Fill / Remove
   ↓
Preview
   ↓
Variation seçimi
   ↓
Apply
   ↓
Blender Image Texture
```

Kullanıcı mümkün olduğunca Blender'dan çıkmamalıdır.

---

# 4. İlk Sürüm (MVP)

İlk sürümde aşağıdaki özellikler zorunludur.

## 4.1 AI Texture Fill

Kullanıcı texture üzerinde bir maske oluşturur.

Örnek prompt:

```text
worn black leather grip, realistic rough surface,
fine woven fibers, subtle scratches
```

AI yalnızca maskeli bölge için sonuç üretir.

## 4.2 AI Remove

Maskelenen bölgedeki içerik kaldırılır.

Prompt opsiyoneldir.

AI çevredeki texture bilgisinden uygun replacement üretir.

## 4.3 Generate Variations

Tek generation yerine birden fazla sonuç üretilebilir.

UI:

```text
Variation 1
Variation 2
Variation 3
Variation 4
```

Kullanıcı birini seçer.

## 4.4 Reference Image

Kullanıcı referans görsel ekleyebilir.

Örnek:

```text
Reference:
old black leather.jpg

Prompt:
aged black leather grip
```

Reference image AI pipeline'a ayrı bir conditioning input olarak aktarılmalıdır.

## 4.5 Apply / Cancel

Generation sonucu önce preview olarak tutulmalıdır.

Kullanıcı:

- Apply
- Cancel
- Generate Again

yapabilmelidir.

---

# 5. Photoshop Benzeri Özellikler

Proje Photoshop'un UI'ını kopyalamamalıdır.

Ancak aşağıdaki generative concepts Blender workflow'una uyarlanmalıdır:

- Generative Fill
- Generative Remove
- Generative Expand
- Generate Image
- Reference Image
- Variations
- Upscale
- AI-assisted editing

Bunlar Blender'ın UV/texture mantığına göre uygulanmalıdır.

---

# 6. Blender Entegrasyonu

Addon Blender Python API kullanmalıdır.

Ana API alanları:

- `bpy`
- `bpy.types`
- `bpy.types.Image`
- `bpy.types.Operator`
- `bpy.types.Panel`
- UV data
- Image Editor
- Texture Paint
- Material
- Shader Nodes
- 3D Viewport

Blender sürümü proje başlangıcında açıkça tanımlanmalıdır.

Kod, Blender API'sine gereksiz şekilde tightly coupled olmamalıdır.

Blender API değişikliklerine karşı adapter katmanı kullanılmalıdır.

---

# 7. Önerilen Mimari

```text
addon/
│
├── __init__.py
│
├── core/
│   ├── project.py
│   ├── state.py
│   ├── config.py
│   └── logging.py
│
├── ai/
│   ├── provider.py
│   ├── registry.py
│   ├── request.py
│   ├── response.py
│   ├── capabilities.py
│   │
│   └── providers/
│       ├── local.py
│       ├── openai.py
│       ├── flux.py
│       ├── gemini.py
│       └── adobe.py
│
├── texture/
│   ├── image.py
│   ├── mask.py
│   ├── composite.py
│   ├── projection.py
│   └── layers.py
│
├── blender/
│   ├── images.py
│   ├── uv.py
│   ├── materials.py
│   ├── viewport.py
│   └── context.py
│
├── operators/
│   ├── generate.py
│   ├── remove.py
│   ├── fill.py
│   ├── variation.py
│   └── apply.py
│
├── ui/
│   ├── panels.py
│   ├── properties.py
│   └── operators.py
│
└── utils/
    ├── files.py
    ├── images.py
    └── validation.py
```

Bu yapı ilk günden uygulanmak zorunda değildir; ancak kod tabanı büyüdüğünde AI, Blender integration, texture processing ve UI birbirine karıştırılmamalıdır.

---

# 8. AI Provider Abstraction

AI sisteminin en önemli mimari kuralı:

> UI hiçbir AI provider'ın API'sini doğrudan çağırmamalıdır.

UI:

```text
Generate
```

der.

Application layer:

```text
AIProvider.generate(request)
```

çağırır.

Provider seçimi registry tarafından yapılır.

Örnek:

```text
AIProvider
    |
    +-- LocalProvider
    +-- FluxProvider
    +-- OpenAIProvider
    +-- GeminiProvider
    +-- AdobeProvider
```

Provider değiştirildiğinde UI kodu değişmemelidir.

---

# 9. AI Request Model

AI request standartlaştırılmalıdır.

Önerilen mantıksal veri:

```text
AIRequest
├── operation
├── prompt
├── negative_prompt
├── source_image
├── mask
├── reference_images[]
├── width
├── height
├── seed
├── variation_count
├── strength
├── seamless
├── preserve_unmasked
└── context
```

`context` ileride şunları taşıyabilir:

```text
context
├── uv_map
├── normal_map
├── depth_map
├── viewport_render
├── selected_faces
└── material_info
```

Provider bu bilgilerin hepsini desteklemek zorunda değildir.

Capability sistemi kullanılmalıdır.

---

# 10. Provider Capability System

Her AI provider hangi özellikleri desteklediğini bildirmelidir.

Örnek:

```text
Capability:
- TEXT_TO_IMAGE
- IMAGE_TO_IMAGE
- INPAINT
- OUTPAINT
- REFERENCE_IMAGE
- VARIATIONS
- UPSCALE
- SEAMLESS
- MASK
- DEPTH_CONTROL
- NORMAL_CONTROL
```

UI desteklenmeyen özellikleri otomatik olarak disable etmelidir.

---

# 11. Texture Editing Pipeline

Texture işlemleri destructive olmamalıdır.

Temel pipeline:

```text
Original Texture
      +
Mask
      +
Generated Result
      ↓
Composite
      ↓
Preview Image
      ↓
Apply
```

Temel compositing:

```text
result = original * (1 - mask) + generated * mask
```

Mask feather/softness desteklenmelidir.

Alpha-aware compositing ileride eklenebilir.

---

# 12. Mask System

Mask sistemi MVP'nin kritik parçalarından biridir.

Desteklenmesi gereken mask kaynakları:

1. Image Editor brush mask
2. Texture Paint mask
3. UV island selection
4. Selected faces
5. Future: 3D viewport paint mask

Mask:

- grayscale,
- 0 = protected,
- 1 = editable

mantığında normalize edilmelidir.

AI'ya gönderilmeden önce provider'ın istediği formata dönüştürülebilir.

---

# 13. Protected Pixels

Aşağıdaki kural zorunludur:

> Mask dışındaki texture alanları AI tarafından değiştirilmemelidir.

AI modeli tüm görüntüyü değiştirmiş olsa bile final compositing sırasında mask dışı pikseller orijinal texture'dan alınmalıdır.

Bu güvenlik katmanı provider'a bırakılmamalıdır.

---

# 14. Image Resolution

Generation resolution ile Blender texture resolution birbirinden ayrılmalıdır.

Örneğin:

```text
Blender Texture:
4096 x 4096

AI Generation:
1024 x 1024

Composite:
4096 x 4096
```

Gerekirse generated patch upscale edilerek doğru UV bölgesine yerleştirilir.

MVP'de resolution mismatch yönetilmelidir.

---

# 15. Seamless Texture

Seamless generation ilk sürümde optional olabilir ancak mimaride yer almalıdır.

Amaç:

```text
left edge ≈ right edge
top edge ≈ bottom edge
```

Texture tile edildiğinde görünür seam oluşmamalıdır.

Bu özellik özellikle:

- fabric
- leather
- stone
- metal
- wood
- concrete

gibi material texture'larında önemlidir.

---

# 16. PBR Roadmap

MVP yalnızca Base Color üzerinde çalışabilir.

Ancak architecture şu kanalları destekleyecek şekilde hazırlanmalıdır:

```text
Base Color
Normal
Roughness
Metallic
Height
Ambient Occlusion
Opacity
Emission
```

İleride:

```text
Prompt
  ↓
Material Generator
  ↓
PBR Set
```

üretilebilmelidir.

---

# 17. Normal Map Özel Kuralı

Normal map işlemleri için AI output doğrudan normal map olarak kabul edilmemelidir.

Gelecekte:

```text
AI generated height/detail
          ↓
Normal reconstruction
          ↓
Existing normal
          ↓
Normal blend
```

yaklaşımı tercih edilmelidir.

Özellikle mevcut normal map'in korunması önemlidir.

---

# 18. 3D-Aware Generation — V2

Projenin uzun vadeli ana özelliği budur.

3D viewport'tan context toplanabilir:

```text
3D Object
   ↓
Camera View
   ├── RGB render
   ├── Depth
   ├── Normal
   └── Mask
          ↓
        AI
```

Ayrıca:

```text
Selected Faces
      ↓
UV Coordinates
      ↓
Texture Region
```

eşleştirilmelidir.

Amaç:

> Kullanıcı 3D model üzerinde bir alan seçtiğinde AI bunun texture üzerindeki karşılığını doğru şekilde bulabilsin.

---

# 19. "Paint From View" — Uzun Vadeli Killer Feature

Kullanıcı doğrudan 3D model üzerinde alan seçer:

```text
[3D VIEWPORT]

        ________
       /        \
      /  █████   \
     |   █████    |
      \          /
       \________/
```

Prompt:

```text
worn black leather
with subtle scratches
```

Addon:

```text
Viewport Selection
       ↓
Selected Faces
       ↓
UV Region
       ↓
Texture Mask
       ↓
AI Generation
       ↓
UV Composite
       ↓
3D Viewport Update
```

Kullanıcı UV layout bilmek zorunda kalmamalıdır.

Bu özellik projenin temel farklılaştırıcı özelliği olarak düşünülmelidir.

---

# 20. Non-Destructive Workflow

AI generation sonucunu mümkün olduğunca doğrudan orijinal texture'a yazma.

Tercih edilen yapı:

```text
Original Texture
      +
AI Layer
      +
Mask
      ↓
Composite
```

İdeal gelecekte Photoshop benzeri layer sistemi:

```text
Texture
├── Original
├── AI Generation 01
├── AI Generation 02
├── AI Remove
└── Manual Paint
```

olabilir.

MVP'de gerçek Blender layer sistemi zorunlu değildir; fakat architecture buna engel olmamalıdır.

---

# 21. History / Undo

Her AI işleminden önce state tutulmalıdır.

Örnek:

```text
State 0 = Original
State 1 = Leather generation
State 2 = Scratches
State 3 = Remove logo
```

Kullanıcı önceki state'e dönebilmelidir.

Blender'ın kendi undo sisteminden yararlanılabilir ancak büyük image data için memory kullanımına dikkat edilmelidir.

---

# 22. UI

İlk UI sade olmalıdır.

Önerilen panel:

```text
AI TEXTURE PAINTER

Operation:
[ Fill ▼ ]

Prompt:
[....................................]

Negative Prompt:
[....................................]

Reference:
[ + Add Image ]

Mask:
[ Use Current Mask ]

Model:
[ Provider / Model ▼ ]

Variations:
[ 4 ]

[ GENERATE ]

────────────────────

RESULTS

[ Result 1 ]
[ Result 2 ]
[ Result 3 ]
[ Result 4 ]

[ APPLY ] [ CANCEL ]
```

İlk aşamada karmaşık UI yapılmamalıdır.

---

# 23. Error Handling

AI request sırasında:

- API key eksik
- network failure
- timeout
- invalid response
- unsupported capability
- image size limit
- malformed image
- provider error

gibi durumlar kullanıcıya anlaşılır şekilde gösterilmelidir.

Örneğin:

```text
Generation failed.

Provider:
Flux

Reason:
Request timed out.

[ Retry ]
```

Raw exception kullanıcıya doğrudan gösterilmemelidir.

Developer log'a detay yazılmalıdır.

---

# 24. API Key Security

API key:

- source code içine yazılmamalı,
- repository'ye commit edilmemeli,
- log'a yazılmamalı.

Environment variables veya Blender'ın güvenli preferences sistemi kullanılabilir.

Örnek:

```text
AI_TEXTURE_API_KEY
```

Ancak provider'a göre credential sistemi değişebilir.

---

# 25. Local AI

Mimari local inference desteklemelidir.

Örneğin:

```text
Blender Addon
      ↓
Local HTTP API
      ↓
AI Server
      ↓
GPU
```

Addon'un model inference kodunu Blender process'ine gömmek MVP için gerekli değildir.

Öncelik:

> Provider abstraction + HTTP based local backend.

---

# 26. Remote AI

Remote provider'lar HTTP API üzerinden çalışmalıdır.

Network layer ayrı tutulmalıdır.

Önerilen:

```text
ai/
  transport/
    http.py
```

Provider implementation HTTP transport detayını application logic'ten ayırmalıdır.

---

# 27. Async / UI Blocking

AI generation Blender UI thread'ini bloklamamalıdır.

Yanlış:

```text
button click
   ↓
HTTP request
   ↓
wait 30 seconds
   ↓
UI frozen
```

Doğru yaklaşım:

```text
button click
   ↓
background task
   ↓
progress
   ↓
result
   ↓
main Blender thread
   ↓
image update
```

Blender API'ye erişim gerektiğinde main thread kurallarına dikkat edilmelidir.

Threading konusunda Blender'ın API kısıtları mutlaka dikkate alınmalıdır.

---

# 28. Cache

Aynı request tekrarlandığında gereksiz generation yapılmamalıdır.

Request hash oluşturulabilir:

```text
hash(
    provider +
    model +
    prompt +
    source +
    mask +
    reference +
    seed
)
```

Cache ileride local disk üzerinde tutulabilir.

---

# 29. Logging

Development sırasında structured logging kullanılmalıdır.

Örnek:

```text
[INFO] AI request started
[INFO] Provider: flux
[INFO] Operation: inpaint
[INFO] Resolution: 1024x1024
[INFO] Generation completed
[INFO] Composite applied
```

API key veya kullanıcı secret'ları loglanmamalıdır.

---

# 30. Testing

Kod tabanı test edilebilir olmalıdır.

Öncelikli testler:

## Unit tests

- mask conversion
- image compositing
- UV coordinate conversion
- request serialization
- provider capability detection
- cache hashing

## Integration tests

- provider request
- generated image import
- Blender image update
- apply/cancel workflow

## Visual tests

Özellikle:

```text
original texture
+
mask
+
generated texture
=
expected composite
```

kontrol edilmelidir.

---

# 31. MVP Geliştirme Sırası

Kodlama şu sırayla yapılmalıdır.

## Phase 1 — Foundation

- [ ] Blender addon skeleton
- [ ] `register()` / `unregister()`
- [ ] preferences
- [ ] logging
- [ ] configuration
- [ ] basic panel

## Phase 2 — Image Pipeline

- [ ] Blender image detection
- [ ] image extraction
- [ ] mask extraction
- [ ] image import
- [ ] compositing
- [ ] preview
- [ ] apply/cancel

## Phase 3 — AI Abstraction

- [ ] AIProvider interface
- [ ] request model
- [ ] response model
- [ ] capability system
- [ ] provider registry
- [ ] mock provider

Önemli:

> Gerçek AI provider bağlamadan önce MockProvider oluştur.

Böylece UI ve texture pipeline API olmadan test edilebilir.

## Phase 4 — First Real Provider

İlk gerçek provider yalnızca tek bir provider olabilir.

Provider implementation diğer sistemlerden bağımsız tutulmalıdır.

## Phase 5 — Reference / Variations

- [ ] reference image
- [ ] multiple results
- [ ] variation UI
- [ ] result selection

## Phase 6 — 3D Integration

- [ ] selected faces
- [ ] UV extraction
- [ ] viewport context
- [ ] texture region mapping

## Phase 7 — Advanced AI

- [ ] seamless
- [ ] expand
- [ ] upscale
- [ ] PBR generation
- [ ] normal generation

---

# 32. Development Rules for Coding Agent

Bu proje üzerinde çalışan coding agent aşağıdaki kurallara uymalıdır.

## Rule 1

Mevcut olmayan sistemi varsayma.

Proje boşsa önce architecture ve minimal working addon oluştur.

## Rule 2

Büyük miktarda kodu tek seferde yazma.

Her aşamadan sonra sistem çalışır durumda kalmalıdır.

## Rule 3

AI provider kodunu Blender UI koduna gömme.

## Rule 4

Texture compositing mantığını AI provider'dan bağımsız tut.

## Rule 5

Mask dışındaki pikselleri koruma garantisini local compositing katmanında uygula.

## Rule 6

API key veya secret hard-code etme.

## Rule 7

Blender main-thread API kurallarını ihlal etme.

## Rule 8

Mock provider olmadan AI-dependent UI geliştirme.

## Rule 9

Kod tekrarını azalt ama erken abstraction yaparak sistemi gereksiz karmaşıklaştırma.

## Rule 10

Her önemli architectural karar için kısa documentation ekle.

---

# 33. İlk Coding Task

İlk görev AI modeli bağlamak değildir.

Önce çalışan bir Blender addon skeleton oluştur.

İlk milestone:

```text
Blender
  ↓
Addon enabled
  ↓
AI Texture Painter panel visible
  ↓
Active image detected
  ↓
Mask detected
  ↓
Generate button
  ↓
MockProvider
  ↓
Fake generated image
  ↓
Mask composite
  ↓
Preview
  ↓
Apply
```

Gerçek AI provider bu sistem tamamen çalıştıktan sonra eklenmelidir.

---

# 34. Mock Provider

MockProvider gerçek AI kullanmaz.

Örneğin:

```text
Original Image
      ↓
Mask
      ↓
Mock generated patch
      ↓
Composite
```

Mock output basit bir test image olabilir.

Amaç:

- UI test etmek,
- mask pipeline test etmek,
- compositing test etmek,
- apply/cancel test etmek.

---

# 35. Definition of Done — MVP

MVP ancak aşağıdaki workflow tamamen çalışıyorsa tamamlanmış sayılır:

```text
1. Blender açılır.
2. Addon aktif edilir.
3. Image Editor'da texture açılır.
4. Kullanıcı mask oluşturur.
5. AI Texture Painter paneli açılır.
6. Prompt girilir.
7. Generate tıklanır.
8. Provider request oluşturulur.
9. Result alınır.
10. Result preview edilir.
11. Mask dışındaki orijinal pikseller korunur.
12. Kullanıcı Apply der.
13. Blender texture güncellenir.
14. Material viewport'ta güncellenir.
15. Undo mümkün olur.
```

Bu workflow çalışmadan advanced feature geliştirmeye geçilmemelidir.

---

# 36. Uzun Vadeli Vizyon

Projenin nihai hedefi:

> Blender içinde Photoshop Generative AI deneyiminin basit bir kopyasını yapmak değil; 2D generative editing + UV editing + 3D viewport context + PBR material generation özelliklerini tek bir texture authoring workflow'unda birleştirmek.

Nihai kullanıcı deneyimi:

```text
             3D MODEL
                 │
       ┌─────────┴─────────┐
       │                   │
   3D PAINT            UV EDITOR
       │                   │
       └─────────┬─────────┘
                 │
          AI TEXTURE ENGINE
                 │
      ┌──────────┼──────────┐
      │          │          │
    FILL       REMOVE     GENERATE
      │          │          │
      └──────────┼──────────┘
                 │
          MATERIAL ENGINE
                 │
       ┌─────────┼─────────┐
       │         │         │
      BASE     NORMAL    ROUGHNESS
      COLOR               │
       │         │         │
       └─────────┼─────────┘
                 │
              MATERIAL
```

Bu proje ileride profesyonel oyun assetleri, 3D art, texture authoring ve AI-assisted material creation için kullanılabilecek bağımsız bir Blender workflow'una dönüşebilir.

---

# 37. Important Engineering Principle

Her özellik eklenirken şu soru sorulmalıdır:

> "Bu özellik Blender'ın mevcut workflow'unu gerçekten hızlandırıyor mu?"

Eğer cevap hayırsa yalnızca AI gösterisi olduğu için özellik eklenmemelidir.

Öncelik:

1. Kontrol
2. Determinism
3. Non-destructive editing
4. Texture quality
5. Workflow speed
6. AI quality
7. Advanced automation

AI kullanıcının kontrolünü azaltmamalı; artırmalıdır.
