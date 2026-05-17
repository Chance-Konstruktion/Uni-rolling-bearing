"""Blender-Operatoren für das UNI-Bearing-Addon."""

from __future__ import annotations

import math

import bpy

from . import constants, mesh_builders, raceway
from .geometry import (
    CageDims,
    ResolvedBearing,
    cage_dimensions,
    resolve_geometry,
    suggest_defaults,
    tapered_apex_z,
)
from .tolerances import apply_tolerances


# Blender-Skalierung: UI in mm, Szene in m.
MM_TO_M = 0.001

# Verhindert rekursive Updates, wenn der Auto-Recompute-Callback Properties
# zurückschreibt, die selbst an den Callback gebunden sind.
_AUTO_RECOMPUTE_GUARD = False


def apply_suggested_defaults(props) -> None:
    """Schreibt die typabhängigen Vorschläge in ``props`` zurück.

    Wird sowohl vom expliziten 'Auto-Berechnen'-Operator als auch vom
    Update-Callback der Geometrie-Felder genutzt.
    """
    global _AUTO_RECOMPUTE_GUARD
    if _AUTO_RECOMPUTE_GUARD:
        return
    _AUTO_RECOMPUTE_GUARD = True
    try:
        suggestion = suggest_defaults(
            props.bearing_type,
            props.bore_diameter,
            props.outer_diameter,
            radial_clearance=props.radial_clearance,
            gap_factor=props.gap_factor,
        )
        props.ring_thickness = suggestion.ring_thickness
        props.roller_diameter = suggestion.roller_diameter
        props.element_count = suggestion.element_count
    finally:
        _AUTO_RECOMPUTE_GUARD = False


def _effective_dims(props):
    """Wendet ISO-492-Toleranzklasse und gewählte Toleranzlage auf d/D/B an."""
    return apply_tolerances(
        bore_diameter_mm=props.bore_diameter,
        outer_diameter_mm=props.outer_diameter,
        width_mm=props.width,
        precision_class=props.precision_class,
        position=getattr(props, "tolerance_position", "MEAN"),
    )


def _props_to_resolve_kwargs(props) -> dict:
    eff = _effective_dims(props)
    return dict(
        bearing_type=props.bearing_type,
        bore_diameter=eff.bore_diameter,
        outer_diameter=eff.outer_diameter,
        width=eff.width,
        ring_thickness=props.ring_thickness,
        roller_diameter=props.roller_diameter,
        element_count=props.element_count,
        radial_clearance=props.radial_clearance,
        gap_factor=props.gap_factor,
        auto_fit=props.auto_fit,
    )


def safe_resolve_geometry(props):
    """Kapselt ``resolve_geometry`` für den UI-Draw (fängt unerwartete Fehler ab)."""
    try:
        return resolve_geometry(**_props_to_resolve_kwargs(props))
    except Exception as exc:  # pragma: no cover – defensive für Blender-UI
        return None, f"Interner Fehler: {exc}"


def _tapered_roller_radii(props, spec: ResolvedBearing) -> tuple:
    """Berechnet (r_small, r_large) für die Kegelrolle so, dass sie nach dem
    Kippen um den Kontaktwinkel im zylindrischen Laufbahnspalt bleibt."""
    contact_angle = math.radians(props.contact_angle_deg)
    half_cone = contact_angle * 0.5  # β ≈ α/2 (klassische Apex-Geometrie)
    length = spec.roller_length
    mean_r = spec.roller_d * 0.5

    sin_a = math.sin(contact_angle)
    cos_a = max(math.cos(contact_angle), 1e-6)

    # Radial verfügbarer Halbspalt um den (mittigen) Teilkreis.
    radial_half_gap = (spec.outer_inner_d - spec.inner_outer_d) * 0.5
    clearance = props.radial_clearance
    # Nach dem Tilt wandert das große Stirnflächenzentrum um sin(α)·L/2 nach
    # außen. Dort darf radius_large·cos α nicht über den Restspalt hinaus.
    max_face_r = max(
        0.05,
        (radial_half_gap * 0.5 - sin_a * length * 0.5 - clearance) / cos_a,
    )

    delta = math.sin(half_cone) * length * 0.5
    radius_small = max(0.05, mean_r - delta)
    radius_large = mean_r + delta

    if radius_large > max_face_r:
        scale = max_face_r / radius_large
        radius_large = max_face_r
        radius_small = max(0.05, radius_small * scale)

    return radius_small, radius_large


