# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
Image Editor N-panel UI panelleri.

UV Seçimi Maskesi, Model Dropdown Listesi & Custom Model ID, Capability-aware arayüz,
Referans Görsel seçimi, History (Undo/Redo) çubuğu, sonuç gridi ve AI Ayarlarını içerir.
"""

import bpy

from ..blender.image_adapter import BlenderImageAdapter
from ..core.state import get_state, StateStatus
from ..core.config import get_addon_preferences
from ..ai.registry import get_active_provider
from ..ai.capabilities import Capability
from ..texture.history import get_history_manager
from ..texture.mask import MaskProcessor
from ..ai.cache import GenerationCache


class AITEXTURE_PT_main_panel(bpy.types.Panel):
    """Ana AI Texture Painter paneli."""

    bl_label = "AI Texture Painter"
    bl_idname = "AITEXTURE_PT_main_panel"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "AI Texture"

    def draw(self, context):
        layout = self.layout
        props = context.scene.ai_texture
        wm = context.window_manager
        state = get_state()
        hist_mgr = get_history_manager()

        try:
            provider = get_active_provider()
        except Exception:
            provider = None

        # ── History / Undo & Redo Çubuğu ──
        if hist_mgr.can_undo or hist_mgr.can_redo:
            row_hist = layout.row(align=True)
            row_hist.operator("ai_texture.undo", text="Undo", icon='LOOP_BACK')
            row_hist.operator("ai_texture.redo", text="Redo", icon='LOOP_FORWARDS')
            layout.separator()

        # ── Status bar (generation veya hata durumunda) ──
        if state.status == StateStatus.GENERATING:
            box = layout.box()
            row = box.row()
            row.label(text=state.progress_message, icon='TIME')
            row = box.row()
            row.prop(wm, "ai_texture_progress", text="", slider=True)
            layout.separator()
        elif state.status == StateStatus.ERROR:
            box = layout.box()
            row = box.row()
            row.alert = True
            row.label(text=state.error_message or "Hata oluştu!", icon='ERROR')
            layout.separator()

        # ── Operation seçimi ──
        layout.label(text="Operation:", icon='BRUSH_DATA')
        row = layout.row(align=True)
        row.prop(props, "operation", expand=True)

        layout.separator()

        # ── Prompt ──
        layout.label(text="Prompt:", icon='TEXT')
        layout.prop(props, "prompt", text="")

        # Negative prompt (sağlayıcı destekliyorsa)
        if provider is None or provider.supports(Capability.NEGATIVE_PROMPT):
            layout.prop(props, "negative_prompt", text="Negative")

        # ── Referans Görsel (Reference Image) ──
        if provider is None or provider.supports(Capability.REFERENCE_IMAGE):
            layout.separator()
            layout.label(text="Reference Image (Opsiyonel):", icon='IMAGE_DATA')
            layout.template_ID(props, "reference_image", open="image.open")

        layout.separator()

        # ── Aktif image & Akıllı Mask durumu ──
        box = layout.box()
        active_img = BlenderImageAdapter.get_active_image(context)

        box.label(text="Hedef Doku (Target Texture):", icon='IMAGE_DATA')
        box.template_ID(props, "target_image", open="image.open")

        if active_img:
            row = box.row()
            row.label(text=f"Aktif: {active_img.name} ({active_img.size[0]}×{active_img.size[1]})", icon='CHECKMARK')

            # Maske ve 3D Selection durum göstergesi
            obj = getattr(context, "active_object", None)
            mask_name = f"_ai_mask_{active_img.name}"

            row = box.row()
            if obj and obj.type == 'MESH' and obj.mode == 'EDIT':
                from ..blender.selection_group import SelectionGroupResolver
                sg = SelectionGroupResolver.resolve_from_mesh(obj)
                if sg and sg.island_count > 1:
                    row.label(text=f"3D Group: {sg.island_count} UV Islands ({sg.total_faces} Faces)", icon='STICKY_UVS_LOC')
                    sub_row = box.row()
                    sub_row.label(text="Auto Island Packing Active", icon='PACKAGE')
                elif sg and sg.island_count == 1:
                    row.label(text=f"3D Group: 1 UV Island ({sg.total_faces} Faces)", icon='STICKY_UVS_LOC')
                else:
                    row.label(text="Mask: UV Face Selection (Edit Mode)", icon='RESTRICT_SELECT_OFF')
            elif mask_name in bpy.data.images:
                row.label(text="Mask: Custom Paint Mask (_ai_mask_...)", icon='CHECKMARK')
            elif props.operation in {'FILL', 'REMOVE'}:
                row.label(text="Mask: Full Image (Tüm Doku / Edit Mode ile seçin)", icon='INFO')
            else:
                row.label(text="Mask: Full Image (Tüm Doku)", icon='INFO')
        else:
            box.label(text="Aktif texture yok — bir görsel seçin", icon='ERROR')

        layout.separator()

        # ── Generate butonu ──
        generate_row = layout.row()
        generate_row.scale_y = 1.5
        generate_row.operator(
            "ai_texture.generate",
            text="GENERATE PREVIEW",
            icon='PLAY',
        )


class AITEXTURE_PT_results_panel(bpy.types.Panel):
    """Sonuç ve Varyasyon Seçim (Preview & Results) paneli."""

    bl_label = "Preview & Results"
    bl_idname = "AITEXTURE_PT_results_panel"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "AI Texture"
    bl_parent_id = "AITEXTURE_PT_main_panel"

    @classmethod
    def poll(cls, context):
        state = get_state()
        return state.status == StateStatus.PREVIEW

    def draw(self, context):
        layout = self.layout
        state = get_state()

        box = layout.box()
        box.label(text=f"Önizleme: {state.preview_image_name}", icon='HIDE_OFF')

        # ── Çoklu varyasyon seçimi ──
        var_count = len(state.variations)
        if var_count > 1:
            box.separator()
            box.label(text=f"Varyasyonlar ({var_count} adet):", icon='FILE_IMAGE')
            row = box.row(align=True)
            for i in range(var_count):
                is_selected = (i == state.selected_variation)
                op = row.operator(
                    "ai_texture.select_variation",
                    text=f"V{i + 1}",
                    depress=is_selected,
                )
                op.variation_index = i

        box.separator()
        row = box.row(align=True)
        row.scale_y = 1.4

        # Apply butonu
        apply_col = row.column()
        apply_col.operator("ai_texture.apply", text="APPLY (Koru)", icon='CHECKMARK')

        # Cancel butonu
        cancel_col = row.column()
        cancel_col.operator("ai_texture.cancel", text="CANCEL (Geri Al)", icon='CANCEL')


class AITEXTURE_PT_settings_panel(bpy.types.Panel):
    """Ayarlar ve AI Sağlayıcı / API Yapılandırma alt paneli."""

    bl_label = "Settings & AI Setup"
    bl_idname = "AITEXTURE_PT_settings_panel"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "AI Texture"
    bl_parent_id = "AITEXTURE_PT_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.ai_texture
        prefs = get_addon_preferences()

        # ── 1. AI Sağlayıcı ve Model Seçimi ──
        box_api = layout.box()
        box_api.label(text="AI Provider & Model", icon='WORLD')

        if prefs:
            box_api.prop(prefs, "active_provider", text="Provider")

            if prefs.active_provider == 'MOCK':
                box_api.label(text="Mock: API anahtarı gerekmez.", icon='INFO')

            elif prefs.active_provider == 'OPENROUTER':
                box_api.prop(prefs, "openrouter_api_key", text="API Key")
                box_api.prop(prefs, "openrouter_model_choice", text="Model")
                if prefs.openrouter_model_choice == 'CUSTOM':
                    box_api.prop(prefs, "openrouter_custom_model", text="Custom ID")
                box_api.prop(prefs, "openrouter_quality", text="Kalite")

            elif prefs.active_provider == 'FAL_AI':
                box_api.prop(prefs, "fal_api_key", text="API Key")
                box_api.prop(prefs, "fal_model_choice", text="Model")
                if prefs.fal_model_choice == 'CUSTOM':
                    box_api.prop(prefs, "fal_custom_model", text="Custom ID")

            elif prefs.active_provider == 'OPENAI_COMPATIBLE':
                box_api.prop(prefs, "openai_api_key", text="API Key")
                box_api.prop(prefs, "openai_base_url", text="Base URL")
                box_api.prop(prefs, "openai_model_choice", text="Model")
                if prefs.openai_model_choice == 'CUSTOM':
                    box_api.prop(prefs, "openai_custom_model", text="Custom ID")

            elif prefs.active_provider == 'GEMINI':
                box_api.prop(prefs, "gemini_api_key", text="API Key")
                box_api.prop(prefs, "gemini_model_choice", text="Model")
                if prefs.gemini_model_choice == 'CUSTOM':
                    box_api.prop(prefs, "gemini_custom_model", text="Custom ID")
        else:
            layout.operator("screen.userpref_show", text="Open Preferences", icon='PREFERENCES')

        layout.separator()

        # ── 2. Üretim Parametreleri ──
        box_params = layout.box()
        box_params.label(text="Generation Parameters", icon='PREFERENCES')

        try:
            provider = get_active_provider()
        except Exception:
            provider = None

        # Strength
        if provider is None or provider.supports(Capability.STRENGTH_CONTROL):
            box_params.prop(props, "strength", slider=True)

        # Seed
        if provider is None or provider.supports(Capability.SEED_CONTROL):
            row = box_params.row(align=True)
            sub = row.row(align=True)
            sub.active = not props.random_seed
            sub.prop(props, "seed")
            row.prop(
                props, "random_seed",
                toggle=True,
                icon='FILE_REFRESH',
                text="",
            )

        # Variations
        if provider is None or provider.supports(Capability.VARIATIONS):
            box_params.prop(props, "variation_count")

        # Context Padding (Photoshop Generative Fill) & Feather
        box_params.prop(props, "context_padding")
        box_params.prop(props, "feather_radius")

        # ── 3. PBR Doku Araçları (Normal & Roughness) ──
        layout.separator()
        box_pbr = layout.box()
        box_pbr.label(text="PBR Material Suite (Saf NumPy)", icon='MATERIAL')
        
        row_pbr_main = box_pbr.row()
        row_pbr_main.scale_y = 1.3
        row_pbr_main.operator("ai_texture.generate_pbr_set", text="GENERATE PBR SET (Normal + Roughness)", icon='SHADING_RENDERED')

        row_pbr = box_pbr.row(align=True)
        row_pbr.operator("ai_texture.generate_normal", text="Normal Map", icon='NORMALS_FACE')
        row_pbr.operator("ai_texture.generate_roughness", text="Roughness Map", icon='NODE_TEXTURE')

        # ── 4. Bellek Yönetimi ──
        layout.separator()
        box_mem = layout.box()
        hist_mgr = get_history_manager()
        hist_count = len(getattr(hist_mgr, "_stack", []))
        box_mem.label(text=f"History RAM: {hist_count} Adım", icon='INFO')
        row_clean = box_mem.row(align=True)
        row_clean.operator("ai_texture.clear_history", text="Clear History RAM", icon='TRASH')
