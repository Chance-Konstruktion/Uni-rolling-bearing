"""Host-freier Bauplan eines Wälzlagers.

Dieser Modul übersetzt die :class:`~freecad_backend.params.BearingParams` in eine
rein geometrische Beschreibung – Querschnittsprofile der Ringe, Platzierungen der
Wälzkörper und Käfigteile – **ohne** ``bpy`` oder ``FreeCAD`` zu importieren.

Damit ist der gesamte „was wird wo gebaut"-Entscheidungsbaum (der in Blender in
``operators.py`` mit ``bpy`` verflochten ist) ohne laufenden Host testbar. Die
eigentliche Geometrie-Mathematik wird **nicht** dupliziert, sondern aus dem
geteilten Kern (``uni_rolling_bearing.geometry`` / ``.raceway``) aufgerufen.

Der dünne FreeCAD-Backend (``backend_freecad.py``) konsumiert nur diesen Plan und
baut daraus ``Part``-Solids. Genauso könnte ein Blender-Pfad den Plan nutzen.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple, Union

from uni_rolling_bearing import constants, raceway
from uni_rolling_bearing.geometry import (
    ResolvedBearing,
    cage_dimensions,
    oil_pocket_diameter,
    resolve_geometry,
    tapered_cone_half_angle,
)
from uni_rolling_bearing.tolerances import apply_tolerances

from .params import BearingParams

Profile = List[Tuple[float, float]]

# Pocket-Geometrie (identisch zu operators.py, damit beide Hosts gleich schneiden).
POCKET_AXIAL_OVERCUT_MM = 0.40
POCKET_RADIAL_CLEARANCE_MM = 0.20
# Profilpunkte entlang der Tonnenrollen-Längsachse (wie mesh_builders).
BARREL_PROFILE_RINGS = 9


@dataclass(frozen=True)
class Placement:
    """Starre Lage eines Wälzkörpers/Käfigteils.

    Rotation entspricht der Blender-Konvention ``Rz(rot_z) · Ry(tilt_y)`` (zuerst
    um die lokale Y-Achse kippen, dann um die Lagerachse Z drehen), gefolgt von
    einer Translation auf den Teilkreis.
    """

    translate: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rot_z: float = 0.0
    tilt_y: float = 0.0


@dataclass(frozen=True)
class RevolveRing:
    """Geschlossenes ``(r, z)``-Profil, das um die Z-Achse revolviert wird."""

    profile: Profile


@dataclass(frozen=True)
class Ball:
    radius: float
    placement: Placement


@dataclass(frozen=True)
class Roller:
    """Kegelstumpf/Zylinder (r1 an -L/2, r2 an +L/2), zentriert um den Ursprung."""

    radius1: float
    radius2: float
    height: float
    placement: Placement


@dataclass(frozen=True)
class Barrel:
    """Tonnenrolle (cos²-Profil), zentriert um den Ursprung."""

    radius_mid: float
    radius_end: float
    length: float
    placement: Placement


Solid = Union[RevolveRing, Ball, Roller, Barrel]


@dataclass(frozen=True)
class CagePart:
    """Ein additiver Käfigkörper plus die davon zu subtrahierenden Cutter."""

    additive: Solid
    cutters: Sequence[Solid] = field(default_factory=tuple)


@dataclass
class BearingPlan:
    inner_ring: Optional[RevolveRing] = None
    outer_ring: Optional[RevolveRing] = None
    elements: List[Solid] = field(default_factory=list)
    cage_parts: List[CagePart] = field(default_factory=list)
    cage_style: str = ""
    spec: Optional[ResolvedBearing] = None
    error: Optional[str] = None


# --------------------------------------------------------------------------- #
# Hilfsfunktionen (spiegeln operators.py, rufen aber denselben Kern)
# --------------------------------------------------------------------------- #


def _effective_dims(p: BearingParams):
    return apply_tolerances(
        bore_diameter_mm=p.bore_diameter,
        outer_diameter_mm=p.outer_diameter,
        width_mm=p.width,
        precision_class=p.precision_class,
        position=p.tolerance_position,
    )


def _resolve(p: BearingParams) -> Tuple[Optional[ResolvedBearing], Optional[str]]:
    eff = _effective_dims(p)
    spec, error = resolve_geometry(
        bearing_type=p.bearing_type,
        bore_diameter=eff.bore_diameter,
        outer_diameter=eff.outer_diameter,
        width=eff.width,
        ring_thickness=p.ring_thickness,
        roller_diameter=p.roller_diameter,
        element_count=p.element_count,
        radial_clearance=p.radial_clearance,
        gap_factor=p.gap_factor,
        auto_fit=p.auto_fit,
        conformity_inner=p.groove_conformity_inner,
        conformity_outer=p.groove_conformity_outer,
        contact_angle_deg=p.contact_angle_deg,
    )
    if (
        spec is not None
        and p.bearing_type == constants.SPHERICAL
        and p.spherical_row_count() == 2
    ):
        spec = dataclasses.replace(
            spec,
            roller_length=spec.roller_length * constants.SPHERICAL_TWO_ROW_LENGTH_FACTOR,
        )
    return spec, error


def _cone_half_angle(p: BearingParams, spec: ResolvedBearing) -> float:
    return tapered_cone_half_angle(
        spec.inner_outer_d, spec.outer_inner_d, math.radians(p.contact_angle_deg)
    )


def _tapered_tilt(p: BearingParams, spec: ResolvedBearing) -> float:
    return math.radians(p.contact_angle_deg) - _cone_half_angle(p, spec)


def _tapered_radii(p: BearingParams, spec: ResolvedBearing) -> Tuple[float, float]:
    beta = _cone_half_angle(p, spec)
    mean_r = spec.roller_d * 0.5
    delta = math.tan(beta) * spec.roller_length * 0.5
    return max(0.05, mean_r - delta), mean_r + delta


def _pocket_clearance(p: BearingParams) -> float:
    return float(p.pocket_clearance_mm)


# --------------------------------------------------------------------------- #
# Ring-Querschnittsprofile (delegiert an raceway.py)
# --------------------------------------------------------------------------- #


def _inner_ring_profile(p: BearingParams, spec: ResolvedBearing) -> Profile:
    bt = p.bearing_type
    eff = _effective_dims(p)
    if bt in (constants.BALL, constants.VGROOVE):
        return raceway.ball_inner_ring_profile(
            bore_d=eff.bore_diameter,
            shoulder_d=spec.inner_outer_d,
            width=eff.width,
            ball_d=spec.roller_d,
            pitch_d=spec.pitch_d,
            conformity=p.groove_conformity_inner,
            chamfer_mm=p.bearing_chamfer_mm,
        )
    if bt == constants.TAPERED:
        cone_w = float(p.tapered_cone_width_mm)
        inner_width = cone_w if cone_w > 0.0 else eff.width
        cone_angle = math.radians(p.contact_angle_deg) - 2.0 * _cone_half_angle(p, spec)
        flange_h = max(0.0, float(p.tapered_flange_height_mm))
        if flange_h > 0.0:
            half_w = inner_width * 0.5
            delta = math.tan(max(0.0, cone_angle)) * half_w
            r_plus = spec.inner_outer_d * 0.5 + delta
            max_flange = max(0.0, spec.outer_inner_d * 0.5 - r_plus - p.radial_clearance)
            flange_h = min(flange_h, max_flange)
        return raceway.tapered_inner_ring_profile(
            bore_d=eff.bore_diameter,
            shoulder_d=spec.inner_outer_d,
            width=inner_width,
            contact_angle_rad=cone_angle,
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
            contact_angle_rad=math.radians(p.spherical_contact_angle_deg),
            rows=p.spherical_row_count(),
        )
    return raceway.cylindrical_inner_ring_profile(
        bore_d=eff.bore_diameter,
        shoulder_d=spec.inner_outer_d,
        width=eff.width,
    )


def _outer_ring_profile(p: BearingParams, spec: ResolvedBearing) -> Profile:
    bt = p.bearing_type
    eff = _effective_dims(p)
    if bt == constants.BALL:
        return raceway.ball_outer_ring_profile(
            shoulder_d=spec.outer_inner_d,
            outer_d=eff.outer_diameter,
            width=eff.width,
            ball_d=spec.roller_d,
            pitch_d=spec.pitch_d,
            conformity=p.groove_conformity_outer,
            chamfer_mm=p.bearing_chamfer_mm,
        )
    if bt == constants.VGROOVE:
        depth = p.vgroove_depth_mm if p.vgroove_depth_mm > 0.0 else None
        return raceway.vgroove_outer_ring_profile(
            shoulder_d=spec.outer_inner_d,
            outer_d=eff.outer_diameter,
            width=eff.width,
            ball_d=spec.roller_d,
            pitch_d=spec.pitch_d,
            groove_depth=depth,
            groove_half_angle_rad=math.radians(p.vgroove_half_angle_deg),
            conformity=p.groove_conformity_outer,
            chamfer_mm=p.bearing_chamfer_mm,
            groove_shape=p.vgroove_shape,
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
        cup_w = float(p.tapered_cup_width_mm)
        outer_width = cup_w if cup_w > 0.0 else eff.width
        return raceway.tapered_outer_ring_profile(
            shoulder_d=spec.outer_inner_d,
            outer_d=eff.outer_diameter,
            width=outer_width,
            contact_angle_rad=math.radians(p.contact_angle_deg),
        )
    if bt == constants.SPHERICAL:
        return raceway.spherical_outer_ring_profile(
            shoulder_d=spec.outer_inner_d,
            outer_d=eff.outer_diameter,
            width=eff.width,
            pitch_d=spec.pitch_d,
            roller_d=spec.roller_d,
        )
    return raceway.cylindrical_outer_ring_profile(
        shoulder_d=spec.outer_inner_d,
        outer_d=eff.outer_diameter,
        width=eff.width,
        roller_length=spec.roller_length,
        roller_d=spec.roller_d,
    )


# --------------------------------------------------------------------------- #
# Wälzkörper
# --------------------------------------------------------------------------- #


def _rolling_elements(p: BearingParams, spec: ResolvedBearing) -> List[Solid]:
    elements: List[Solid] = []
    ring_r = spec.pitch_d * 0.5
    roller_r = spec.roller_d * 0.5
    bt = p.bearing_type

    if bt == constants.TAPERED:
        r_small, r_large = _tapered_radii(p, spec)
        tilt = _tapered_tilt(p, spec)

    for i in range(spec.element_count):
        a = 2.0 * math.pi * i / spec.element_count
        pos = (ring_r * math.cos(a), ring_r * math.sin(a), 0.0)

        if bt in (constants.BALL, constants.VGROOVE):
            elements.append(Ball(roller_r, Placement(pos)))
        elif bt in (constants.CYLINDRICAL, constants.NEEDLE):
            elements.append(
                Roller(roller_r, roller_r, spec.roller_length, Placement(pos, rot_z=a))
            )
        elif bt == constants.TAPERED:
            elements.append(
                Roller(r_small, r_large, spec.roller_length, Placement(pos, rot_z=a, tilt_y=tilt))
            )
        elif bt == constants.SPHERICAL:
            if p.spherical_row_count() == 1:
                elements.append(
                    Barrel(roller_r, roller_r * 0.78, spec.roller_length, Placement(pos, rot_z=a))
                )
            else:
                alpha = math.radians(p.spherical_contact_angle_deg)
                row_z = raceway.spherical_inner_row_z(
                    _effective_dims(p).width, spec.roller_length, alpha
                )
                for sign in (-1, +1):
                    elements.append(
                        Barrel(
                            roller_r,
                            roller_r * 0.78,
                            spec.roller_length,
                            Placement((pos[0], pos[1], sign * row_z), rot_z=a, tilt_y=-sign * alpha),
                        )
                    )
        else:
            raise ValueError(f"Unbekannter Lagertyp: {bt}")

    return elements


def _pocket_cutter(p: BearingParams, spec: ResolvedBearing, pos, angle) -> Optional[Solid]:
    bt = p.bearing_type
    roller_r = spec.roller_d * 0.5
    clr = _pocket_clearance(p)
    overcut = 2.0 * POCKET_AXIAL_OVERCUT_MM

    if bt in (constants.BALL, constants.VGROOVE):
        return Ball(roller_r + clr, Placement(pos))
    if bt in (constants.CYLINDRICAL, constants.NEEDLE):
        return Roller(
            roller_r + clr, roller_r + clr, spec.roller_length + overcut, Placement(pos, rot_z=angle)
        )
    if bt == constants.TAPERED:
        r_small, r_large = _tapered_radii(p, spec)
        tilt = _tapered_tilt(p, spec)
        return Roller(
            r_small + clr, r_large + clr, spec.roller_length + overcut, Placement(pos, rot_z=angle, tilt_y=tilt)
        )
    if bt == constants.SPHERICAL:
        return Barrel(
            roller_r + clr, roller_r * 0.78 + clr, spec.roller_length + overcut, Placement(pos, rot_z=angle)
        )
    return None


# --------------------------------------------------------------------------- #
# Käfig
# --------------------------------------------------------------------------- #


def _ring_profile(inner_d: float, outer_d: float, width: float) -> Profile:
    inner_r, outer_r, hw = inner_d * 0.5, outer_d * 0.5, width * 0.5
    return [(outer_r, -hw), (outer_r, hw), (inner_r, hw), (inner_r, -hw)]


def _cage_parts(p: BearingParams, spec: ResolvedBearing, cage) -> Tuple[List[CagePart], str]:
    sleeve_width = 2.0 * cage.plate_z_offset + cage.plate_thickness
    pitch_r = spec.pitch_d * 0.5

    def _all_cutters() -> List[Solid]:
        cutters: List[Solid] = []
        for i in range(spec.element_count):
            a = 2.0 * math.pi * i / spec.element_count
            pos = (pitch_r * math.cos(a), pitch_r * math.sin(a), 0.0)
            cutter = _pocket_cutter(p, spec, pos, a)
            if cutter is not None:
                cutters.append(cutter)
        return cutters

    style = p.cage_style

    # Leiter-Käfig: zwei Endplatten + tangentiale Webs (keine Booleans).
    if style == "LADDER":
        parts: List[CagePart] = []
        for sign in (+1, -1):
            ring = RevolveRing(_ring_profile(cage.plate_inner_d, cage.plate_outer_d, cage.plate_thickness))
            # Platten-z-Versatz über eine eigene Revolve mit verschobenem Profil.
            shifted = RevolveRing([(r, z + sign * cage.plate_z_offset) for r, z in ring.profile])
            parts.append(CagePart(shifted))
        ang = 2.0 * math.pi / spec.element_count
        for i in range(spec.element_count):
            theta = (i + 0.5) * ang
            loc = (cage.web_pitch_r * math.cos(theta), cage.web_pitch_r * math.sin(theta), 0.0)
            box = Box(cage.web_radial_size, cage.web_tangential_size, cage.web_axial_length,
                      Placement(loc, rot_z=theta))
            parts.append(CagePart(box))
        return parts, "ladder"

    # Ribbon-Käfig: zwei genietete Halbringe mit halbschaligen Pockets.
    if style == "RIBBON" and sleeve_width > 0.5:
        half_width = sleeve_width * 0.5
        half_offset = half_width * 0.5
        parts = []
        for sign in (+1, -1):
            prof = [(r, z + sign * half_offset)
                    for r, z in _ring_profile(cage.plate_inner_d, cage.plate_outer_d, half_width)]
            parts.append(CagePart(RevolveRing(prof), tuple(_all_cutters())))
        rivet_r = max(0.25, cage.web_radial_size * 0.25)
        ang = 2.0 * math.pi / spec.element_count
        for i in range(spec.element_count):
            theta = (i + 0.5) * ang
            loc = (cage.web_pitch_r * math.cos(theta), cage.web_pitch_r * math.sin(theta), 0.0)
            parts.append(CagePart(Roller(rivet_r, rivet_r, sleeve_width, Placement(loc))))
        return parts, "ribbon"

    # Massivkäfig: Pocket-Sleeve plus radiale Schmiertaschen.
    if style == "MASSIVE" and sleeve_width > 0.5:
        cutters = _all_cutters()
        oil_d = oil_pocket_diameter(
            requested_mm=float(p.oil_pocket_diameter_mm),
            sleeve_axial_extent_mm=sleeve_width,
            web_tangential_size_mm=cage.web_tangential_size,
            edge_clearance_mm=_pocket_clearance(p),
        )
        if oil_d > 0.0:
            radial_span = cage.plate_outer_d - cage.plate_inner_d
            length = radial_span + 4.0 * POCKET_AXIAL_OVERCUT_MM
            ang = 2.0 * math.pi / spec.element_count
            for i in range(spec.element_count):
                theta = (i + 0.5) * ang
                loc = (cage.web_pitch_r * math.cos(theta), cage.web_pitch_r * math.sin(theta), 0.0)
                # Achse radial nach außen: erst um Y um 90° kippen, dann um Z drehen.
                cutters.append(
                    Roller(oil_d * 0.5, oil_d * 0.5, length, Placement(loc, rot_z=theta, tilt_y=math.pi * 0.5))
                )
        sleeve = RevolveRing(_ring_profile(cage.plate_inner_d, cage.plate_outer_d, sleeve_width))
        return [CagePart(sleeve, tuple(cutters))], "massive"

    # Standard (AUTO/POCKET): einteiliger Sleeve mit typabhängigen Pockets.
    if sleeve_width > 0.5:
        sleeve = RevolveRing(_ring_profile(cage.plate_inner_d, cage.plate_outer_d, sleeve_width))
        return [CagePart(sleeve, tuple(_all_cutters()))], "pocket"

    return [], ""


# --------------------------------------------------------------------------- #
# Öffentliche API
# --------------------------------------------------------------------------- #


def build_plan(p: BearingParams) -> BearingPlan:
    """Erzeugt den vollständigen, host-freien Bauplan für ``p``.

    Bei unlösbarer Geometrie wird ``BearingPlan(error=...)`` zurückgegeben.
    """
    spec, error = _resolve(p)
    if spec is None:
        return BearingPlan(error=error or "Geometrie konnte nicht aufgelöst werden.")

    plan = BearingPlan(
        inner_ring=RevolveRing(_inner_ring_profile(p, spec)),
        outer_ring=RevolveRing(_outer_ring_profile(p, spec)),
        elements=_rolling_elements(p, spec),
        spec=spec,
    )

    if p.use_cage:
        eff = _effective_dims(p)
        cage = cage_dimensions(
            pitch_d=spec.pitch_d,
            roller_d=spec.roller_d,
            roller_length=spec.roller_length,
            width=eff.width,
            element_count=spec.element_count,
            inner_race_d=spec.inner_outer_d,
            outer_race_d=spec.outer_inner_d,
        )
        if cage is not None:
            plan.cage_parts, plan.cage_style = _cage_parts(p, spec, cage)

    return plan


@dataclass(frozen=True)
class Box:
    """Achsausgerichteter Quader (Leiter-Käfig-Web)."""

    sx: float
    sy: float
    sz: float
    placement: Placement


__all__ = [
    "BearingPlan",
    "Placement",
    "RevolveRing",
    "Ball",
    "Roller",
    "Barrel",
    "Box",
    "CagePart",
    "build_plan",
    "BARREL_PROFILE_RINGS",
]
