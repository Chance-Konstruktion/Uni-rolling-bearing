"""Laufbahn-Profile (Cross-Sections) für Innen- und Außenringe.

Jede Funktion liefert eine geschlossene 2D-Polygonlinie in der ``(r, z)``-Ebene
zurück, die anschließend um die Z-Achse zu einem manifold Ring revolviert
wird. Reine Berechnung – keine Blender-Abhängigkeit, daher direkt testbar.

Konventionen:

* ``r >= 0``, ``z`` symmetrisch um 0 (Lager-Mittelebene).
* Punktreihenfolge ist gleichgerichtet (i. d. R. gegen den Uhrzeigersinn in der
  ``(r, z)``-Ebene), aufeinanderfolgende identische Punkte werden entfernt.
* Der erste und letzte Punkt sind nicht identisch; das Schließen übernimmt der
  Mesh-Builder beim Revolvieren.
"""

from __future__ import annotations

import math
from typing import List, Tuple

# Numerische Toleranz, unter der zwei Profil-Punkte als gleich gelten.
PROFILE_EPSILON = 1.0e-6

# Default-Konformitätsfaktoren f = r_groove / d_ball für Rillenkugellager.
# Real bewegen sich Innen- und Außenring zwischen 0.515 und 0.535 (Eschmann/
# Hasbargen/Weigand "Die Wälzlagerpraxis"). Hier liegen die Werte etwas höher,
# damit die Rille auch bei nicht-perfekt befülltem Spalt sichtbar ins Material
# schneidet (Visualisierungsoptimum vs. Tragmechanik). Der Außenring hat traditionell
# die etwas größere Konformität.
BALL_GROOVE_CONFORMITY_INNER = 0.58
BALL_GROOVE_CONFORMITY_OUTER = 0.60

# Maximaler axialer Halbweite-Anteil der Rille relativ zur Lagerbreite und
# zum Wälzkörper-Ø. Verhindert, dass die Rille die Stirnflächen erreicht.
BALL_GROOVE_MAX_Z_FRACTION_OF_WIDTH = 0.45
BALL_GROOVE_MAX_Z_FRACTION_OF_BALL = 0.55

# Schulterhöhe (Bord) auf Zylinder-/Nadelrollen-Außenringen, ausgedrückt als
# Anteil des Roller-Ø.
CYL_SHOULDER_HEIGHT_FRACTION = 0.20
# Mindest-Bord-Höhe in mm, damit die Schulter visuell sichtbar bleibt.
CYL_SHOULDER_MIN_MM = 0.3
# Axiale Verlängerung der Schulter über die Rollenenden hinaus, relativ
# zur halben Lagerbreite.
CYL_SHOULDER_AXIAL_FRACTION = 0.5
# Axialspiel zwischen Rollenstirn und Bord-Innenfläche (Lauf-Spielraum).
CYL_BORD_AXIAL_CLEARANCE_MM = 0.1

# Rillen-/Schulter-Geometrie für Tonnenlager.
SPHERICAL_OUTER_RACE_FACTOR = 1.04  # Sphäre-Radius = factor · pitch_r
SPHERICAL_RACE_MIN_DEPTH_MM = 0.1


Profile = List[Tuple[float, float]]


# ---------------------------------------------------------------------------
# Hilfen
# ---------------------------------------------------------------------------


def _dedupe_profile(points: Profile) -> Profile:
    """Entfernt aufeinanderfolgende Duplikate und schließt nicht implizit."""
    out: Profile = []
    for p in points:
        if not out:
            out.append(p)
            continue
        dr = abs(p[0] - out[-1][0])
        dz = abs(p[1] - out[-1][1])
        if dr > PROFILE_EPSILON or dz > PROFILE_EPSILON:
            out.append(p)
    # Doppelten Schließpunkt entfernen, falls vorhanden.
    while len(out) > 2:
        dr = abs(out[-1][0] - out[0][0])
        dz = abs(out[-1][1] - out[0][1])
        if dr <= PROFILE_EPSILON and dz <= PROFILE_EPSILON:
            out.pop()
        else:
            break
    return out


def _hollow_cylinder_profile(
    inner_d: float,
    outer_d: float,
    width: float,
) -> Profile:
    """Rechteckiger Querschnitt eines einfachen Hohlzylinder-Rings."""
    inner_r = inner_d * 0.5
    outer_r = outer_d * 0.5
    half_w = width * 0.5
    return [
        (inner_r, -half_w),
        (outer_r, -half_w),
        (outer_r, half_w),
        (inner_r, half_w),
    ]


