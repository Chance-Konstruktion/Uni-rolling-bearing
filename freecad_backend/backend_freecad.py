"""FreeCAD/Part-Backend: baut aus einem :class:`~freecad_backend.plan.BearingPlan`
echte BREP-Solids.

Dies ist das **dünne** Frontend im Sinne des „geteilter Kern, zwei Hosts"-Prinzips.
Alle Entscheidungen (Maße, Platzierungen, Profile) stammen aus dem host-freien
``plan``-Modul; hier wird ausschließlich ``Part`` bedient.

Wichtig (Blocker 6 aus der Skill-Erfahrung): Rotationskörper werden aus **geraden
Polygon-Meridianen** revolviert – niemals aus interpolierten BSplines. So trifft
der FreeCAD-Körper exakt dieselben Nennmaße wie der Blender-Mesh; gerade Schultern
bleiben gerade, Rillenradien werden über die Punktdichte des Kerns aufgelöst.

``Part``/``FreeCAD`` werden bewusst erst **innerhalb** der Funktionen importiert,
damit dieses Modul ohne laufendes FreeCAD importier- und (mit gemocktem ``Part``)
testbar bleibt.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

from .plan import (
    BARREL_PROFILE_RINGS,
    Ball,
    Barrel,
    BearingPlan,
    Box,
    CagePart,
    Placement,
    RevolveRing,
    Roller,
    Solid,
    build_plan,
)
from .params import BearingParams


@dataclass
class BuildResult:
    """Benannte Solids eines gebauten Lagers (jeweils ``Part.Shape``)."""

    inner_ring: object = None
    outer_ring: object = None
    elements: List[object] = field(default_factory=list)
    cage: List[object] = field(default_factory=list)

    def all_shapes(self) -> List[object]:
        shapes = []
        if self.inner_ring is not None:
            shapes.append(self.inner_ring)
        if self.outer_ring is not None:
            shapes.append(self.outer_ring)
        shapes.extend(self.elements)
        shapes.extend(self.cage)
        return shapes

    def compound(self):
        import Part  # lazy – nur in echtem FreeCAD verfügbar

        return Part.makeCompound(self.all_shapes())


def _barrel_meridian(radius_mid: float, radius_end: float, length: float,
                     rings: int = BARREL_PROFILE_RINGS) -> List[Tuple[float, float]]:
    """Geschlossener ``(r, z)``-Meridian einer Tonnenrolle (cos²-Profil).

    Identisch zur Blender-Variante (``mesh_builders.add_barrel_roller``), aber als
    revolvierbarer Meridian inkl. der beiden Achsenpunkte (r=0) für saubere Deckel.
    """
    rings_n = max(3, rings)
    pts: List[Tuple[float, float]] = [(0.0, -length * 0.5)]
    for i in range(rings_n):
        t = i / (rings_n - 1)
        u = 2.0 * t - 1.0
        z = -length * 0.5 + t * length
        r = radius_end + (radius_mid - radius_end) * math.cos(0.5 * math.pi * u) ** 2
        pts.append((r, z))
    pts.append((0.0, length * 0.5))
    return pts


def _placement(pl: Placement, pre_translate: Tuple[float, float, float] = (0.0, 0.0, 0.0)):
    """FreeCAD-``Placement`` für ``Rz(rot_z) · Ry(tilt_y) · T(pre_translate)``.

    ``pre_translate`` zentriert Formen, die ``Part`` an ``z=0`` beginnend baut
    (z. B. ``makeCone``), bevor Kippung und Drehung greifen.
    """
    import FreeCAD as App

    Vector = App.Vector
    Rotation = App.Rotation
    P = App.Placement

    rot = Rotation(Vector(0, 0, 1), math.degrees(pl.rot_z)).multiply(
        Rotation(Vector(0, 1, 0), math.degrees(pl.tilt_y))
    )
    pre = P(Vector(*pre_translate), Rotation())
    mid = P(Vector(0, 0, 0), rot)
    post = P(Vector(*pl.translate), Rotation())
    return post.multiply(mid).multiply(pre)


def _revolve_profile(profile: Sequence[Tuple[float, float]]):
    """Revolviert ein geschlossenes ``(r, z)``-Polygon 360° um die Z-Achse."""
    import FreeCAD as App
    import Part

    Vector = App.Vector
    pts = [Vector(r, 0.0, z) for r, z in profile]
    pts.append(pts[0])  # Kontur schließen – gerade Kanten, keine BSpline
    wire = Part.makePolygon(pts)
    face = Part.Face(wire)
    return face.revolve(Vector(0, 0, 0), Vector(0, 0, 1), 360.0)


def _make_solid(solid: Solid):
    """Baut ein einzelnes :mod:`plan`-Primitive als ``Part.Shape``."""
    import Part

    if isinstance(solid, RevolveRing):
        return _revolve_profile(solid.profile)

    if isinstance(solid, Ball):
        shape = Part.makeSphere(solid.radius)
        shape.Placement = _placement(solid.placement)
        return shape

    if isinstance(solid, Roller):
        # makeCone baut von z=0 (r1) bis z=h (r2); um den Ursprung zentrieren.
        shape = Part.makeCone(solid.radius1, solid.radius2, solid.height)
        shape.Placement = _placement(solid.placement, pre_translate=(0.0, 0.0, -solid.height * 0.5))
        return shape

    if isinstance(solid, Barrel):
        shape = _revolve_profile(_barrel_meridian(solid.radius_mid, solid.radius_end, solid.length))
        shape.Placement = _placement(solid.placement)
        return shape

    if isinstance(solid, Box):
        import FreeCAD as App

        shape = Part.makeBox(solid.sx, solid.sy, solid.sz,
                             App.Vector(-solid.sx * 0.5, -solid.sy * 0.5, -solid.sz * 0.5))
        shape.Placement = _placement(solid.placement)
        return shape

    raise TypeError(f"Unbekanntes Solid: {type(solid)!r}")


def _build_cage_part(part: CagePart):
    """Baut einen Käfigkörper und subtrahiert seine Pocket-Cutter (Boolean)."""
    shape = _make_solid(part.additive)
    for cutter in part.cutters:
        cut_shape = _make_solid(cutter)
        try:
            shape = shape.cut(cut_shape)
        except Exception:  # pragma: no cover – einzelner Boolean darf scheitern
            continue
    return shape


def build_from_plan(plan: BearingPlan) -> BuildResult:
    """Baut alle Solids eines bereits aufgelösten Plans."""
    if plan.error is not None or plan.spec is None:
        raise ValueError(plan.error or "Ungültiger Bauplan.")

    result = BuildResult()
    if plan.inner_ring is not None:
        result.inner_ring = _make_solid(plan.inner_ring)
    if plan.outer_ring is not None:
        result.outer_ring = _make_solid(plan.outer_ring)
    result.elements = [_make_solid(e) for e in plan.elements]
    result.cage = [_build_cage_part(c) for c in plan.cage_parts]
    return result


def build_bearing(params: BearingParams) -> BuildResult:
    """Komfort-Einstieg: löst die Geometrie auf und baut die Solids.

    Wirft ``ValueError`` mit der Resolver-Meldung, wenn die Maße unlösbar sind.
    """
    return build_from_plan(build_plan(params))


__all__ = ["BuildResult", "build_from_plan", "build_bearing"]
