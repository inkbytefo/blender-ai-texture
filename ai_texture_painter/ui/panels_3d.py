# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Inkbytefo

"""
3D Viewport UI Panelleri.

3D Görünüm (VIEW_3D) N-Panel'inde "AI Texture" sekmesi altında
ortografik açı hizalama, 3D yüzey boyama ("Paint from Viewport"),
Photoshop benzeri prompt/referans görsel kontrolleri ve önizleme yönetimini sunar.
"""

import bpy

from ..blender.image_adapter import BlenderImageAdapter
from ..core.state import get_state, StateStatus
from ..core.config import get_addon_preferences
from ..ai.registry import get_active_provider
from ..ai.capabilities import Capability
from ..texture.history import get_history_manager


class AITEXTURE_PT_3d_main_panel(bpy.types.Panel):
    """3D Viewport Ana AI Texture Painter Paneli."""

    bl_label = "AI 3D Texture Painter"
    bl_idname = "AITEXTURE_PT_3d_main_panel"
    bl_space_type = 'VIEW_3D'
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

        # ── 1. History / Undo & Redo ──
        if hist_mgr.can_undo or hist_mgr.can_redo:
            row_hist = layout.row(align=True)
            row_hist.operator("ai_texture.undo", text="Undo", icon='LOOP_BACK')
            row_hist.operator("ai_texture.redo", text="Redo", icon='LOOP_FORWARDS')
            layout.separator()

        # ── 2. Hızlı Açı Hizalama (Quick View Alignment) ──
        box_align = layout.box()
        box_align.label(text="Kamera Açısı Hizalama:", icon='CAMERA_DATA')
        grid_align = box_align.grid_flow(columns=3, align=True)
        
        op_r = grid_align.operator("ai_texture.align_view", text="Sağ (3)")
        op_r.view_direction = 'RIGHT'
        op_f = grid_align.operator("ai_texture.align_view", text="Ön (1)")
        op_f.view_direction = 'FRONT'
        op_t = grid_align.operator("ai_texture.align_view", text="Üst (7)")
        op_t.view_direction = 'TOP'
        
        op_l = grid_align.operator("ai_texture.align_view", text="Sol (Ctrl+3)")
        op_l.view_direction = 'LEFT'
        op_b = grid_align.operator("ai_texture.align_view", text="Arka (Ctrl+1)")
        op_b.view_direction = 'BACK'
        op_c = grid_align.operator("ai_texture.align_view", text="Kamera (0)")
        op_c.view_direction = 'CAMERA'

        layout.separator()

        # ── 3. Durum Çubuğu (Generation / Error) ──
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

        # ── 4. Operasyon Seçimi & AI Modeli ──
        prefs = get_addon_preferences()
        if prefs:
            row_p = layout.row(align=True)
            if prefs.active_provider == 'MOCK':
                row_p.alert = True
                row_p.label(text="Sağlayıcı: Mock Provider (Test / Sentetik)", icon='INFO')
            else:
                row_p.label(text=f"AI: {provider.display_name if provider else prefs.active_provider}", icon='WORLD')

        layout.label(text="Operation:", icon='BRUSH_DATA')
        row = layout.row(align=True)
        row.prop(props, "operation", expand=True)

        # ── 5. Prompt & Negative ──
        layout.label(text="Prompt:", icon='TEXT')
        layout.prop(props, "prompt", text="")

        if provider is None or provider.supports(Capability.NEGATIVE_PROMPT):
            layout.prop(props, "negative_prompt", text="Negative")

        # ── 6. Referans Görsel (Reference Image) ──
        if provider is None or provider.supports(Capability.REFERENCE_IMAGE):
            layout.separator()
            layout.label(text="Reference Image (Opsiyonel):", icon='IMAGE_DATA')
            layout.template_ID(props, "reference_image", open="image.open")

        layout.separator()

        # ── 7. Aktif Model ve Hedef Doku ──
        box_stat = layout.box()
        obj = context.active_object
        active_img = BlenderImageAdapter.get_active_image(context)

        if obj and obj.type == 'MESH':
            box_stat.label(text=f"Model: {obj.name}", icon='OBJECT_DATA')
            
            # Hedef doku seçici ve göstergesi
            box_stat.label(text="Hedef Doku (Target Texture):", icon='IMAGE_DATA')
            box_stat.template_ID(props, "target_image", open="image.open")
            
            if active_img:
                box_stat.label(text=f"Aktif Doku: {active_img.name} ({active_img.size[0]}×{active_img.size[1]})", icon='CHECKMARK')
            else:
                box_stat.label(text="Materyal dokusu bulunamadı!", icon='ERROR')

            if obj.mode == 'EDIT':
                box_stat.label(text="Mod: Edit Mode (Seçili yüzeyler boyanacak)", icon='EDITMODE_HLT')
            else:
                box_stat.label(text="Mod: Object Mode (Görünen tüm yüzeyler boyanacak)", icon='OBJECT_DATAMODE')
        else:
            box_stat.label(text="Bir 3D Mesh nesnesi seçin", icon='ERROR')

        layout.separator()

        # ── 8. Ana Buton: Paint from Viewport ──
        row_gen = layout.row()
        row_gen.scale_y = 1.6
        row_gen.operator(
            "ai_texture.paint_from_view",
            text="PAINT FROM VIEWPORT",
            icon='BRUSH_DATA',
        )