# ---------------------------------------------------------------------------
# Rillenkugellager
# ---------------------------------------------------------------------------


def _ball_groove_z_arc(
    *,
    radial_gap: float,
    groove_r: float,
    ball_d: float,
    width: float,
) -> float:
    """Axiale Halb-Spanne, über die die Rillenkurve den Lagerquerschnitt schneidet.

    ``radial_gap`` = ``pitch_r - shoulder_r`` (für Innen- oder Außenring; immer
    positiv). Liefert ``0.0``, wenn die Rille die Schulter nicht erreichen
    würde – in dem Fall ist kein materiell ausgeprägter Rillenschnitt möglich.
    """
    if groove_r <= radial_gap + PROFILE_EPSILON:
        return 0.0
    z_meet = math.sqrt(groove_r * groove_r - radial_gap * radial_gap)
    z_max = min(
        BALL_GROOVE_MAX_Z_FRACTION_OF_WIDTH * width,
        BALL_GROOVE_MAX_Z_FRACTION_OF_BALL * ball_d,
        groove_r * 0.95,
    )
    return max(0.0, min(z_meet, z_max))


def _arc_points_inner(pitch_r: float, groove_r: float, z_arc: float, segments: int) -> Profile:
    """Punkte des Innenring-Rillenbogens (kleinerer ``r`` als ``pitch_r``)."""
    n = max(4, segments)
    pts: Profile = []
    for i in range(n + 1):
        t = i / n
        z = -z_arc + 2.0 * z_arc * t
        d = math.sqrt(max(0.0, groove_r * groove_r - z * z))
        pts.append((pitch_r - d, z))
    return pts


def _arc_points_outer(pitch_r: float, groove_r: float, z_arc: float, segments: int) -> Profile:
    """Punkte des Außenring-Rillenbogens (größerer ``r`` als ``pitch_r``)."""
    n = max(4, segments)
    pts: Profile = []
    for i in range(n + 1):
        t = i / n
        z = -z_arc + 2.0 * z_arc * t
        d = math.sqrt(max(0.0, groove_r * groove_r - z * z))
        pts.append((pitch_r + d, z))
    return pts


def ball_inner_ring_profile(
    *,
    bore_d: float,
    shoulder_d: float,
    width: float,
    ball_d: float,
    pitch_d: float,
    conformity: float = BALL_GROOVE_CONFORMITY_INNER,
    arc_segments: int = 24,
) -> Profile:
    """Querschnitt des Innenrings eines Rillenkugellagers.

    ``shoulder_d`` ist der Außen-Ø des Innenrings (Schulterhöhe). Reicht der
    Rillenbogen geometrisch nicht bis zur Schulter, wird ein einfacher
    Hohlzylinder zurückgegeben (Fallback ohne ausgeprägte Rille).
    """
    bore_r = bore_d * 0.5
    shoulder_r = shoulder_d * 0.5
    pitch_r = pitch_d * 0.5
    half_w = width * 0.5
    groove_r = conformity * ball_d
    radial_gap = pitch_r - shoulder_r

    if radial_gap <= PROFILE_EPSILON:
        return _dedupe_profile(_hollow_cylinder_profile(bore_d, shoulder_d, width))

    z_arc = _ball_groove_z_arc(
        radial_gap=radial_gap, groove_r=groove_r, ball_d=ball_d, width=width
    )
    if z_arc <= PROFILE_EPSILON:
        return _dedupe_profile(_hollow_cylinder_profile(bore_d, shoulder_d, width))

    arc = _arc_points_inner(pitch_r, groove_r, z_arc, arc_segments)
    profile: Profile = [
        (bore_r, -half_w),
        (shoulder_r, -half_w),
        (shoulder_r, -z_arc),
    ]
    profile.extend(arc)
    profile.extend([
        (shoulder_r, z_arc),
        (shoulder_r, half_w),
        (bore_r, half_w),
    ])
    return _dedupe_profile(profile)


