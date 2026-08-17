# 09 — API Referansı

> İç API referansı, veri modelleri, interface tanımları ve enum'lar.

---

## 9.1 Veri Modelleri

### AIOperation (Enum)

```python
class AIOperation(Enum):
    """AI işlem türleri"""
    GENERATE = auto()     # Tamamen yeni texture üretimi
    FILL = auto()         # Maskeli alanı prompt'a göre doldurma (inpaint)
    REMOVE = auto()       # Maskeli alandaki içeriği kaldırma
    EXPAND = auto()       # Texture sınırlarını genişletme (outpaint)
    UPSCALE = auto()      # Çözünürlük artırma
    VARIATION = auto()    # Mevcut sonucun varyasyonunu üretme
```

| Değer | Mask Gerekli | Prompt Gerekli | Source Image Gerekli |
|:------|:-------------|:---------------|:---------------------|
| `GENERATE` | ❌ | ✅ | ❌ |
| `FILL` | ✅ | ✅ | ✅ |
| `REMOVE` | ✅ | ⚙️ opsiyonel | ✅ |
| `EXPAND` | ✅ | ⚙️ opsiyonel | ✅ |
| `UPSCALE` | ❌ | ❌ | ✅ |
| `VARIATION` | ❌ | ❌ | ✅ |

---

### Capability (Enum)

```python
class Capability(Enum):
    """AI provider capability tanımları"""
    
    # --- Temel Generation Modları ---
    TEXT_TO_IMAGE = auto()
    # Sadece prompt ile sıfırdan image üretme.
    # Gerekli: prompt, width, height
    
    IMAGE_TO_IMAGE = auto()
    # Var olan image'ı prompt ile dönüştürme.
    # Gerekli: source_image, prompt, strength
    
    INPAINT = auto()
    # Maskeli bölgeyi prompt'a göre doldurma.
    # Gerekli: source_image, mask, prompt
    
    OUTPAINT = auto()
    # Image sınırlarını genişletme.
    # Gerekli: source_image, mask (genişletme bölgesi)
    
    # --- Ek Özellikler ---
    REFERENCE_IMAGE = auto()
    # Referans image ile yönlendirme.
    # Opsiyonel: reference_images[]
    
    VARIATIONS = auto()
    # Çoklu sonuç üretimi.
    # Parametre: variation_count
    
    UPSCALE = auto()
    # Çözünürlük artırma (super-resolution).
    # Gerekli: source_image
    
    SEAMLESS = auto()
    # Tileable/seamless texture üretimi.
    # Parametre: seamless=True
    
    # --- Kontrol ---
    MASK = auto()
    # Mask desteği (tüm inpaint provider'lar desteklemeli)
    
    DEPTH_CONTROL = auto()
    # Depth map ile kontrol (ControlNet benzeri)
    # Opsiyonel: context.depth_map
    
    NORMAL_CONTROL = auto()
    # Normal map ile kontrol
    # Opsiyonel: context.normal_map
    
    # --- Parametre Kontrolü ---
    NEGATIVE_PROMPT = auto()
    # İstenmeyen özellikleri belirtme
    
    SEED_CONTROL = auto()
    # Seed ile tekrarlanabilir sonuçlar
    
    STRENGTH_CONTROL = auto()
    # Denoising strength (0-1) kontrolü
```

---

### AIRequest

