"""N-Panel für das UNI-Bearing-Addon.

Aufbau: ein Wurzel-Panel ``UNI_PT_bearing_panel`` mit dem Erstellen-Button.
Darunter sitzen mehrere Sub-Panels (über ``bl_parent_id`` verknüpft), die
sich pro Sektion einzeln auf- und zuklappen lassen. Die berechneten
Ergebnisse aus den Eingabesektionen werden in einer eigenen
``Ergebnisse``-Sub-Panel-Box gesammelt.

Jeder Sub-Panel-Header zeigt zusätzlich einen kleinen ``?``-Info-Button,
der beim Klick das passende Erklärungs-Popup öffnet.
"""

from __future__ import annotations

import bpy

from . import constants
from .geometry import validate_against_suggestion
from .operators import safe_resolve_geometry


def _info_button(layout, info_op: str) -> None:
    """Fügt einen kleinen Hilfe-Button in den Layout-Header ein."""
    layout.operator(info_op, text="", icon="QUESTION", emboss=False)


class _UNI_SubPanelBase:
    """Gemeinsame Konfiguration für alle UNI-Sub-Panels."""

    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UNI Bearings"
    bl_parent_id = "UNI_PT_BEARING_PANEL"


class UNI_PT_bearing_panel(bpy.types.Panel):
    bl_label = "UNI Rolling Bearing"
    bl_idname = "UNI_PT_BEARING_PANEL"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "UNI Bearings"

    def draw(self, context):
        layout = self.layout
        layout.operator("uni_bearing.create", icon="MESH_TORUS")


class UNI_PT_section_type(_UNI_SubPanelBase, bpy.types.Panel):
    bl_idname = "UNI_PT_section_type"
    bl_label = "1) Lagertyp wählen"

    def draw_header(self, context):
        _info_button(self.layout, "uni_bearing.info_lagertyp")

    def draw(self, context):
        layout = self.layout
        props = context.scene.uni_bearing
        layout.prop(props, "bearing_type", text="")
        norm_hint = constants.NORM_HINTS.get(props.bearing_type, "")
        if norm_hint:
            layout.label(text=norm_hint, icon="INFO")


class UNI_PT_section_norms(_UNI_SubPanelBase, bpy.types.Panel):
    bl_idname = "UNI_PT_section_norms"
    bl_label = "2) Normen & Presets"

    def draw_header(self, context):
        _info_button(self.layout, "uni_bearing.info_normen")

    def draw(self, context):
        layout = self.layout
        props = context.scene.uni_bearing
        layout.prop(props, "precision_class")
        layout.prop(props, "tolerance_position")
        from .tolerances import apply_tolerances
        eff = apply_tolerances(
            bore_diameter_mm=props.bore_diameter,
            outer_diameter_mm=props.outer_diameter,
            width_mm=props.width,
            precision_class=props.precision_class,
            position=props.tolerance_position,
        )
        if any(abs(x) > 0.0005 for x in (eff.bore_offset_um, eff.od_offset_um, eff.width_offset_um)):
            layout.label(
                text=(
                    f"Δd={eff.bore_offset_um:+.1f} µm  "
                    f"ΔD={eff.od_offset_um:+.1f} µm  "
                    f"ΔB={eff.width_offset_um:+.1f} µm"
                ),
                icon="DRIVER_DISTANCE",
            )
        layout.prop(props, "radial_clearance")
        layout.prop(props, "use_preset")
        if props.use_preset:
            from . import norm_engine
            coding = norm_engine.coding_for(props.bearing_type)
            if coding == "din623":
                preset_col = layout.column(align=True)
                preset_col.prop(props, "mass_series")
                preset_col.prop(props, "bore_code")
                if props.mass_series != "NONE" and props.bore_code != "NONE":
                    combined = f"{props.mass_series}{props.bore_code}"
                    preset_col.label(text=f"Bezeichnung: {combined}", icon="COPY_ID")
                layout.operator("uni_bearing.apply_bore_code_preset", icon="PRESET")
            else:
                layout.prop(props, "series_code")
                layout.operator("uni_bearing.apply_series_preset", icon="PRESET")