def ball_outer_ring_profile(
    *,
    shoulder_d: float,
    outer_d: float,
    width: float,
    ball_d: float,
    pitch_d: float,
    conformity: float = BALL_GROOVE_CONFORMITY_OUTER,
    arc_segments: int = 24,
) -> Profile:
    """Querschnitt des Außenrings eines Rillenkugellagers."""
    outer_r = outer_d * 0.5
    shoulder_r = shoulder_d * 0.5
    pitch_r = pitch_d * 0.5
    half_w = width * 0.5
    groove_r = conformity * ball_d
    radial_gap = shoulder_r - pitch_r

    if radial_gap <= PROFILE_EPSILON:
        return _dedupe_profile(_hollow_cylinder_profile(shoulder_d, outer_d, width))

    z_arc = _ball_groove_z_arc(
        radial_gap=radial_gap, groove_r=groove_r, ball_d=ball_d, width=width
    )
    if z_arc <= PROFILE_EPSILON:
        return _dedupe_profile(_hollow_cylinder_profile(shoulder_d, outer_d, width))

    arc = _arc_points_outer(pitch_r, groove_r, z_arc, arc_segments)
    # Im Profil traversieren wir den Außenring so, dass die Innenfläche
    # (Rillen-Seite) im positiven z-Halbraum eingegangen und im negativen
    # wieder verlassen wird; dazu wird der Bogen umgekehrt eingefügt.
    profile: Profile = [
        (shoulder_r, -half_w),
        (outer_r, -half_w),
        (outer_r, half_w),
        (shoulder_r, half_w),
        (shoulder_r, z_arc),
    ]
    profile.extend(reversed(arc))
    profile.append((shoulder_r, -z_arc))
    return _dedupe_profile(profile)


# ---------------------------------------------------------------------------
# Zylinder-/Nadelrollenlager
# ---------------------------------------------------------------------------


def _shoulder_height(roller_d: float, max_height: float) -> float:
    target = max(CYL_SHOULDER_MIN_MM, roller_d * CYL_SHOULDER_HEIGHT_FRACTION)
    return max(0.0, min(target, max_height))


def cylindrical_inner_ring_profile(
    *,
    bore_d: float,
    shoulder_d: float,
    width: float,
) -> Profile:
    """Innenring zylindrischer Rollenlager (NU-Bauart): einfacher Hohlzylinder."""
    return _dedupe_profile(_hollow_cylinder_profile(bore_d, shoulder_d, width))


def cylindrical_outer_ring_profile(
    *,
    shoulder_d: float,
    outer_d: float,
    width: float,
    roller_length: float,
    roller_d: float,
) -> Profile:
    """Außenring mit zwei Borden (NU-Bauart).

    Die Borde stehen radial nach innen vor und halten die Rollen axial. Wenn
    Bauraum oder Rollenlänge die Bordhöhe rechnerisch wegfressen, fällt die
    Funktion auf einen einfachen Hohlzylinder zurück.
    """
    outer_r = outer_d * 0.5
    shoulder_r = shoulder_d * 0.5
    half_w = width * 0.5
    half_roller = roller_length * 0.5

    # Maximale Bordhöhe = halber Spalt; sonst würde der Bord die Lagerachse
    # erreichen oder unter dem Mindestmaß verschwinden.
    max_height = max(0.0, shoulder_r - PROFILE_EPSILON)
    height = _shoulder_height(roller_d, max_height)
    if height <= PROFILE_EPSILON:
        return _dedupe_profile(_hollow_cylinder_profile(shoulder_d, outer_d, width))

    # Axiale Position der Bord-Innenkante – knapp neben dem Rollenende.
    bord_z_min = half_roller + CYL_BORD_AXIAL_CLEARANCE_MM
    bord_z_target = max(bord_z_min, half_w * (1.0 - CYL_SHOULDER_AXIAL_FRACTION))
    if bord_z_target >= half_w - PROFILE_EPSILON:
        # Rollen füllen die Breite quasi voll – kein Platz für einen Bord.
        return _dedupe_profile(_hollow_cylinder_profile(shoulder_d, outer_d, width))
    bord_z = bord_z_target

    bord_inner_r = shoulder_r - height

    profile: Profile = [
        (bord_inner_r, -half_w),
        (outer_r, -half_w),
        (outer_r, half_w),
        (bord_inner_r, half_w),
        (bord_inner_r, bord_z),
        (shoulder_r, bord_z),
        (shoulder_r, -bord_z),
        (bord_inner_r, -bord_z),
    ]
    return _dedupe_profile(profile)


# ---------------------------------------------------------------------------
# Kegelrollenlager
# ---------------------------------------------------------------------------


