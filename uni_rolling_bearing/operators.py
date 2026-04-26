"""Blender-Operatoren für das UNI-Bearing-Addon."""

from __future__ import annotations

import math

import bpy

from . import constants, mesh_builders
from .geometry import (
    CageDims,
    ResolvedBearing,
    cage_dimensions,
    resolve_geometry,
    suggest_defaults,
    tapered_apex_z,
)


# Blender-Skalierung: UI in mm, Szene in m.
MM_TO_M = 0.001


def _props_to_resolve_kwargs(props) -> dict:
    return dict(
        bearing_type=props.bearing_type,
        bore_diameter=props.bore_diameter,
        outer_diameter=props.outer_diameter,
        width=props.width,
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


def _build_rolling_elements(props, spec: ResolvedBearing, collection):
    """Erzeugt alle Wälzkörper und liefert die entstandenen Objekte als Liste."""
    elements = []
    ring_r = spec.pitch_d * 0.5
    roller_r = spec.roller_d * 0.5
    segments = props.segments
    tapered_tilt = math.radians(props.contact_angle_deg)

    for i in range(spec.element_count):
        a = 2.0 * math.pi * i / spec.element_count
        position = (ring_r * math.cos(a), ring_r * math.sin(a), 0.0)

        if props.bearing_type == constants.BALL:
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
                radius_small=roller_r * 0.75,
                radius_large=roller_r * 1.15,
                depth=spec.roller_length,
                location=position,
                segments=max(12, segments // 2),
                collection=collection,
                tilt=tapered_tilt,
            )
            obj.rotation_euler[2] = a
        elif props.bearing_type == constants.SPHERICAL:
            obj = mesh_builders.add_barrel_roller(
                f"BarrelRoller_{i + 1:02d}",
                radius_mid=roller_r * 1.05,
                radius_end=roller_r * 0.80,
                length=spec.roller_length,
                location=position,
                segments=max(12, segments // 2),
                collection=collection,
            )
            obj.rotation_euler[2] = a
        else:
            raise ValueError(f"Unbekannter Lagertyp: {props.bearing_type}")

        elements.append(obj)

    return elements


def _build_cage(props, spec: ResolvedBearing, cage: CageDims, collection):
    """Erzeugt Käfig-Komponenten (zwei Endplatten + Webs) und gibt sie zurück."""
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
        # Web sitzt mittig zwischen Wälzkörper i und i+1.
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


def _build_bearing(props, spec: ResolvedBearing, collection):
    inner_ring = mesh_builders.make_hollow_ring(
        "InnerRing",
        props.bore_diameter,
        spec.inner_outer_d,
        props.width,
        props.segments,
        collection=collection,
    )
    outer_ring = mesh_builders.make_hollow_ring(
        "OuterRing",
        spec.outer_inner_d,
        props.outer_diameter,
        props.width,
        props.segments,
        collection=collection,
    )
    elements = _build_rolling_elements(props, spec, collection)

    assembly = bpy.data.objects.new("Bearing", None)
    collection.objects.link(assembly)
    assembly.empty_display_type = "PLAIN_AXES"

    parts = [inner_ring, outer_ring, *elements]

    cage_built = False
    if props.use_cage:
        cage = cage_dimensions(
            pitch_d=spec.pitch_d,
            roller_d=spec.roller_d,
            roller_length=spec.roller_length,
            width=props.width,
            element_count=spec.element_count,
            inner_race_d=spec.inner_outer_d,
            outer_race_d=spec.outer_inner_d,
        )
        if cage is not None:
            cage_parent = bpy.data.objects.new("Cage", None)
            collection.objects.link(cage_parent)
            cage_parent.empty_display_type = "PLAIN_AXES"
            cage_parent.parent = assembly
            for cage_part in _build_cage(props, spec, cage, collection):
                cage_part.parent = cage_parent
                parts.append(cage_part)
            cage_built = True

    for part in parts:
        if part.parent is None:
            part.parent = assembly

    non_manifold = sum(mesh_builders.count_non_manifold_edges(p.data) for p in parts)
    return assembly, non_manifold, cage_built


class UNI_OT_apply_series_preset(bpy.types.Operator):
    bl_idname = "uni_bearing.apply_series_preset"
    bl_label = "Norm-Preset anwenden"
    bl_description = "Überträgt die Maßwerte des ausgewählten Presets"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.uni_bearing
        preset = constants.SERIES_PRESETS.get(props.bearing_type, {}).get(props.series_code)
        if not preset:
            self.report({"WARNING"}, "Kein Preset für die aktuelle Auswahl hinterlegt.")
            return {"CANCELLED"}
        bore, outer, width = preset
        props.bore_diameter = bore
        props.outer_diameter = outer
        props.width = width

        # Ringstärke/Roller/Anzahl mitziehen, damit das Preset ohne weitere
        # Eingaben ein funktionierendes Lager liefert.
        suggestion = suggest_defaults(
            props.bearing_type,
            bore,
            outer,
            radial_clearance=props.radial_clearance,
            gap_factor=props.gap_factor,
        )
        props.ring_thickness = suggestion.ring_thickness
        props.roller_diameter = suggestion.roller_diameter
        props.element_count = suggestion.element_count
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
        assembly, non_manifold, cage_built = _build_bearing(props, spec, collection)

        assembly.scale = (MM_TO_M, MM_TO_M, MM_TO_M)
        assembly.location = cursor_location
        assembly["bearing_type"] = props.bearing_type
        assembly["norm_hint"] = constants.NORM_HINTS.get(props.bearing_type, "")
        assembly["precision_class"] = props.precision_class
        assembly["radial_clearance_mm"] = props.radial_clearance
        assembly["resolved_roller_d_mm"] = spec.roller_d
        assembly["resolved_element_count"] = spec.element_count
        assembly["resolved_pitch_d_mm"] = spec.pitch_d
        assembly["has_cage"] = cage_built
        if props.bearing_type == constants.TAPERED:
            assembly["contact_angle_deg"] = props.contact_angle_deg
            assembly["tapered_apex_z_mm"] = tapered_apex_z(
                spec.pitch_d, spec.roller_length, math.radians(props.contact_angle_deg)
            )

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
