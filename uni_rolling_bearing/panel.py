"""N-Panel für das UNI-Bearing-Addon.

Jede Sektion bekommt einen kleinen Info-Button (Fragezeichen). Beim Hovern
zeigt Blender den ``bl_description``-Text als Tooltip; ein Klick öffnet ein
Popup mit der gleichen Erklärung in mehreren Zeilen.
"""

from __future__ import annotations

import bpy

from . import constants
from .geometry import validate_against_suggestion
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
        norms.prop(props, "tolerance_position")
        from .tolerances import apply_tolerances
        eff = apply_tolerances(
            bore_diameter_mm=props.bore_diameter,
            outer_diameter_mm=props.outer_diameter,
            width_mm=props.width,
            precision_class=props.precision_class,
            position=props.tolerance_position,
        )
        if any(abs(x) > 0.0005 for x in (eff.bore_offset_um, eff.od_offset_um, eff.width_offset_um)):
            norms.label(
                text=(
                    f"Δd={eff.bore_offset_um:+.1f} µm  "
                    f"ΔD={eff.od_offset_um:+.1f} µm  "
                    f"ΔB={eff.width_offset_um:+.1f} µm"
                ),
                icon="DRIVER_DISTANCE",
            )
        norms.prop(props, "radial_clearance")
        norms.prop(props, "use_preset")
        if props.use_preset:
            from . import norm_engine
            coding = norm_engine.coding_for(props.bearing_type)
            if coding == "din623":
                # Workflow: Reihe → Bohrungskennzahl (UI-Folge der Norm).
                preset_col = norms.column(align=True)
                preset_col.prop(props, "mass_series")
                preset_col.prop(props, "bore_code")
                if props.mass_series != "NONE" and props.bore_code != "NONE":
                    combined = f"{props.mass_series}{props.bore_code}"
                    preset_col.label(text=f"Bezeichnung: {combined}", icon="COPY_ID")
                norms.operator("uni_bearing.apply_bore_code_preset", icon="PRESET")
            else:
                # Direkte Code-Auswahl für 'direct'-Coding (z. B. SG10, HK0808).
                norms.prop(props, "series_code")
                norms.operator("uni_bearing.apply_series_preset", icon="PRESET")

        dims = _section_header(layout, "3) Geometrie", "uni_bearing.info_geometrie")
        dims.prop(props, "bore_diameter")
        dims.prop(props, "outer_diameter")
        dims.prop(props, "width")
        dims.prop(props, "ring_thickness")

        # Auto-Berechnen: füllt Ringstärke + Wälzkörper-Ø + Anzahl typgerecht.
        auto_row = dims.row(align=True)
        auto_row.operator("uni_bearing.auto_calculate", icon="MOD_SOLIDIFY")
        auto_row.prop(props, "auto_recompute", text="live", toggle=True)

        rollers = _section_header(layout, "4) Wälzkörper", "uni_bearing.info_waelzkoerper")
        rollers.prop(props, "roller_diameter")
        rollers.prop(props, "element_count")
        rollers.prop(props, "gap_factor")
        rollers.prop(props, "auto_fit")
        rollers.prop(props, "use_cage")
        if props.use_cage:
            cage_box = rollers.column(align=True)
            cage_box.prop(props, "cage_style")
            cage_box.prop(props, "cage_material")
            cage_box.prop(props, "pocket_clearance_mm")

        # Validierung: wie weit liegen die aktuellen Werte vom Vorschlag entfernt?
        ok, hint = validate_against_suggestion(
            bearing_type=props.bearing_type,
            bore_diameter=props.bore_diameter,
            outer_diameter=props.outer_diameter,
            ring_thickness=props.ring_thickness,
            roller_diameter=props.roller_diameter,
            element_count=props.element_count,
            radial_clearance=props.radial_clearance,
            gap_factor=props.gap_factor,
        )
        rollers.label(
            text=hint if ok else f"Abweichung: {hint}",
            icon="CHECKMARK" if ok else "INFO",
        )

        if props.bearing_type in (constants.CYLINDRICAL, constants.NEEDLE):
            rollers.label(text="Hinweis: Zylindrische Rollen werden erzeugt.")
        elif props.bearing_type == constants.TAPERED:
            tapered_row = rollers.row(align=True)
            tapered_row.prop(props, "contact_angle_deg")
            tapered_row.operator(
                "uni_bearing.info_kontaktwinkel", text="", icon="QUESTION", emboss=False
            )
            rollers.prop(props, "tapered_flange_height_mm")
            tapered_widths = rollers.column(align=True)
            tapered_widths.prop(props, "tapered_cone_width_mm")
            tapered_widths.prop(props, "tapered_cup_width_mm")
        elif props.bearing_type == constants.SPHERICAL:
            rollers.label(text="Hinweis: Zweireihige Tonnenrollen (DIN 635-2).")
            rollers.prop(props, "spherical_contact_angle_deg")
        elif props.bearing_type == constants.VGROOVE:
            rollers.label(text="Hinweis: V-Rille im Außenmantel (SG/W-Reihe).")
            rollers.prop(props, "vgroove_depth_mm")
            rollers.prop(props, "vgroove_half_angle_deg")

        if props.bearing_type in (constants.BALL, constants.VGROOVE):
            conformity = rollers.column(align=True)
            conformity.prop(props, "groove_conformity_inner")
            conformity.prop(props, "groove_conformity_outer")
            conformity.prop(props, "bearing_chamfer_mm")

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

        ratings_box = _section_header(
            layout, "7) Tragzahlen & Lebensdauer", "uni_bearing.info_tragzahlen"
        )
        ratings_box.prop(props, "equivalent_load_p_n")
        ratings_box.prop(props, "speed_rpm")
        if spec is not None and error is None:
            from . import ratings as ratings_mod
            angle = (
                props.contact_angle_deg
                if props.bearing_type == constants.TAPERED
                else 0.0
            )
            r = ratings_mod.compute_ratings(
                bearing_type=props.bearing_type,
                roller_d_mm=spec.roller_d,
                roller_length_mm=spec.roller_length,
                element_count=spec.element_count,
                pitch_d_mm=spec.pitch_d,
                contact_angle_deg=angle,
                equivalent_load_P_N=props.equivalent_load_p_n,
                speed_rpm=props.speed_rpm,
            )
            ratings_box.label(
                text=f"γ={r.gamma:.3f}  f0={r.f0:.1f}  fc={r.fc:.1f}",
                icon="OUTLINER_DATA_EMPTY",
            )
            ratings_box.label(text=f"C0r ≈ {r.static_C0_N:,.0f} N", icon="PHYSICS")
            ratings_box.label(text=f"Cr  ≈ {r.dynamic_C_N:,.0f} N", icon="PHYSICS")
            if r.L10h is not None:
                ratings_box.label(text=f"L10h ≈ {r.L10h:,.0f} h", icon="TIME")

        fits_box = _section_header(
            layout, "8) Passungen (DIN 5418)", "uni_bearing.info_passungen"
        )
        fits_box.prop(props, "load_case")
        from . import fits as fits_mod
        fit = fits_mod.recommend_fits(
            load_case=props.load_case,
            bore_diameter_mm=props.bore_diameter,
            outer_diameter_mm=props.outer_diameter,
        )

        def _dev_label(prefix: str, cls: str, u, l):
            if u is None or l is None:
                return f"{prefix} {cls} (außerhalb Tabelle)"
            return f"{prefix} {cls}  {u:+d}/{l:+d} µm"

        fits_box.label(
            text=_dev_label("Welle:", fit.shaft_class, fit.shaft_upper_um, fit.shaft_lower_um),
            icon="CON_LOCKTRACK",
        )
        fits_box.label(
            text=_dev_label("Gehäuse:", fit.housing_class, fit.housing_upper_um, fit.housing_lower_um),
            icon="CON_OBJECTSOLVER",
        )

        layout.separator()
        layout.operator("uni_bearing.create", icon="MESH_TORUS")