```python
@dataclass
class AIRequest:
    """Standartlaştırılmış AI generation request"""
    
    # ── Zorunlu Alanlar ──
    operation: AIOperation
    # AI işlem türü
    
    prompt: str
    # Generation prompt'u. REMOVE hariç tüm operasyonlarda zorunlu.
    
    width: int
    # İstenen generation genişliği (px). Provider desteklemiyorsa
    # en yakın desteklenen boyuta yuvarlanır.
    
    height: int
    # İstenen generation yüksekliği (px).
    
    # ── Opsiyonel Alanlar ──
    negative_prompt: str = ""
    # İstenmeyen özellikleri belirtir. Desteklemeyen provider'lar
    # bu alanı sessizce yok sayar.
    
    source_image: Optional[np.ndarray] = None
    # Kaynak image. Shape: (H, W, 4), dtype: float32, range: 0-1
    # FILL, REMOVE, EXPAND, IMAGE_TO_IMAGE, UPSCALE için gerekli.
    
    mask: Optional[np.ndarray] = None
    # Mask data. Shape: (H, W), dtype: float32, range: 0-1
    # 0.0 = korunan, 1.0 = düzenlenebilir
    # FILL ve REMOVE için zorunlu.
    
    reference_images: list[np.ndarray] = field(default_factory=list)
    # Referans görseller. Her biri (H, W, 4) float32.
    # Provider REFERENCE_IMAGE capability'sine sahip olmalı.
    
    # ── Generation Parametreleri ──
    seed: int = -1
    # Random seed. -1 = random. Tekrarlanabilirlik için sabit değer.
    
    variation_count: int = 1
    # Kaç adet sonuç üretilecek. 1-8 arası.
    
    strength: float = 0.75
    # Denoising strength. 0.0 = orijinale yakın, 1.0 = tamamen yeni.
    # IMAGE_TO_IMAGE ve INPAINT'te önemli.
    
    seamless: bool = False
    # True ise tileable texture üretilir.
    
    preserve_unmasked: bool = True
    # True ise mask dışı pikseller compositor tarafından korunur.
    # Bu parametre provider'a değil compositor'a yöneliktir.
    
    # ── 3D Context (V2+) ──
    context: Optional[AIContext] = None
    # 3D viewport context bilgisi.
```

**Metodlar:**

| Metod | Dönüş | Açıklama |
|:------|:------|:---------|
| `validate()` | `list[str]` | Request doğrulama hataları (boş = geçerli) |
| `to_hash()` | `str` | Cache key için SHA-256 hash (16 karakter) |

---

### AIResponse

```python
@dataclass
class AIResponse:
    """Standartlaştırılmış AI generation response"""
    
    success: bool
    # İşlem başarılı mı?
    
    images: list[np.ndarray]
    # Üretilen image'lar. Her biri (H, W, 4) float32, range: 0-1
    
    provider_name: str = ""
    # Sonucu üreten provider adı
    
    model_name: str = ""
    # Kullanılan model adı
    
    generation_time: float = 0.0
    # Generation süresi (saniye)
    
    seed_used: int = -1
    # Kullanılan seed (tekrarlanabilirlik için)
    
    error_message: str = ""
    # Hata mesajı (başarısızsa)
    
    error_code: str = ""
    # Hata kodu (AIErrorCode değerleri)
    
    metadata: dict = field(default_factory=dict)
    # Provider-specific ek metadata
```

**Property'ler:**

| Property | Tip | Açıklama |
|:---------|:----|:---------|
| `variation_count` | `int` | Üretilen image sayısı |
| `has_error` | `bool` | Hata var mı? |

**Factory Metodları:**

| Metod | Açıklama |
|:------|:---------|
| `AIResponse.error(message, code)` | Hata response'u oluşturur |

---

### AIContext

```python
@dataclass
class AIContext:
    """3D viewport context bilgisi (Phase 6+)"""
    
    uv_map: Optional[np.ndarray] = None
    # UV koordinat haritası
    
    normal_map: Optional[np.ndarray] = None
    # Surface normal map (camera space)
    
    depth_map: Optional[np.ndarray] = None
    # Depth map (0-1 normalized)
    
    viewport_render: Optional[np.ndarray] = None
    # Viewport render sonucu (RGBA)
    
    selected_faces: Optional[list[int]] = None
    # Seçili face indeksleri
    
    material_info: Optional[dict] = None
    # Material metadata (shader tipi, renk, vb.)
```

---

## 9.2 Interface Tanımları

### AIProvider (Abstract Base Class)

```python
class AIProvider(ABC):
    """AI provider base class — tüm provider'lar bu interface'i uygulamalı"""
```

| Property/Method | Tip | Abstract | Açıklama |
|:----------------|:----|:---------|:---------|
| `name` | `str` | ✅ | Tekil provider ismi (lowercase) |
| `display_name` | `str` | ✅ | UI gösterim ismi |
| `capabilities` | `set[Capability]` | ✅ | Desteklenen capability seti |
| `generate(request)` | `AIResponse` | ✅ | AI generation çalıştır |
| `validate_config()` | `bool` | ✅ | Konfigürasyon geçerli mi? |
| `supports(capability)` | `bool` | ❌ | Capability kontrolü |
| `get_models()` | `list[str]` | ❌ | Kullanılabilir model listesi |

