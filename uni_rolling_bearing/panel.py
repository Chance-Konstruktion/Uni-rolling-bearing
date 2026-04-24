"""N-Panel für das UNI-Bearing-Addon."""

from __future__ import annotations

import bpy

from . import constants
from .operators import safe_resolve_geometry


class UNI_PT_bearing_panel(bpy.types.Panel):
    bl_label = "UNI Rolling Bearing"
    bl_idname = "UNI_PT_BEARING_PANEL"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UNI Bearings"

    def draw(self, context):
        layout = self.layout
        props = context.scene.uni_bearing

        col = layout.column(align=True)
        col.label(text="1) Lagertyp wählen")
        col.prop(props, "bearing_type", text="")

        norms = layout.box()
        norms.label(text="2) Normen & Presets")
        norms.prop(props, "precision_class")
        norms.prop(props, "radial_clearance")
        norms.prop(props, "use_preset")
        if props.use_preset:
            norms.prop(props, "series_code")
            norms.operator("uni_bearing.apply_series_preset", icon="PRESET")

        dims = layout.box()
        dims.label(text="3) Geometrie")
        dims.prop(props, "bore_diameter")
        dims.prop(props, "outer_diameter")
        dims.prop(props, "width")
        dims.prop(props, "ring_thickness")

        rollers = layout.box()
        rollers.label(text="4) Wälzkörper")
        rollers.prop(props, "roller_diameter")
        rollers.prop(props, "element_count")
        rollers.prop(props, "gap_factor")
        rollers.prop(props, "auto_fit")

        if props.bearing_type in (constants.CYLINDRICAL, constants.NEEDLE):
            rollers.label(text="Hinweis: Zylindrische Rollen werden erzeugt.")
        elif props.bearing_type == constants.TAPERED:
            rollers.label(text="Hinweis: Kegelrollen werden erzeugt.")
        elif props.bearing_type == constants.SPHERICAL:
            rollers.label(text="Hinweis: Tonnenrollen werden erzeugt.")

        preview = layout.box()
        preview.label(text="5) Plausibilitäts-Check")
        spec, error = safe_resolve_geometry(props)
        if error or spec is None:
            preview.alert = True
            preview.label(text=error or "Geometrie unzulässig.", icon="ERROR")
        else:
            preview.label(text=f"Effektiver Roller-Ø: {spec.roller_d:.3f} mm")
            preview.label(text=f"Effektive Anzahl: {spec.element_count}")
            preview.label(text=f"Teilkreis-Ø: {spec.pitch_d:.3f} mm")

        quality = layout.box()
        quality.label(text="6) Mesh-Qualität")
        quality.prop(props, "segments")

        layout.separator()
        layout.operator("uni_bearing.create", icon="MESH_TORUS")