class AITEXTURE_PT_3d_results_panel(bpy.types.Panel):
    """3D Viewport Sonuç ve Önizleme Onaylama Paneli."""

    bl_label = "3D Preview & Results"
    bl_idname = "AITEXTURE_PT_3d_results_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AI Texture"
    bl_parent_id = "AITEXTURE_PT_3d_main_panel"

    @classmethod
    def poll(cls, context):
        state = get_state()
        return state.status == StateStatus.PREVIEW

    def draw(self, context):
        layout = self.layout
        state = get_state()

        box = layout.box()
        box.label(text=f"Önizleme Aktif: {state.preview_image_name}", icon='HIDE_OFF')

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

        apply_col = row.column()
        apply_col.operator("ai_texture.apply", text="APPLY (Koru)", icon='CHECKMARK')

        cancel_col = row.column()
        cancel_col.operator("ai_texture.cancel", text="CANCEL (Geri Al)", icon='CANCEL')


class AITEXTURE_PT_3d_settings_panel(bpy.types.Panel):
    """3D Viewport Ayarlar ve Parametreler alt paneli."""

    bl_label = "3D Paint Parameters & AI Setup"
    bl_idname = "AITEXTURE_PT_3d_settings_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "AI Texture"
    bl_parent_id = "AITEXTURE_PT_3d_main_panel"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.ai_texture
        prefs = get_addon_preferences()

        # Provider seçici
        box_api = layout.box()
        box_api.label(text="AI Provider & Model", icon='WORLD')
        if prefs:
            box_api.prop(prefs, "active_provider", text="Provider")
            if prefs.active_provider == 'OPENROUTER':
                box_api.prop(prefs, "openrouter_model_choice", text="Model")
            elif prefs.active_provider == 'FAL_AI':
                box_api.prop(prefs, "fal_model_choice", text="Model")
            elif prefs.active_provider == 'OPENAI_COMPATIBLE':
                box_api.prop(prefs, "openai_model_choice", text="Model")
            elif prefs.active_provider == 'GEMINI':
                box_api.prop(prefs, "gemini_model_choice", text="Model")

        # Üretim ayarları
        box_params = layout.box()
        box_params.label(text="Generation Parameters", icon='PREFERENCES')
        box_params.prop(props, "strength", slider=True)
        box_params.prop(props, "variation_count")
        box_params.prop(props, "context_padding")
        box_params.prop(props, "feather_radius")