def _build_rolling_elements(props, spec: ResolvedBearing, collection):
    """Erzeugt alle Wälzkörper und liefert die entstandenen Objekte als Liste."""
    elements = []
    ring_r = spec.pitch_d * 0.5
    roller_r = spec.roller_d * 0.5
    segments = props.segments
    tapered_tilt = math.radians(props.contact_angle_deg)

    if props.bearing_type == constants.TAPERED:
        taper_r_small, taper_r_large = _tapered_roller_radii(props, spec)

    for i in range(spec.element_count):
        a = 2.0 * math.pi * i / spec.element_count
        position = (ring_r * math.cos(a), ring_r * math.sin(a), 0.0)

        if props.bearing_type in (constants.BALL, constants.VGROOVE):
            obj = mesh_builders.add_uv_sphere(
                f"Ball_{i + 1:02d}",
                roller_r,
                position,
                u_segments=segments,
                v_segments=max(8, segments // 2),
                collection=collection,
            )
        elif props.bearing_type in (constants.CYLINDRICAL, constants.NEEDLE):
            obj = mesh_builders.add_cylinder(
                f"Roller_{i + 1:02d}",
                roller_r,
                spec.roller_length,
                position,
                segments=max(12, segments // 2),
                collection=collection,
            )
            obj.rotation_euler[2] = a
        elif props.bearing_type == constants.TAPERED:
            obj = mesh_builders.add_tapered_roller(
                f"TaperRoller_{i + 1:02d}",
                radius_small=taper_r_small,
                radius_large=taper_r_large,
                depth=spec.roller_length,
                location=position,
                segments=max(12, segments // 2),
                collection=collection,
                tilt=tapered_tilt,
            )
            obj.rotation_euler[2] = a
        elif props.bearing_type == constants.SPHERICAL:
            # Zweireihig (DIN 635-2): jede Position erzeugt zwei Rollen
            # symmetrisch um z=0, jeweils um ±α gekippt.
            alpha = math.radians(float(getattr(props, "spherical_contact_angle_deg", 10.0)))
            row_z = raceway.spherical_inner_row_z(
                _effective_dims(props).width, spec.roller_length, alpha
            )
            for sign, label in ((-1, "A"), (+1, "B")):
                pos = (position[0], position[1], sign * row_z)
                row_obj = mesh_builders.add_barrel_roller(
                    f"BarrelRoller_{i + 1:02d}{label}",
                    radius_mid=roller_r,
                    radius_end=roller_r * 0.78,
                    length=spec.roller_length,
                    location=pos,
                    segments=max(12, segments // 2),
                    collection=collection,
                )
                row_obj.rotation_euler[2] = a
                # Tonnen kippen radial nach außen → kleine Stirn zur Lagermitte.
                row_obj.rotation_euler[1] = -sign * alpha
                elements.append(row_obj)
            # Erste obj-Variable überspringen; wir haben bereits über elements
            # erweitert und brauchen kein zusätzliches Element.
            continue
        else:
            raise ValueError(f"Unbekannter Lagertyp: {props.bearing_type}")

        elements.append(obj)

    return elements


# Default-Pocket-Spiel, wenn keine UI-Property gesetzt ist (mm). Real bewegt
# sich das im Bereich 0.05–0.3 mm; hier etwas größer, damit die Subtraktion
# auch bei groben Auflösungen sauber durchschneidet.
POCKET_RADIAL_CLEARANCE_MM = 0.20
# Axialer Überstand des Cutters über die Wälzkörperenden hinaus (mm), damit der
# Boolean garantiert durch das Käfig-Material schneidet und keine Filme stehen
# bleiben.
POCKET_AXIAL_OVERCUT_MM = 0.40


def _pocket_clearance(props) -> float:
    return float(getattr(props, "pocket_clearance_mm", POCKET_RADIAL_CLEARANCE_MM))


def _ladder_cage_parts(props, spec: ResolvedBearing, cage: CageDims, collection):
    """Fallback: einfacher Leiter-Käfig (zwei Endplatten + tangentiale Webs)."""
    parts = []
    for sign, label in ((+1, "Top"), (-1, "Bottom")):
        plate = mesh_builders.make_hollow_ring(
            f"CagePlate_{label}",
            cage.plate_inner_d,
            cage.plate_outer_d,
            cage.plate_thickness,
            props.segments,
            collection=collection,
        )
        plate.location.z = sign * cage.plate_z_offset
        parts.append(plate)

    angular_pitch = 2.0 * math.pi / spec.element_count
    for i in range(spec.element_count):
        theta = (i + 0.5) * angular_pitch
        web = mesh_builders.add_box(
            f"CageWeb_{i + 1:02d}",
            size=(cage.web_radial_size, cage.web_tangential_size, cage.web_axial_length),
            location=(cage.web_pitch_r * math.cos(theta), cage.web_pitch_r * math.sin(theta), 0.0),
            rotation_z=theta,
            collection=collection,
        )
        parts.append(web)
    return parts


def _build_pocket_cutter(props, spec: ResolvedBearing, position, angle, name, collection):
    """Erzeugt einen vergrößerten Wälzkörper-Stempel zur Boolean-Subtraktion."""
    bt = props.bearing_type
    roller_r = spec.roller_d * 0.5
    seg = max(16, props.segments // 2)
    cutter = None

    if bt in (constants.BALL, constants.VGROOVE):
        cutter = mesh_builders.add_uv_sphere(
            name,
            radius=roller_r + _pocket_clearance(props),
            location=position,
            u_segments=seg,
            v_segments=max(12, props.segments // 4),
            collection=collection,
        )
    elif bt in (constants.CYLINDRICAL, constants.NEEDLE):
        cutter = mesh_builders.add_cylinder(
            name,
            radius=roller_r + _pocket_clearance(props),
            depth=spec.roller_length + 2.0 * POCKET_AXIAL_OVERCUT_MM,
            location=position,
            segments=seg,
            collection=collection,
        )
        cutter.rotation_euler[2] = angle
    elif bt == constants.TAPERED:
        taper_r_small, taper_r_large = _tapered_roller_radii(props, spec)
        tilt = math.radians(props.contact_angle_deg)
        cutter = mesh_builders.add_tapered_roller(
            name,
            radius_small=taper_r_small + _pocket_clearance(props),
            radius_large=taper_r_large + _pocket_clearance(props),
            depth=spec.roller_length + 2.0 * POCKET_AXIAL_OVERCUT_MM,
            location=position,
            segments=seg,
            collection=collection,
            tilt=tilt,
        )
        cutter.rotation_euler[2] = angle
    elif bt == constants.SPHERICAL:
        cutter = mesh_builders.add_barrel_roller(
            name,
            radius_mid=roller_r + _pocket_clearance(props),
            radius_end=roller_r * 0.78 + _pocket_clearance(props),
            length=spec.roller_length + 2.0 * POCKET_AXIAL_OVERCUT_MM,
            location=position,
            segments=seg,
            collection=collection,
        )
        cutter.rotation_euler[2] = angle
    return cutter


def _build_ribbon_cage(props, spec: ResolvedBearing, cage: CageDims, collection):
    """Ribbon-/Schnappkäfig aus zwei genieteten Halbringen.

    Klassische Pressblech-Bauart bei Rillenkugellagern: zwei dünne
    Halbringe sitzen oberhalb und unterhalb der Wälzkörpermitte und
    werden durch kleine Niete in den Lücken zwischen den Pockets
    verbunden. Aus jedem Halbring wird der jeweils zugewandte Teil der
    Wälzkörper-Stempel ausgeschnitten, sodass halbschalige Pockets
    entstehen.
    """
    sleeve_width = 2.0 * cage.plate_z_offset + cage.plate_thickness
    if sleeve_width <= 0.5:
        return None

    half_width = sleeve_width * 0.5
    half_offset = half_width * 0.5  # z-Mitte jedes Halbrings
    halves = []
    for sign, label in ((+1, "Top"), (-1, "Bottom")):
        half = mesh_builders.make_hollow_ring(
            f"CageRibbon_{label}",
            cage.plate_inner_d,
            cage.plate_outer_d,
            half_width,
            props.segments,
            collection=collection,
        )
        half.location.z = sign * half_offset
        halves.append(half)

    pitch_r = spec.pitch_d * 0.5

    def _build_cutters_for(label: str):
        cutters = []
        for i in range(spec.element_count):
            a = 2.0 * math.pi * i / spec.element_count
            position = (pitch_r * math.cos(a), pitch_r * math.sin(a), 0.0)
            cutter = _build_pocket_cutter(
                props, spec, position, a, f"_RibbonCutter_{label}_{i + 1:02d}", collection
            )
            if cutter is not None:
                cutters.append(cutter)
        return cutters

    pocket_hits = 0
    for half, side_label in zip(halves, ("T", "B")):
        cutters = _build_cutters_for(side_label)
        pocket_hits += mesh_builders.apply_boolean_difference(half, cutters)
    if pocket_hits == 0:
        for half in halves:
            if half.name in bpy.data.objects:
                bpy.data.objects.remove(half, do_unlink=True)
        return None

    rivets = []
    rivet_r = max(0.25, cage.web_radial_size * 0.25)
    rivet_pitch_r = cage.web_pitch_r
    angular_pitch = 2.0 * math.pi / spec.element_count
    for i in range(spec.element_count):
        theta = (i + 0.5) * angular_pitch
        rivet = mesh_builders.add_cylinder(
            f"CageRivet_{i + 1:02d}",
            radius=rivet_r,
            depth=sleeve_width,
            location=(rivet_pitch_r * math.cos(theta), rivet_pitch_r * math.sin(theta), 0.0),
            segments=max(8, props.segments // 4),
            collection=collection,
        )
        rivets.append(rivet)

    return halves + rivets


def _build_pocket_cage(props, spec: ResolvedBearing, cage: CageDims, collection):
    """Einteiliger Sleeve-Käfig mit typabhängigen Pockets (Boolean-Subtraktion).

    Der Sleeve nutzt die gleichen radialen/axialen Hüllmaße wie der bisherige
    Leiter-Käfig (Endplatten-Ringfenster) – das stellt sicher, dass weder
    Innen- noch Außenlaufbahn berührt werden. Aus dem Sleeve werden für jeden
    Wälzkörper oversized Stempel herausgeschnitten, sodass die Pockets typ-
    spezifisch (Kugel: sphärisch, Zylinder/Nadel: zylindrisch, Kegel: kegelig,
    Tonne: tonnenförmig) im Mesh entstehen.
    """
    sleeve_width = 2.0 * cage.plate_z_offset + cage.plate_thickness
    if sleeve_width <= 0.5:
        return None

    sleeve = mesh_builders.make_hollow_ring(
        "CageSleeve",
        cage.plate_inner_d,
        cage.plate_outer_d,
        sleeve_width,
        props.segments,
        collection=collection,
    )

    pitch_r = spec.pitch_d * 0.5
    cutters = []
    for i in range(spec.element_count):
        a = 2.0 * math.pi * i / spec.element_count
        position = (pitch_r * math.cos(a), pitch_r * math.sin(a), 0.0)
        cutter = _build_pocket_cutter(
            props, spec, position, a, f"_PocketCutter_{i + 1:02d}", collection
        )
        if cutter is not None:
            cutters.append(cutter)

    succeeded = mesh_builders.apply_boolean_difference(sleeve, cutters)
    if succeeded == 0:
        # Kein Pocket konnte geschnitten werden – Sleeve hat keine Funktion mehr.
        if sleeve.name in bpy.data.objects:
            bpy.data.objects.remove(sleeve, do_unlink=True)
        return None
    return sleeve


def _build_cage(props, spec: ResolvedBearing, cage: CageDims, collection):
    """Erzeugt die Käfig-Komponenten und gibt (parts, style) zurück.

    Bevorzugt wird ein Sleeve-Käfig mit typabhängigen Pockets (eine zusammen-
    hängende Komponente). Schlägt der Boolean fehl (z. B. wegen Mesh-Auflösung
    oder degenerierter Cutter), wird der historische Leiter-Käfig als Fallback
    zurückgegeben. ``style`` ist ``"pocket"`` oder ``"ladder"``.
    """
    style_pref = getattr(props, "cage_style", "AUTO")
    if style_pref == "RIBBON":
        parts = _build_ribbon_cage(props, spec, cage, collection)
        if parts:
            return parts, "ribbon"
        # Fallback bei misslungenem Boolean: Sleeve → Leiter.
    if style_pref in ("AUTO", "POCKET"):
        pocket_part = _build_pocket_cage(props, spec, cage, collection)
        if pocket_part is not None:
            return [pocket_part], "pocket"
    if style_pref == "LADDER":
        return _ladder_cage_parts(props, spec, cage, collection), "ladder"
    return _ladder_cage_parts(props, spec, cage, collection), "ladder"


def _inner_ring_profile(props, spec: ResolvedBearing):
    """Wählt das passende Innenring-Querschnittsprofil je Lagertyp."""
    bt = props.bearing_type
    eff = _effective_dims(props)
    if bt in (constants.BALL, constants.VGROOVE):
        return raceway.ball_inner_ring_profile(
            bore_d=eff.bore_diameter,
            shoulder_d=spec.inner_outer_d,
            width=eff.width,
            ball_d=spec.roller_d,
            pitch_d=spec.pitch_d,
            conformity=props.groove_conformity_inner,
            chamfer_mm=props.bearing_chamfer_mm,
        )
    if bt == constants.TAPERED:
        # Bordhöhe so begrenzen, dass der Bord die Außenlaufbahn nicht berührt.
        flange_h = max(0.0, float(getattr(props, "tapered_flange_height_mm", 0.0)))
        if flange_h > 0.0:
            half_w = eff.width * 0.5
            delta = math.tan(math.radians(max(0.0, props.contact_angle_deg))) * half_w
            r_plus = spec.inner_outer_d * 0.5 + delta
            max_flange = max(0.0, spec.outer_inner_d * 0.5 - r_plus - props.radial_clearance)
            flange_h = min(flange_h, max_flange)
        return raceway.tapered_inner_ring_profile(
            bore_d=eff.bore_diameter,
            shoulder_d=spec.inner_outer_d,
            width=eff.width,
            contact_angle_rad=math.radians(props.contact_angle_deg),
            large_flange_height_mm=flange_h,
        )
    if bt == constants.SPHERICAL:
        return raceway.spherical_inner_ring_profile(
            bore_d=eff.bore_diameter,
            shoulder_d=spec.inner_outer_d,
            width=eff.width,
            pitch_d=spec.pitch_d,
            roller_d=spec.roller_d,
            roller_length=spec.roller_length,
            contact_angle_rad=math.radians(
                float(getattr(props, "spherical_contact_angle_deg", 10.0))
            ),
        )
    # Zylinder- und Nadellager nutzen einen einfachen zylindrischen Innenring
    # (Bord liegt am Außenring).
    return raceway.cylindrical_inner_ring_profile(
        bore_d=eff.bore_diameter,
        shoulder_d=spec.inner_outer_d,
        width=eff.width,
    )


def _outer_ring_profile(props, spec: ResolvedBearing):
    """Wählt das passende Außenring-Querschnittsprofil je Lagertyp."""
    bt = props.bearing_type
    eff = _effective_dims(props)
    if bt == constants.BALL:
        return raceway.ball_outer_ring_profile(
            shoulder_d=spec.outer_inner_d,
            outer_d=eff.outer_diameter,
            width=eff.width,
            ball_d=spec.roller_d,
            pitch_d=spec.pitch_d,
            conformity=props.groove_conformity_outer,
            chamfer_mm=props.bearing_chamfer_mm,
        )
    if bt == constants.VGROOVE:
        depth = props.vgroove_depth_mm if props.vgroove_depth_mm > 0.0 else None
        return raceway.vgroove_outer_ring_profile(
            shoulder_d=spec.outer_inner_d,
            outer_d=eff.outer_diameter,
            width=eff.width,
            ball_d=spec.roller_d,
            pitch_d=spec.pitch_d,
            groove_depth=depth,
            groove_half_angle_rad=math.radians(props.vgroove_half_angle_deg),
            conformity=props.groove_conformity_outer,
            chamfer_mm=props.bearing_chamfer_mm,
        )
    if bt in (constants.CYLINDRICAL, constants.NEEDLE):
        return raceway.cylindrical_outer_ring_profile(
            shoulder_d=spec.outer_inner_d,
            outer_d=eff.outer_diameter,
            width=eff.width,
            roller_length=spec.roller_length,
            roller_d=spec.roller_d,
        )
    if bt == constants.TAPERED:
        return raceway.tapered_outer_ring_profile(
            shoulder_d=spec.outer_inner_d,
            outer_d=eff.outer_diameter,
            width=eff.width,
            contact_angle_rad=math.radians(props.contact_angle_deg),
        )
    if bt == constants.SPHERICAL:
        return raceway.spherical_outer_ring_profile(
            shoulder_d=spec.outer_inner_d,
            outer_d=eff.outer_diameter,
            width=eff.width,
            pitch_d=spec.pitch_d,
            roller_d=spec.roller_d,
        )
    # Fallback: einfacher Hohlzylinder.
    return raceway.cylindrical_outer_ring_profile(
        shoulder_d=spec.outer_inner_d,
        outer_d=eff.outer_diameter,
        width=eff.width,
        roller_length=spec.roller_length,
        roller_d=spec.roller_d,
    )


def _build_bearing(props, spec: ResolvedBearing, collection):
    inner_ring = mesh_builders.make_revolved_ring(
        "InnerRing",
        _inner_ring_profile(props, spec),
        props.segments,
        collection=collection,
    )
    outer_ring = mesh_builders.make_revolved_ring(
        "OuterRing",
        _outer_ring_profile(props, spec),
        props.segments,
        collection=collection,
    )
    elements = _build_rolling_elements(props, spec, collection)

    assembly = bpy.data.objects.new("Bearing", None)
    collection.objects.link(assembly)
    assembly.empty_display_type = "PLAIN_AXES"

    parts = [inner_ring, outer_ring, *elements]

    cage_built = False
    cage_style = ""
    if props.use_cage:
        cage = cage_dimensions(
            pitch_d=spec.pitch_d,
            roller_d=spec.roller_d,
            roller_length=spec.roller_length,
            width=_effective_dims(props).width,
            element_count=spec.element_count,
            inner_race_d=spec.inner_outer_d,
            outer_race_d=spec.outer_inner_d,
        )
        if cage is not None:
            cage_parent = bpy.data.objects.new("Cage", None)
            collection.objects.link(cage_parent)
            cage_parent.empty_display_type = "PLAIN_AXES"
            cage_parent.parent = assembly
            cage_parts, cage_style = _build_cage(props, spec, cage, collection)
            for cage_part in cage_parts:
                cage_part.parent = cage_parent
                parts.append(cage_part)
            cage_built = True

    for part in parts:
        if part.parent is None:
            part.parent = assembly

    non_manifold = sum(mesh_builders.count_non_manifold_edges(p.data) for p in parts)
    return assembly, non_manifold, cage_built, cage_style


class _UNI_InfoPopupBase(bpy.types.Operator):
    """Basis für Hilfe-/Info-Buttons.

    Beim *Hovern* zeigt Blender den ``bl_description``-Text als Tooltip an –
    das ist die primäre Erklärungsquelle. Beim *Klick* öffnet sich zusätzlich
    ein Popup mit dem gleichen Text in mehreren Zeilen, falls der Tooltip zu
    schnell ausgeblendet wird.
    """

    bl_options = {"INTERNAL"}

    def execute(self, context):
        text = self.__class__.bl_description
        title = self.__class__.bl_label

        def _draw(self_popup, _ctx):
            for line in text.split("\n"):
                self_popup.layout.label(text=line)

        context.window_manager.popup_menu(_draw, title=title, icon="INFO")
        return {"FINISHED"}


class UNI_OT_info_lagertyp(_UNI_InfoPopupBase):
    bl_idname = "uni_bearing.info_lagertyp"
    bl_label = "Lagertyp wählen"
    bl_description = (
        "Lagerbauformen im Überblick:\n"
        "• Kugellager (DIN 625 / ISO 15): Kugeln, hohe Drehzahl, kombinierte Last.\n"
        "• Zylinderrollenlager (DIN 5412): zylindrische Rollen, hohe Radiallast.\n"
        "• Nadellager (DIN 617): lange dünne Rollen, kompakte Bauhöhe.\n"
        "• Kegelrollenlager (DIN 720 / ISO 355): kombinierte Radial-/Axiallast.\n"
        "• Tonnenlager / Pendelrollen (DIN 635): Schiefstellung ausgleichbar.\n"
        "Die Auswahl steuert Wälzkörperform, verfügbare Presets und ob der "
        "Kontaktwinkel α einstellbar ist."
    )


class UNI_OT_info_normen(_UNI_InfoPopupBase):
    bl_idname = "uni_bearing.info_normen"
    bl_label = "Normen & Presets"
    bl_description = (
        "Norm-Bezugssystem (Stand v0.5):\n"
        "• DIN ISO 15 / DIN 616 – Hauptmaßreihen (d, D, B).\n"
        "• DIN 623 – Bezeichnungssystem (z. B. 6204, 30206, 22210).\n"
        "• ISO 492 / DIN 620 – Toleranzklassen (Normal, P6, P5, P4) – \n"
        "  werden über 'Toleranzlage' (oberes/Mitten-/unteres Maß) in d, D, B umgerechnet.\n"
        "• ISO 5753 / DIN 620 – Lagerluftgruppen (C0, C2, C3, ...).\n"
        "• ISO 281 / ISO 76 – dynamische/statische Tragzahl (geplant).\n"
        "Presets enthalten nur d/D/B; abgeleitete Werte (Wälzkörper-Ø, "
        "Anzahl, Ringstärke) werden vom Resolver gerechnet."
    )


class UNI_OT_info_geometrie(_UNI_InfoPopupBase):
    bl_idname = "uni_bearing.info_geometrie"
    bl_label = "Geometrie-Eingabe"
    bl_description = (
        "Hauptmaße (alle in mm, DIN ISO 15):\n"
        "• d  – Bohrungs-Ø (Wellensitz).\n"
        "• D  – Außen-Ø (Gehäusesitz).\n"
        "• B  – Lagerbreite in Achsrichtung.\n"
        "• Ringstärke – radiale Wandstärke pro Ring; üblich (D−d)/6.\n"
        "Aus diesen Werten ergeben sich Innenlaufbahn-Ø, Außenlaufbahn-Ø und "
        "der nutzbare Wälzkörperraum."
    )


class UNI_OT_info_waelzkoerper(_UNI_InfoPopupBase):
    bl_idname = "uni_bearing.info_waelzkoerper"
    bl_label = "Wälzkörper-Parameter"
    bl_description = (
        "Wälzkörperauslegung:\n"
        "• Wälzkörper-Ø: Kugel/Roller-Ø; max. Laufbahnspalt minus Lagerluft.\n"
        "• Anzahl: wird durch Umfang/Pitch begrenzt (siehe Umfangsspalt).\n"
        "• Umfangsspalt-Faktor: relative Lücke zwischen Wälzkörpern auf dem "
        "Teilkreis (0.10 ≈ 10 %).\n"
        "• Auto-Fit: kürzt zu großen Ø und zu hohe Anzahl automatisch, statt "
        "Fehler zu melden.\n"
        "• Käfig: optionaler einfacher Leiter-Käfig zwischen den Wälzkörpern."
    )


class UNI_OT_info_kontaktwinkel(_UNI_InfoPopupBase):
    bl_idname = "uni_bearing.info_kontaktwinkel"
    bl_label = "Kontaktwinkel α"
    bl_description = (
        "Kontaktwinkel α (DIN 720 / ISO 355):\n"
        "Winkel zwischen Wälzkörperachse und Lagerachse. Alle Rollenachsen "
        "treffen sich auf der Lagerachse in einem gemeinsamen Apex.\n"
        "• 10–18°  Standardreihen (z. B. 30000-Reihe).\n"
        "• 25–30°  steile Reihen (höhere Axialtragfähigkeit).\n"
        "Der berechnete Apex-Z wird als 'tapered_apex_z_mm' am Bearing-Empty "
        "hinterlegt."
    )


class UNI_OT_info_check(_UNI_InfoPopupBase):
    bl_idname = "uni_bearing.info_check"
    bl_label = "Plausibilitäts-Check"
    bl_description = (
        "Live-Vorschau der vom Resolver verwendeten Werte:\n"
        "• Effektiver Roller-Ø: tatsächlich erzeugter Wälzkörper-Ø.\n"
        "• Effektive Anzahl: tatsächliche Anzahl auf dem Teilkreis.\n"
        "• Teilkreis-Ø: zentral zwischen Innen- und Außenlaufbahn.\n"
        "Auto-Fit-Korrekturen werden mit Modifier-Symbol markiert."
    )


class UNI_OT_info_qualitaet(_UNI_InfoPopupBase):
    bl_idname = "uni_bearing.info_qualitaet"
    bl_label = "Mesh-Qualität"
    bl_description = (
        "Auflösung der erzeugten Meshes:\n"
        "• 12–24  niedrige Vorschau, kantig.\n"
        "• 48     Standard – guter Kompromiss zwischen Optik und Größe.\n"
        "• 96–256 für Renderings/Subdivision Surface.\n"
        "Höhere Werte erhöhen Polygonzahl entsprechend linear (Kugel: ~quadratisch)."
    )


class UNI_OT_info_passungen(_UNI_InfoPopupBase):
    bl_idname = "uni_bearing.info_passungen"
    bl_label = "Passungen (DIN 5418)"
    bl_description = (
        "Empfehlung für Welle- und Gehäusepassung nach DIN 5418:\n"
        "• Stufung nach Belastungsfall (Innenring rotiert leicht/normal/\n"
        "  schwer, Außenring rotiert, stillstehend).\n"
        "• ISO 286-Toleranzklassen mit Abmaßen in µm.\n"
        "Für d, D außerhalb 1..250 mm wird nur die Klasse genannt."
    )


class UNI_OT_info_tragzahlen(_UNI_InfoPopupBase):
    bl_idname = "uni_bearing.info_tragzahlen"
    bl_label = "Tragzahlen & Lebensdauer"
    bl_description = (
        "Vereinfachte Tragzahlberechnung nach ISO 76 / ISO 281:\n"
        "• C0r – statische radiale Tragzahl in N.\n"
        "• Cr  – dynamische radiale Tragzahl in N.\n"
        "• L10h – nominelle Lebensdauer in Stunden, wenn P und n > 0.\n"
        "Beiwerte f0/fc sind aus den ISO-Tabellen gemittelt; das Ergebnis "
        "weicht typischerweise um ±15 % von Hersteller-Katalogwerten ab."
    )


class UNI_OT_apply_series_preset(bpy.types.Operator):
    bl_idname = "uni_bearing.apply_series_preset"
    bl_label = "Norm-Preset anwenden"
    bl_description = "Überträgt die Maßwerte des ausgewählten Presets"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uni_bearing
        preset = constants.SERIES_PRESETS.get(props.bearing_type, {}).get(props.series_code)
        if not preset:
            self.report(
                {"WARNING"},
                f"Kein Preset '{props.series_code}' für Lagertyp "
                f"'{props.bearing_type}' hinterlegt. Bitte anderen Reihen-Code "
                f"wählen oder Hauptmaße manuell eingeben.",
            )
            return {"CANCELLED"}
        bore, outer, width = preset
        props.bore_diameter = bore
        props.outer_diameter = outer
        props.width = width

        # Ringstärke/Roller/Anzahl mitziehen, damit das Preset ohne weitere
        # Eingaben ein funktionierendes Lager liefert.
        apply_suggested_defaults(props)
        return {"FINISHED"}


class UNI_OT_auto_calculate(bpy.types.Operator):
    bl_idname = "uni_bearing.auto_calculate"
    bl_label = "Auto-Berechnen"
    bl_description = (
        "Berechnet Ringstärke, Wälzkörper-Ø und Anzahl automatisch aus den "
        "aktuellen Hauptmaßen (d, D) und dem Lagertyp – typische Industrie-"
        "Faustwerte, kein Taschenrechner nötig"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uni_bearing
        if props.bore_diameter >= props.outer_diameter:
            self.report(
                {"ERROR"},
                f"Innendurchmesser ({props.bore_diameter:.2f} mm) muss kleiner "
                f"als Außendurchmesser ({props.outer_diameter:.2f} mm) sein. "
                f"Vorschlag: d auf < {props.outer_diameter:.2f} mm setzen.",
            )
            return {"CANCELLED"}
        apply_suggested_defaults(props)
        self.report(
            {"INFO"},
            (
                f"Ringstärke={props.ring_thickness:.2f} mm, "
                f"Roller-Ø={props.roller_diameter:.2f} mm, n={props.element_count}"
            ),
        )
        return {"FINISHED"}


class UNI_OT_create_bearing(bpy.types.Operator):
    bl_idname = "uni_bearing.create"
    bl_label = "Erstellen"
    bl_description = "Erstellt das konfigurierte Wälzlager als separate, funktionsfähige Komponenten"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uni_bearing
        spec, error = resolve_geometry(**_props_to_resolve_kwargs(props))
        if error or spec is None:
            self.report({"ERROR"}, error or "Geometrie konnte nicht aufgelöst werden.")
            return {"CANCELLED"}

        cursor_location = context.scene.cursor.location.copy()
        collection = mesh_builders.get_or_create_collection(f"Bearing_{props.bearing_type}")
        assembly, non_manifold, cage_built, cage_style = _build_bearing(props, spec, collection)

        assembly.scale = (MM_TO_M, MM_TO_M, MM_TO_M)
        assembly.location = cursor_location
        assembly["bearing_type"] = props.bearing_type
        assembly["norm_hint"] = constants.NORM_HINTS.get(props.bearing_type, "")
        assembly["precision_class"] = props.precision_class
        assembly["tolerance_position"] = props.tolerance_position
        eff = _effective_dims(props)
        assembly["bore_deviation_um"] = round(eff.bore_offset_um, 3)
        assembly["od_deviation_um"] = round(eff.od_offset_um, 3)
        assembly["width_deviation_um"] = round(eff.width_offset_um, 3)
        assembly["effective_bore_mm"] = eff.bore_diameter
        assembly["effective_outer_mm"] = eff.outer_diameter
        assembly["effective_width_mm"] = eff.width
        assembly["radial_clearance_mm"] = props.radial_clearance
        assembly["resolved_roller_d_mm"] = spec.roller_d
        assembly["resolved_element_count"] = spec.element_count
        assembly["resolved_pitch_d_mm"] = spec.pitch_d
        assembly["has_cage"] = cage_built
        if cage_built and cage_style:
            assembly["cage_style"] = cage_style
            assembly["cage_material"] = props.cage_material
            assembly["pocket_clearance_mm"] = props.pocket_clearance_mm
        if props.bearing_type == constants.TAPERED:
            assembly["contact_angle_deg"] = props.contact_angle_deg
            assembly["tapered_apex_z_mm"] = tapered_apex_z(
                spec.pitch_d, spec.roller_length, math.radians(props.contact_angle_deg)
            )
            assembly["tapered_flange_height_mm"] = props.tapered_flange_height_mm
        if props.bearing_type == constants.VGROOVE:
            assembly["vgroove_depth_mm"] = props.vgroove_depth_mm
            assembly["vgroove_half_angle_deg"] = props.vgroove_half_angle_deg
        if props.bearing_type in (constants.BALL, constants.VGROOVE):
            assembly["groove_conformity_inner"] = props.groove_conformity_inner
            assembly["groove_conformity_outer"] = props.groove_conformity_outer
            assembly["bearing_chamfer_mm"] = props.bearing_chamfer_mm

        from . import ratings as ratings_mod
        ratings_result = ratings_mod.compute_ratings(
            bearing_type=props.bearing_type,
            roller_d_mm=spec.roller_d,
            roller_length_mm=spec.roller_length,
            element_count=spec.element_count,
            contact_angle_deg=(
                props.contact_angle_deg
                if props.bearing_type == constants.TAPERED
                else 0.0
            ),
            equivalent_load_P_N=props.equivalent_load_p_n,
            speed_rpm=props.speed_rpm,
        )
        from . import fits as fits_mod
        fit = fits_mod.recommend_fits(
            load_case=props.load_case,
            bore_diameter_mm=eff.bore_diameter,
            outer_diameter_mm=eff.outer_diameter,
        )
        assembly["load_case"] = props.load_case
        assembly["shaft_fit_class"] = fit.shaft_class
        assembly["housing_fit_class"] = fit.housing_class
        if fit.shaft_upper_um is not None:
            assembly["shaft_fit_upper_um"] = fit.shaft_upper_um
            assembly["shaft_fit_lower_um"] = fit.shaft_lower_um
        if fit.housing_upper_um is not None:
            assembly["housing_fit_upper_um"] = fit.housing_upper_um
            assembly["housing_fit_lower_um"] = fit.housing_lower_um

        assembly["static_load_rating_N"] = round(ratings_result.static_C0_N, 1)
        assembly["dynamic_load_rating_N"] = round(ratings_result.dynamic_C_N, 1)
        if ratings_result.L10h is not None:
            assembly["L10h_hours"] = round(ratings_result.L10h, 1)

        if non_manifold > 0:
            self.report(
                {"WARNING"},
                f"Lager erstellt, aber {non_manifold} nicht-manifold Kanten erkannt.",
            )
        elif props.use_cage and not cage_built:
            self.report(
                {"WARNING"},
                "Lager erzeugt, aber für den Käfig war zu wenig Platz – Käfig übersprungen.",
            )
        else:
            cage_msg = " inkl. Käfig" if cage_built else ""
            self.report(
                {"INFO"},
                f"Wälzlager erzeugt{cage_msg} (ØRoller={spec.roller_d:.2f} mm, n={spec.element_count}).",
            )
        return {"FINISHED"}
