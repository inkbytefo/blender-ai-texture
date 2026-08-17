# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
PBR Generation Operators.

Mevcut dokudan tek tıkla Tangent-Space Normal Map ve Roughness Map türeten,
yeni bağımsız görseller olarak kaydeden/pack eden ve Blender Shader Node ağacına
(Principled BSDF) otomatik bağlayan profesyonel operatörler.
"""

import bpy

from ..blender.image_adapter import BlenderImageAdapter
from ..blender.material_adapter import BlenderMaterialAdapter
from ..texture.pbr import PBRGenerator
from ..core.logging import get_logger

logger = get_logger("operators.pbr_ops")


def _create_unique_pbr_image(base_name: str, map_type: str, width: int, height: int) -> bpy.types.Image:
    """Benzersiz isimde yeni bir PBR görsel nesnesi oluşturur ve Non-Color olarak ayarlar."""
    clean_base = base_name.replace("_Normal", "").replace("_Roughness", "")
    target_name = f"{clean_base}_{map_type}"
    
    # Benzersiz isim kontrolü
    idx = 1
    final_name = target_name
    while final_name in bpy.data.images:
        final_name = f"{target_name}_{idx:03d}"
        idx += 1

    img = bpy.data.images.new(name=final_name, width=width, height=height, alpha=True, float_buffer=False)
    
    # Non-Color renk uzayını ata
    try:
        img.colorspace_settings.name = 'Non-Color'
    except Exception:
        pass

    return img


class AITEXTURE_OT_generate_normal(bpy.types.Operator):
    """Aktif dokudan Tangent-Space Normal Map (OpenGL standardı) üretir, yeni görsel olarak kaydeder ve materyale bağlar."""

    bl_idname = "ai_texture.generate_normal"
    bl_label = "Generate Normal Map"
    bl_description = "Aktif dokudan yüksek kaliteli Tangent-Space Normal Map türet, yeni görsel olarak kaydet ve materyale bağla"
    bl_options = {'REGISTER', 'UNDO'}

    strength: bpy.props.FloatProperty(
        name="Strength",
        description="Normal kabartma gücü",
        default=1.5,
        min=0.1,
        max=10.0,
    )

    auto_connect: bpy.props.BoolProperty(
        name="Auto Connect to Material",
        description="Üretilen Normal Map'i aktif materyalin Principled BSDF Normal soketine bağla",
        default=True,
    )

    pack_image: bpy.props.BoolProperty(
        name="Pack into Blend File",
        description="Görseli .blend dosyasına kalıcı olarak göm (Pack)",
        default=True,
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return BlenderImageAdapter.get_active_image(context) is not None

    def execute(self, context: bpy.types.Context):
        base_img = BlenderImageAdapter.get_active_image(context)
        if not base_img:
            self.report({'ERROR'}, "Aktif texture bulunamadı!")
            return {'CANCELLED'}

        src_pixels = BlenderImageAdapter.image_to_numpy(base_img)
        h, w = src_pixels.shape[:2]
        
        # 1. Normal Map türet (Saf NumPy)
        norm_pixels = PBRGenerator.generate_normal_map(src_pixels, strength=self.strength)

        # 2. Yeni bağımsız görsel olarak oluştur
        norm_img = _create_unique_pbr_image(base_img.name, "Normal", w, h)
        BlenderImageAdapter.numpy_to_image(norm_pixels, norm_img)

        # 3. Pack et (Blend dosyasına göm)
        if self.pack_image:
            try:
                norm_img.pack()
            except Exception:
                pass

        # 4. Aktif materyale otomatik bağla
        obj = context.active_object
        if self.auto_connect and obj and obj.type == 'MESH':
            BlenderMaterialAdapter.connect_normal_map_to_material(obj, norm_img, strength=self.strength)

        # 5. Image Editor'de göster ve ekranı tazele
        if context.space_data and context.space_data.type == 'IMAGE_EDITOR':
            context.space_data.image = norm_img

        BlenderMaterialAdapter.force_viewport_redraw()

        self.report({'INFO'}, f"Normal Map oluşturuldu ve kaydedildi: {norm_img.name}")
        logger.info("Normal Map created and connected", image=norm_img.name, strength=self.strength)
        return {'FINISHED'}


class AITEXTURE_OT_generate_roughness(bpy.types.Operator):
    """Aktif dokudan Roughness haritası üretir, yeni görsel olarak kaydeder ve materyale bağlar."""

    bl_idname = "ai_texture.generate_roughness"
    bl_label = "Generate Roughness Map"
    bl_description = "Aktif dokudan pürüzlülük (Roughness) haritası türet, yeni görsel olarak kaydet ve materyale bağla"
    bl_options = {'REGISTER', 'UNDO'}

    base_roughness: bpy.props.FloatProperty(
        name="Base Roughness",
        description="Ortalama pürüzlülük değeri (0.0 = ayna gibi parlak, 1.0 = mat)",
        default=0.5,
        min=0.0,
        max=1.0,
    )

    invert: bpy.props.BoolProperty(
        name="Invert (Glossiness)",
        description="Değerleri tersle",
        default=False,
    )

    auto_connect: bpy.props.BoolProperty(
        name="Auto Connect to Material",
        description="Üretilen Roughness haritasını aktif materyalin Principled BSDF Roughness soketine bağla",
        default=True,
    )

    pack_image: bpy.props.BoolProperty(
        name="Pack into Blend File",
        description="Görseli .blend dosyasına kalıcı olarak göm (Pack)",
        default=True,
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return BlenderImageAdapter.get_active_image(context) is not None

    def execute(self, context: bpy.types.Context):
        base_img = BlenderImageAdapter.get_active_image(context)
        if not base_img:
            self.report({'ERROR'}, "Aktif texture bulunamadı!")
            return {'CANCELLED'}

        src_pixels = BlenderImageAdapter.image_to_numpy(base_img)
        h, w = src_pixels.shape[:2]

        # 1. Roughness Map türet
        rough_pixels = PBRGenerator.generate_roughness_map(
            src_pixels,
            invert=self.invert,
            base_roughness=self.base_roughness,
        )

        # 2. Yeni bağımsız görsel olarak oluştur
        rough_img = _create_unique_pbr_image(base_img.name, "Roughness", w, h)
        BlenderImageAdapter.numpy_to_image(rough_pixels, rough_img)

        # 3. Pack et
        if self.pack_image:
            try:
                rough_img.pack()
            except Exception:
                pass

        # 4. Aktif materyale otomatik bağla
        obj = context.active_object
        if self.auto_connect and obj and obj.type == 'MESH':
            BlenderMaterialAdapter.connect_roughness_map_to_material(obj, rough_img)

        # 5. Image Editor'de göster ve tazele
        if context.space_data and context.space_data.type == 'IMAGE_EDITOR':
            context.space_data.image = rough_img

        BlenderMaterialAdapter.force_viewport_redraw()

        self.report({'INFO'}, f"Roughness Map oluşturuldu ve kaydedildi: {rough_img.name}")
        logger.info("Roughness Map created and connected", image=rough_img.name)
        return {'FINISHED'}


class AITEXTURE_OT_generate_pbr_set(bpy.types.Operator):
    """Aktif dokudan tek tıkla hem Normal Map hem de Roughness Map türetir ve materyale bağlar."""

    bl_idname = "ai_texture.generate_pbr_set"
    bl_label = "Generate Complete PBR Set"
    bl_description = "Aktif dokudan tek tıkla Normal ve Roughness haritalarını üret, yeni görseller olarak kaydet ve materyale bağla"
    bl_options = {'REGISTER', 'UNDO'}

    normal_strength: bpy.props.FloatProperty(
        name="Normal Strength",
        description="Normal kabartma gücü",
        default=1.5,
        min=0.1,
        max=10.0,
    )

    base_roughness: bpy.props.FloatProperty(
        name="Base Roughness",
        description="Ortalama pürüzlülük değeri",
        default=0.5,
        min=0.0,
        max=1.0,
    )

    auto_connect: bpy.props.BoolProperty(
        name="Auto Connect to Material",
        description="Oluşturulan tüm haritaları otomatik olarak Principled BSDF node'larına bağla",
        default=True,
    )

    @classmethod
    def poll(cls, context: bpy.types.Context) -> bool:
        return BlenderImageAdapter.get_active_image(context) is not None

    def execute(self, context: bpy.types.Context):
        base_img = BlenderImageAdapter.get_active_image(context)
        if not base_img:
            self.report({'ERROR'}, "Aktif texture bulunamadı!")
            return {'CANCELLED'}

        src_pixels = BlenderImageAdapter.image_to_numpy(base_img)
        h, w = src_pixels.shape[:2]
        obj = context.active_object

        # 1. Normal Map üret & kaydet
        norm_pixels = PBRGenerator.generate_normal_map(src_pixels, strength=self.normal_strength)
        norm_img = _create_unique_pbr_image(base_img.name, "Normal", w, h)
        BlenderImageAdapter.numpy_to_image(norm_pixels, norm_img)
        try:
            norm_img.pack()
        except Exception:
            pass

        # 2. Roughness Map üret & kaydet
        rough_pixels = PBRGenerator.generate_roughness_map(src_pixels, base_roughness=self.base_roughness)
        rough_img = _create_unique_pbr_image(base_img.name, "Roughness", w, h)
        BlenderImageAdapter.numpy_to_image(rough_pixels, rough_img)
        try:
            rough_img.pack()
        except Exception:
            pass

        # 3. Materyale bağla
        if self.auto_connect and obj and obj.type == 'MESH':
            BlenderMaterialAdapter.connect_normal_map_to_material(obj, norm_img, strength=self.normal_strength)
            BlenderMaterialAdapter.connect_roughness_map_to_material(obj, rough_img)

        BlenderMaterialAdapter.force_viewport_redraw()

        self.report({'INFO'}, f"Eksiksiz PBR Seti oluşturuldu: {norm_img.name}, {rough_img.name}")
        logger.info("Complete PBR Set generated successfully", normal=norm_img.name, roughness=rough_img.name)
        return {'FINISHED'}