class UNI_PT_section_geometry(_UNI_SubPanelBase, bpy.types.Panel):
    bl_idname = "UNI_PT_section_geometry"
    bl_label = "3) Geometrie"

    def draw_header(self, context):
        _info_button(self.layout, "uni_bearing.info_geometrie")

    def draw(self, context):
        layout = self.layout
        props = context.scene.uni_bearing
        layout.prop(props, "bore_diameter")
        layout.prop(props, "outer_diameter")
        layout.prop(props, "width")
        layout.prop(props, "ring_thickness")

        auto_row = layout.row(align=True)
        auto_row.operator("uni_bearing.auto_calculate", icon="MOD_SOLIDIFY")
        auto_row.prop(props, "auto_recompute", text="live", toggle=True)


class UNI_PT_section_rollers(_UNI_SubPanelBase, bpy.types.Panel):
    bl_idname = "UNI_PT_section_rollers"
    bl_label = "4) Wälzkörper"

    def draw_header(self, context):
        _info_button(self.layout, "uni_bearing.info_waelzkoerper")

    def draw(self, context):
        layout = self.layout
        props = context.scene.uni_bearing
        layout.prop(props, "roller_diameter")
        layout.prop(props, "element_count")
        layout.prop(props, "gap_factor")
        layout.prop(props, "auto_fit")
        layout.prop(props, "use_cage")
        if props.use_cage:
            cage_box = layout.column(align=True)
            cage_box.prop(props, "cage_style")
            cage_box.prop(props, "cage_material")
            cage_box.prop(props, "pocket_clearance_mm")
            if props.cage_style == "MASSIVE":
                cage_box.prop(props, "oil_pocket_diameter_mm")

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
        layout.label(
            text=hint if ok else f"Abweichung: {hint}",
            icon="CHECKMARK" if ok else "INFO",
        )

        if props.bearing_type in (constants.CYLINDRICAL, constants.NEEDLE):
            layout.label(text="Hinweis: Zylindrische Rollen werden erzeugt.")
        elif props.bearing_type == constants.TAPERED:
            tapered_row = layout.row(align=True)
            tapered_row.prop(props, "contact_angle_deg")
            tapered_row.operator(
                "uni_bearing.info_kontaktwinkel", text="", icon="QUESTION", emboss=False
            )
            layout.prop(props, "tapered_flange_height_mm")
            tapered_widths = layout.column(align=True)
            tapered_widths.prop(props, "tapered_cone_width_mm")
            tapered_widths.prop(props, "tapered_cup_width_mm")
        elif props.bearing_type == constants.SPHERICAL:
            layout.label(text="Hinweis: Zweireihige Tonnenrollen (DIN 635-2).")
            layout.prop(props, "spherical_contact_angle_deg")
        elif props.bearing_type == constants.VGROOVE:
            layout.label(text="Hinweis: V-Rille im Außenmantel (SG/W-Reihe).")
            layout.prop(props, "vgroove_depth_mm")
            layout.prop(props, "vgroove_half_angle_deg")

        if props.bearing_type in (constants.BALL, constants.VGROOVE):
            conformity = layout.column(align=True)
            conformity.prop(props, "groove_conformity_inner")
            conformity.prop(props, "groove_conformity_outer")
            conformity.prop(props, "bearing_chamfer_mm")


class UNI_PT_section_quality(_UNI_SubPanelBase, bpy.types.Panel):
    bl_idname = "UNI_PT_section_quality"
    bl_label = "5) Mesh-Qualität"

    def draw_header(self, context):
        _info_button(self.layout, "uni_bearing.info_qualitaet")

    def draw(self, context):
        layout = self.layout
        props = context.scene.uni_bearing
        layout.prop(props, "segments")


class UNI_PT_section_ratings(_UNI_SubPanelBase, bpy.types.Panel):
    bl_idname = "UNI_PT_section_ratings"
    bl_label = "6) Tragzahlen & Lebensdauer"

    def draw_header(self, context):
        _info_button(self.layout, "uni_bearing.info_tragzahlen")

    def draw(self, context):
        layout = self.layout
        props = context.scene.uni_bearing
        layout.prop(props, "radial_load_fr_n")
        layout.prop(props, "axial_load_fa_n")
        layout.prop(props, "speed_rpm")