---

### ProviderRegistry (Singleton)

```python
class ProviderRegistry:
    """AI provider merkezi kayıt sistemi"""
```

| Method | Parametre | Dönüş | Açıklama |
|:-------|:----------|:------|:---------|
| `register(provider)` | `AIProvider` | `None` | Provider kaydet |
| `get(name)` | `str` | `AIProvider \| None` | İsme göre provider al |
| `get_active()` | — | `AIProvider` | Aktif provider'ı al |
| `list_providers()` | — | `list[dict]` | Tüm provider'ları listele |
| `get_providers_for_capability(cap)` | `Capability` | `list[AIProvider]` | Capability'ye göre filtrele |

---

### TextureCompositor

```python
class TextureCompositor:
    """Mask-protected texture compositing"""
```

| Method | Parametreler | Dönüş | Açıklama |
|:-------|:-------------|:------|:---------|
| `composite(original, generated, mask)` | `np.ndarray × 3` | `np.ndarray` | Mask-protected compositing |
| `composite_with_feather(original, generated, mask, radius)` | `np.ndarray × 3, int` | `np.ndarray` | Feather'lı compositing |
| `verify_protected_pixels(original, result, mask, tolerance)` | `np.ndarray × 3, float` | `bool` | Protected pixel doğrulaması |

---

### ResolutionManager

```python
class ResolutionManager:
    """Texture ↔ AI generation çözünürlük yönetimi"""
```

| Method | Parametreler | Dönüş | Açıklama |
|:-------|:-------------|:------|:---------|
| `get_mask_bounding_box(mask, padding)` | `np.ndarray, int` | `tuple[4]` | Mask bbox (x,y,w,h) |
| `find_best_generation_size(w, h)` | `int, int` | `tuple[2]` | En uygun AI boyutu |
| `crop_region(image, bbox)` | `np.ndarray, tuple` | `np.ndarray` | Bölge kırpma |
| `place_region(target, region, bbox)` | `np.ndarray × 2, tuple` | `np.ndarray` | Bölge yerleştirme |

---

### HistoryManager

```python
class HistoryManager:
    """Undo/redo yönetimi"""
```

| Method | Parametreler | Dönüş | Açıklama |
|:-------|:-------------|:------|:---------|
| `push(entry)` | `HistoryEntry` | `None` | Yeni state kaydet |
| `undo()` | — | `HistoryEntry \| None` | Bir adım geri |
| `redo()` | — | `HistoryEntry \| None` | Bir adım ileri |
| `can_undo` | — | `bool` | Geri alınabilir mi? |
| `can_redo` | — | `bool` | İleri alınabilir mi? |
| `get_memory_usage_mb()` | — | `float` | Memory kullanımı (MB) |

---

## 9.3 Blender API Wrapper'lar

### BlenderImageAdapter

| Method | Parametreler | Dönüş | Açıklama |
|:-------|:-------------|:------|:---------|
| `get_pixels_as_numpy(name)` | `str` | `np.ndarray` | Image → NumPy (H,W,4) |
| `set_pixels_from_numpy(name, pixels)` | `str, np.ndarray` | `None` | NumPy → Image |
| `get_or_create_preview(name, w, h)` | `str, int, int` | `bpy.types.Image` | Preview image al/oluştur |
| `backup_original(name)` | `str` | `np.ndarray` | Orijinal yedekle |
| `cleanup_previews()` | — | `None` | Preview'ları temizle |

### BlenderUVAdapter

| Method | Parametreler | Dönüş | Açıklama |
|:-------|:-------------|:------|:---------|
| `get_uv_data(obj)` | `bpy.types.Object` | `list[dict]` | UV koordinatları |
| `get_selected_faces_uvs(obj)` | `bpy.types.Object` | `list[dict]` | Seçili face UV'leri |
| `get_uv_bounding_box(obj)` | `bpy.types.Object` | `dict` | UV bbox |

### BlenderMaterialAdapter

| Method | Parametreler | Dönüş | Açıklama |
|:-------|:-------------|:------|:---------|
| `get_base_color_image(obj)` | `bpy.types.Object` | `bpy.types.Image \| None` | Base Color image |
| `get_texture_images(obj)` | `bpy.types.Object` | `dict[str, Image]` | Tüm texture image'lar |
| `force_viewport_update(context)` | `bpy.types.Context` | `None` | Viewport güncelle |