def tapered_inner_ring_profile(
    *,
    bore_d: float,
    shoulder_d: float,
    width: float,
    contact_angle_rad: float,
) -> Profile:
    """Innenring (Kegel) eines Kegelrollenlagers.

    Die Außenfläche tapert: am +z-Ende größer, am -z-Ende kleiner, passend zum
    typischen Aufstellsinn von Kegelrollenlagern (kleine Stirn der Rolle nach
    -z). ``contact_angle_rad`` ist der Kontaktwinkel α; die Flanke der
    Innenlaufbahn wird mit α gegen die Lagerachse geneigt.
    """
    bore_r = bore_d * 0.5
    shoulder_r = shoulder_d * 0.5
    half_w = width * 0.5

    # Halbe radiale Verschiebung der Konusenden gegenüber dem Mittenradius.
    delta = math.tan(max(0.0, contact_angle_rad)) * half_w
    r_minus = max(bore_r + PROFILE_EPSILON, shoulder_r - delta)
    r_plus = shoulder_r + delta

    profile: Profile = [
        (bore_r, -half_w),
        (r_minus, -half_w),
        (r_plus, half_w),
        (bore_r, half_w),
    ]
    return _dedupe_profile(profile)


def tapered_outer_ring_profile(
    *,
    shoulder_d: float,
    outer_d: float,
    width: float,
    contact_angle_rad: float,
) -> Profile:
    """Außenring (Cup) eines Kegelrollenlagers."""
    outer_r = outer_d * 0.5
    shoulder_r = shoulder_d * 0.5
    half_w = width * 0.5

    delta = math.tan(max(0.0, contact_angle_rad)) * half_w
    r_minus = max(PROFILE_EPSILON, shoulder_r - delta)
    r_plus = min(outer_r - PROFILE_EPSILON, shoulder_r + delta)

    profile: Profile = [
        (r_minus, -half_w),
        (outer_r, -half_w),
        (outer_r, half_w),
        (r_plus, half_w),
    ]
    return _dedupe_profile(profile)


# ---------------------------------------------------------------------------
# Tonnenlager / Pendelrollenlager
# ---------------------------------------------------------------------------


def spherical_outer_ring_profile(
    *,
    shoulder_d: float,
    outer_d: float,
    width: float,
    pitch_d: float,
    roller_d: float,
    arc_segments: int = 24,
) -> Profile:
    """Außenring mit sphärischer Innenlaufbahn (Pendelrollen-/Tonnenlager).

    Die Sphäre ist auf der Lagerachse zentriert; ihr Radius wird so gewählt,
    dass er dem Pitch-Radius plus dem mittleren Tonnen-Radius entspricht und
    die Schulterhöhe an den Stirnflächen nicht unterschreitet.
    """
    outer_r = outer_d * 0.5
    shoulder_r = shoulder_d * 0.5
    pitch_r = pitch_d * 0.5
    half_w = width * 0.5

    # Sphäre-Radius mindestens so groß, dass die Innenfläche an den Stirn-
    # flächen am Schulterradius (oder darüber) sitzt; sonst würde das Profil
    # an den Stirnseiten unter die Schulter tauchen.
    min_R = math.sqrt(shoulder_r * shoulder_r + half_w * half_w) + SPHERICAL_RACE_MIN_DEPTH_MM
    target_R = max(min_R, pitch_r + roller_d * 0.5)
    R = target_R

    n = max(4, arc_segments)
    arc: Profile = []
    for i in range(n + 1):
        t = i / n
        z = -half_w + 2.0 * half_w * t
        r = math.sqrt(max(0.0, R * R - z * z))
        # Sicherstellen, dass die Innenfläche nicht über die Stirnschulter
        # hinaus nach innen sticht.
        r = min(r, outer_r - PROFILE_EPSILON)
        arc.append((r, z))

    # Profil: Außenmantel von -half_w nach +half_w, dann Stirnfläche oben,
    # sphärische Innenfläche von +half_w nach -half_w (umgekehrt), Stirnfläche
    # unten zurück zum Start.
    profile: Profile = [
        (arc[0][0], -half_w),
        (outer_r, -half_w),
        (outer_r, half_w),
        (arc[-1][0], half_w),
    ]
    profile.extend(reversed(arc))
    return _dedupe_profile(profile)


__all__ = [
    "BALL_GROOVE_CONFORMITY_INNER",
    "BALL_GROOVE_CONFORMITY_OUTER",
    "ball_inner_ring_profile",
    "ball_outer_ring_profile",
    "cylindrical_inner_ring_profile",
    "cylindrical_outer_ring_profile",
    "spherical_outer_ring_profile",
    "tapered_inner_ring_profile",
    "tapered_outer_ring_profile",
]