class UNI_PT_section_fits(_UNI_SubPanelBase, bpy.types.Panel):
    bl_idname = "UNI_PT_section_fits"
    bl_label = "7) Passungen (DIN 5418)"

    def draw_header(self, context):
        _info_button(self.layout, "uni_bearing.info_passungen")

    def draw(self, context):
        layout = self.layout
        props = context.scene.uni_bearing
        layout.prop(props, "load_case")


class UNI_PT_section_results(_UNI_SubPanelBase, bpy.types.Panel):
    bl_idname = "UNI_PT_section_results"
    bl_label = "Ergebnisse"

    def draw_header(self, context):
        _info_button(self.layout, "uni_bearing.info_check")

    def draw(self, context):
        layout = self.layout
        props = context.scene.uni_bearing
        spec, error = safe_resolve_geometry(props)

        plaus = layout.box()
        plaus.label(text="Plausibilität", icon="CHECKMARK")
        if error or spec is None:
            plaus.alert = True
            plaus.label(text=error or "Geometrie unzulässig.", icon="ERROR")
        else:
            roller_label = f"Effektiver Roller-Ø: {spec.roller_d:.3f} mm"
            count_label = f"Effektive Anzahl: {spec.element_count}"
            roller_clamped = spec.roller_d + 1e-4 < props.roller_diameter
            count_clamped = spec.element_count < props.element_count
            if roller_clamped:
                roller_label += f"  (angefragt: {props.roller_diameter:.3f})"
            if count_clamped:
                count_label += f"  (angefragt: {props.element_count})"
            plaus.label(
                text=roller_label,
                icon="MODIFIER" if roller_clamped else "NONE",
            )
            plaus.label(
                text=count_label,
                icon="MODIFIER" if count_clamped else "NONE",
            )
            plaus.label(text=f"Teilkreis-Ø: {spec.pitch_d:.3f} mm")
            if roller_clamped or count_clamped:
                plaus.label(text="Auto-Fit hat Werte angepasst.", icon="INFO")

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
                radial_load_Fr_N=props.radial_load_fr_n,
                axial_load_Fa_N=props.axial_load_fa_n,
                speed_rpm=props.speed_rpm,
            )
            ratings_box = layout.box()
            ratings_box.label(text="Tragzahlen", icon="PHYSICS")
            ratings_box.label(
                text=f"γ={r.gamma:.3f}  f0={r.f0:.1f}  fc={r.fc:.1f}",
                icon="OUTLINER_DATA_EMPTY",
            )
            ratings_box.label(text=f"C0r ≈ {r.static_C0_N:,.0f} N")
            ratings_box.label(text=f"Cr  ≈ {r.dynamic_C_N:,.0f} N")
            if props.radial_load_fr_n > 0.0 or props.axial_load_fa_n > 0.0:
                ratings_box.label(
                    text=f"X={r.X:.2f}  Y={r.Y:.2f}  e={r.e:.2f}",
                    icon="DRIVER_TRANSFORM",
                )
                ratings_box.label(text=f"P ≈ {r.P_N:,.0f} N", icon="FORCE_FORCE")
                if (
                    props.bearing_type in (constants.CYLINDRICAL, constants.NEEDLE)
                    and props.axial_load_fa_n > 0.0
                ):
                    ratings_box.label(
                        text="Axiallast wird bei diesem Lagertyp ignoriert.",
                        icon="ERROR",
                    )
            if r.L10h is not None:
                ratings_box.label(text=f"L10h ≈ {r.L10h:,.0f} h", icon="TIME")

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

        fits_box = layout.box()
        fits_box.label(text="Passungen", icon="SETTINGS")
        fits_box.label(
            text=_dev_label("Welle:", fit.shaft_class, fit.shaft_upper_um, fit.shaft_lower_um),
            icon="CON_LOCKTRACK",
        )
        fits_box.label(
            text=_dev_label("Gehäuse:", fit.housing_class, fit.housing_upper_um, fit.housing_lower_um),
            icon="CON_OBJECTSOLVER",
        )