---

## 9.4 Hata Kodları

### AIErrorCode

| Kod | Kategori | Açıklama | Kullanıcı Mesajı |
|:----|:---------|:---------|:-----------------|
| `API_KEY_MISSING` | Config | API key ayarlanmamış | "API anahtarı ayarlanmamış" |
| `API_KEY_INVALID` | Config | API key geçersiz | "API anahtarı geçersiz" |
| `PROVIDER_NOT_FOUND` | Config | Provider bulunamadı | "Provider bulunamadı" |
| `NETWORK_ERROR` | Network | Bağlantı hatası | "Bağlantı hatası" |
| `TIMEOUT` | Network | Zaman aşımı | "İstek zaman aşımına uğradı" |
| `RATE_LIMIT` | Network | İstek limiti | "İstek limiti aşıldı" |
| `PROVIDER_ERROR` | Provider | Provider hatası | "AI servisi hatası" |
| `UNSUPPORTED_OPERATION` | Provider | Desteklenmeyen işlem | "Bu işlem desteklenmiyor" |
| `INVALID_RESPONSE` | Provider | Geçersiz response | "Geçersiz yanıt alındı" |
| `INVALID_IMAGE_SIZE` | Input | Geçersiz boyut | "Geçersiz image boyutu" |
| `INVALID_MASK` | Input | Geçersiz mask | "Geçersiz mask" |
| `CONTENT_POLICY` | Input | İçerik ihlali | "İçerik politikası ihlali" |
| `UNKNOWN` | Genel | Bilinmeyen hata | "Beklenmeyen hata oluştu" |

---

## 9.5 Blender Operators

### Kayıtlı Operator'lar

| bl_idname | Açıklama | Kısayol |
|:----------|:---------|:--------|
| `ai_texture.generate` | AI generation başlat | `Ctrl+Shift+G` |
| `ai_texture.fill` | AI fill (inpaint) | — |
| `ai_texture.remove` | AI remove | — |
| `ai_texture.apply` | Sonucu uygula | `Ctrl+Shift+A` |
| `ai_texture.cancel` | İptal et | `Escape` |
| `ai_texture.select_variation` | Variation seç | `1-8` |
| `ai_texture.show_error` | Hata dialog | — |
| `ai_texture.cancel_generation` | Generation iptal | — |

### Kayıtlı Panel'ler

| bl_idname | Space | Region | Açıklama |
|:----------|:------|:-------|:---------|
| `AITEXTURE_PT_main_panel` | IMAGE_EDITOR | UI | Ana panel |
| `AITEXTURE_PT_results_panel` | IMAGE_EDITOR | UI | Sonuçlar (child) |
| `AITEXTURE_PT_settings_panel` | IMAGE_EDITOR | UI | Ayarlar (child) |

---

## 9.6 Custom Properties

### Scene Properties (`bpy.types.Scene.ai_texture`)

| Property | Tip | Default | Açıklama |
|:---------|:----|:--------|:---------|
| `operation` | EnumProperty | `'FILL'` | İşlem türü |
| `prompt` | StringProperty | `""` | Generation prompt |
| `negative_prompt` | StringProperty | `""` | Negatif prompt |
| `reference_image` | PointerProperty(Image) | `None` | Referans görsel |
| `provider_enum` | EnumProperty | — | Aktif provider |
| `strength` | FloatProperty | `0.75` | Denoising strength |
| `seed` | IntProperty | `-1` | Random seed |
| `random_seed` | BoolProperty | `True` | Rastgele seed |
| `variation_count` | IntProperty | `4` | Variation sayısı |
| `selected_variation` | IntProperty | `0` | Seçili variation |
| `feather_radius` | IntProperty | `5` | Mask feather (px) |

### WindowManager Properties

| Property | Tip | Açıklama |
|:---------|:----|:---------|
| `ai_texture_progress` | FloatProperty | Progress bar (0-1) |
| `ai_texture_status` | StringProperty | Status mesajı |

---

*Sonraki bölüm: [10 — Güvenlik ve Dağıtım](./10-SECURITY_AND_DEPLOYMENT.md)*
