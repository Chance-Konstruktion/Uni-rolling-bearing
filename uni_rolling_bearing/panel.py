"""N-Panel für das UNI-Bearing-Addon.

Jede Sektion bekommt einen kleinen Info-Button (Fragezeichen). Beim Hovern
zeigt Blender den ``bl_description``-Text als Tooltip; ein Klick öffnet ein
Popup mit der gleichen Erklärung in mehreren Zeilen.
"""

from __future__ import annotations

import bpy

from . import constants
from .operators import safe_resolve_geometry


def _section_header(layout, title: str, info_op: str) -> bpy.types.UILayout:
    """Erzeugt eine Box mit Titel und ``?``-Hover-Hilfe und liefert die Box zurück."""
    box = layout.box()
    header = box.row(align=True)
    header.label(text=title)
    header.operator(info_op, text="", icon="QUESTION", emboss=False)
    return box


class UNI_PT_bearing_panel(bpy.types.Panel):
    bl_label = "UNI Rolling Bearing"
    bl_idname = "UNI_PT_BEARING_PANEL"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UNI Bearings"

    def draw(self, context):
        layout = self.layout
        props = context.scene.uni_bearing

        bearing_box = _section_header(layout, "1) Lagertyp wählen", "uni_bearing.info_lagertyp")
        bearing_box.prop(props, "bearing_type", text="")
        norm_hint = constants.NORM_HINTS.get(props.bearing_type, "")
        if norm_hint:
            bearing_box.label(text=norm_hint, icon="INFO")

        norms = _section_header(layout, "2) Normen & Presets", "uni_bearing.info_normen")
        norms.prop(props, "precision_class")
        norms.prop(props, "radial_clearance")
        norms.prop(props, "use_preset")
        if props.use_preset:
            norms.prop(props, "series_code")
            norms.operator("uni_bearing.apply_series_preset", icon="PRESET")

        dims = _section_header(layout, "3) Geometrie", "uni_bearing.info_geometrie")
        dims.prop(props, "bore_diameter")
        dims.prop(props, "outer_diameter")
        dims.prop(props, "width")
        dims.prop(props, "ring_thickness")

        rollers = _section_header(layout, "4) Wälzkörper", "uni_bearing.info_waelzkoerper")
        rollers.prop(props, "roller_diameter")
        rollers.prop(props, "element_count")
        rollers.prop(props, "gap_factor")
        rollers.prop(props, "auto_fit")
        rollers.prop(props, "use_cage")

        if props.bearing_type in (constants.CYLINDRICAL, constants.NEEDLE):
            rollers.label(text="Hinweis: Zylindrische Rollen werden erzeugt.")
        elif props.bearing_type == constants.TAPERED:
            tapered_row = rollers.row(align=True)
            tapered_row.prop(props, "contact_angle_deg")
            tapered_row.operator(
                "uni_bearing.info_kontaktwinkel", text="", icon="QUESTION", emboss=False
            )
        elif props.bearing_type == constants.SPHERICAL:
            rollers.label(text="Hinweis: Tonnenrollen werden erzeugt.")

        preview = _section_header(layout, "5) Plausibilitäts-Check", "uni_bearing.info_check")
        spec, error = safe_resolve_geometry(props)
        if error or spec is None:
            preview.alert = True
            preview.label(text=error or "Geometrie unzulässig.", icon="ERROR")
        else:
            roller_label = f"Effektiver Roller-Ø: {spec.roller_d:.3f} mm"
            count_label = f"Effektive Anzahl: {spec.element_count}"
            roller_clamped = spec.roller_d + 1e-4 < props.roller_diameter
            count_clamped = spec.element_count < props.element_count
            if roller_clamped:
                roller_label += f"  (angefragt: {props.roller_diameter:.3f})"
            if count_clamped:
                count_label += f"  (angefragt: {props.element_count})"
            preview.label(
                text=roller_label,
                icon="MODIFIER" if roller_clamped else "NONE",
            )
            preview.label(
                text=count_label,
                icon="MODIFIER" if count_clamped else "NONE",
            )
            preview.label(text=f"Teilkreis-Ø: {spec.pitch_d:.3f} mm")
            if roller_clamped or count_clamped:
                preview.label(text="Auto-Fit hat Werte angepasst.", icon="INFO")

        quality = _section_header(layout, "6) Mesh-Qualität", "uni_bearing.info_qualitaet")
        quality.prop(props, "segments")

        layout.separator()
        layout.operator("uni_bearing.create", icon="MESH_TORUS")
