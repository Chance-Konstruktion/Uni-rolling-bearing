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

# Sicherheitsanteil des verfügbaren Bauraums, den eine Fase maximal einnehmen
# darf (axial wie radial). 0.45 lässt mindestens 10 % Material zwischen
# gegenüberliegenden Fasen bzw. zwischen Fase und Laufbahn stehen.
CHAMFER_MAX_FRACTION = 0.45

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


def _clamp_chamfer(chamfer: float, *limits: float) -> float:
    """Begrenzt eine Fase auf den verfügbaren Bauraum.

    ``limits`` sind die freien Abstände (axial wie radial) an der Fase. Die
    zurückgegebene Fase liegt zwischen 0 und ``CHAMFER_MAX_FRACTION`` × dem
    kleinsten Limit. Negative Eingaben werden auf 0 gekürzt.
    """
    c = max(0.0, float(chamfer))
    if c <= PROFILE_EPSILON:
        return 0.0
    headroom = min(limits) if limits else 0.0
    upper = max(0.0, headroom * CHAMFER_MAX_FRACTION)
    return min(c, upper)


def _inner_ring_endpoints(bore_r: float, half_w: float, chamfer: float) -> tuple[list, list]:
    """Liefert die Start-/Endpunkte eines Innenring-Profils mit Bohrungsfase.

    Der "Start" sind die Punkte am unteren z-Ende (negative z-Halbachse) vom
    Übergang Bohrungswand → Stirnfläche bis zur Schulter; das "Ende" sind die
    Punkte am oberen z-Ende von der Schulter zurück bis zur Bohrungswand. Ohne
    Fase entspricht das den klassischen Eckpunkten ``(bore_r, ±half_w)``.
    """
    if chamfer <= PROFILE_EPSILON:
        return [(bore_r, -half_w)], [(bore_r, half_w)]
    start = [(bore_r + chamfer, -half_w)]
    end = [
        (bore_r + chamfer, half_w),
        (bore_r, half_w - chamfer),
        (bore_r, -half_w + chamfer),
    ]
    return start, end


def _outer_ring_endpoints(outer_r: float, half_w: float, chamfer: float) -> tuple[list, list]:
    """Liefert die Eck-Punkte am Außenmantel mit optionaler OD-Fase.

    Profile von Außenringen traversieren den Außenmantel von ``-half_w`` nach
    ``+half_w``. Ohne Fase sind das zwei Punkte ``(outer_r, ±half_w)``; mit
    Fase werden die Außenkanten durch je zwei Punkte ersetzt.
    """
    if chamfer <= PROFILE_EPSILON:
        return [(outer_r, -half_w)], [(outer_r, half_w)]
    start = [
        (outer_r - chamfer, -half_w),
        (outer_r, -half_w + chamfer),
    ]
    end = [
        (outer_r, half_w - chamfer),
        (outer_r - chamfer, half_w),
    ]
    return start, end


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
    chamfer_mm: float = 0.0,
) -> Profile:
    """Querschnitt des Innenrings eines Rillenkugellagers.

    ``shoulder_d`` ist der Außen-Ø des Innenrings (Schulterhöhe). Reicht der
    Rillenbogen geometrisch nicht bis zur Schulter, wird ein einfacher
    Hohlzylinder zurückgegeben (Fallback ohne ausgeprägte Rille).

    ``chamfer_mm`` ist die 45°-Fase an den Bohrungskanten (DIN 620 r_s). Wird
    bei zu wenig Bauraum (sehr dünne Wand oder schmales Lager) automatisch
    auf einen sicheren Wert gekürzt; ``0`` lässt die Bohrungskante scharf.
    """
    bore_r = bore_d * 0.5
    shoulder_r = shoulder_d * 0.5
    pitch_r = pitch_d * 0.5
    half_w = width * 0.5
    groove_r = conformity * ball_d
    radial_gap = pitch_r - shoulder_r

    chamfer = _clamp_chamfer(chamfer_mm, shoulder_r - bore_r, half_w)
    start_pts, end_pts = _inner_ring_endpoints(bore_r, half_w, chamfer)

    if radial_gap <= PROFILE_EPSILON:
        return _dedupe_profile(
            [*start_pts, (shoulder_r, -half_w), (shoulder_r, half_w), *end_pts]
        )

    z_arc = _ball_groove_z_arc(
        radial_gap=radial_gap, groove_r=groove_r, ball_d=ball_d, width=width
    )
    if z_arc <= PROFILE_EPSILON:
        return _dedupe_profile(
            [*start_pts, (shoulder_r, -half_w), (shoulder_r, half_w), *end_pts]
        )

    arc = _arc_points_inner(pitch_r, groove_r, z_arc, arc_segments)
    profile: Profile = [
        *start_pts,
        (shoulder_r, -half_w),
        (shoulder_r, -z_arc),
    ]
    profile.extend(arc)
    profile.extend([
        (shoulder_r, z_arc),
        (shoulder_r, half_w),
        *end_pts,
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
    chamfer_mm: float = 0.0,
) -> Profile:
    """Querschnitt des Außenrings eines Rillenkugellagers.

    ``chamfer_mm`` ist die 45°-Fase an den Außenkanten (DIN 620). Wird auf
    den verfügbaren Bauraum begrenzt; ``0`` lässt die Außenkante scharf.
    """
    outer_r = outer_d * 0.5
    shoulder_r = shoulder_d * 0.5
    pitch_r = pitch_d * 0.5
    half_w = width * 0.5
    groove_r = conformity * ball_d
    radial_gap = shoulder_r - pitch_r

    chamfer = _clamp_chamfer(chamfer_mm, outer_r - shoulder_r, half_w)
    od_start, od_end = _outer_ring_endpoints(outer_r, half_w, chamfer)

    if radial_gap <= PROFILE_EPSILON:
        return _dedupe_profile(
            [(shoulder_r, -half_w), *od_start, *od_end, (shoulder_r, half_w)]
        )

    z_arc = _ball_groove_z_arc(
        radial_gap=radial_gap, groove_r=groove_r, ball_d=ball_d, width=width
    )
    if z_arc <= PROFILE_EPSILON:
        return _dedupe_profile(
            [(shoulder_r, -half_w), *od_start, *od_end, (shoulder_r, half_w)]
        )

    arc = _arc_points_outer(pitch_r, groove_r, z_arc, arc_segments)
    # Im Profil traversieren wir den Außenring so, dass die Innenfläche
    # (Rillen-Seite) im positiven z-Halbraum eingegangen und im negativen
    # wieder verlassen wird; dazu wird der Bogen umgekehrt eingefügt.
    profile: Profile = [
        (shoulder_r, -half_w),
        *od_start,
        *od_end,
        (shoulder_r, half_w),
        (shoulder_r, z_arc),
    ]
    profile.extend(reversed(arc))
    profile.append((shoulder_r, -z_arc))
    return _dedupe_profile(profile)


# ---------------------------------------------------------------------------
# U-/V-Rillen-Führungsrollenlager (SG/W-Reihe)
# ---------------------------------------------------------------------------


# Default-Geometrie der Außenrille einer SG-Führungsrolle. Werte sind
# Anteile, weil die Reihe stark unterschiedliche Baugrößen umfasst.
VGROOVE_DEFAULT_DEPTH_FRACTION = 0.35   # Anteil der radialen Außenring-Wand
VGROOVE_DEFAULT_HALF_ANGLE_DEG = 45.0   # Halbwinkel der V-Flanke (=> 90° V-Rille)
VGROOVE_MIN_DEPTH_MM = 0.3              # Mindesttiefe, sonst entartet die Rille
VGROOVE_MIN_FLAT_WIDTH_MM = 0.1         # Mindest-Flachstirn am OD links/rechts


def vgroove_outer_ring_profile(
    *,
    shoulder_d: float,
    outer_d: float,
    width: float,
    ball_d: float,
    pitch_d: float,
    groove_depth: float | None = None,
    groove_half_angle_rad: float | None = None,
    conformity: float = BALL_GROOVE_CONFORMITY_OUTER,
    arc_segments: int = 24,
    chamfer_mm: float = 0.0,
) -> Profile:
    """Außenring eines U-/V-Rillen-Kugellagers (Führungsrolle, SG-Reihe).

    Kombiniert die innere Kugelrille (Laufbahn) mit einer V-förmigen Außenrille
    auf dem Außenmantel (OD). ``groove_depth`` ist die radiale Tiefe der V-Rille
    in mm, ``groove_half_angle_rad`` der halbe Öffnungswinkel der V-Flanke. Wird
    keiner der Werte angegeben, wählt die Funktion sinnvolle Defaults aus
    Außenring-Wandstärke und 90°-V-Rille.

    ``chamfer_mm`` ist die 45°-Fase an den OD-Stirnkanten (links/rechts der
    V-Rille). Wird auf den verbleibenden axialen Flachstirn-Anteil und die
    Außenwand begrenzt.
    """
    outer_r = outer_d * 0.5
    shoulder_r = shoulder_d * 0.5
    pitch_r = pitch_d * 0.5
    half_w = width * 0.5

    # --- Defaults / Clamping für die Rillen-Parameter -----------------------
    wall = max(0.0, outer_r - shoulder_r)
    if groove_depth is None:
        groove_depth = wall * VGROOVE_DEFAULT_DEPTH_FRACTION
    # Tiefe muss klein bleiben gegenüber der Außenwand und gegen die halbe Breite,
    # sonst kollidiert die Rille mit der Stirnfläche bzw. der Laufbahnschulter.
    max_depth = max(0.0, min(wall * 0.85, half_w * 0.85))
    if max_depth < VGROOVE_MIN_DEPTH_MM:
        # Kein Platz für eine sichtbare Rille: Fallback auf Standard-Außenring.
        return ball_outer_ring_profile(
            shoulder_d=shoulder_d,
            outer_d=outer_d,
            width=width,
            ball_d=ball_d,
            pitch_d=pitch_d,
            conformity=conformity,
            arc_segments=arc_segments,
            chamfer_mm=chamfer_mm,
        )
    groove_depth = max(VGROOVE_MIN_DEPTH_MM, min(groove_depth, max_depth))

    if groove_half_angle_rad is None:
        groove_half_angle_rad = math.radians(VGROOVE_DEFAULT_HALF_ANGLE_DEG)
    groove_half_angle_rad = max(math.radians(5.0), min(groove_half_angle_rad, math.radians(80.0)))

    half_groove_w = math.tan(groove_half_angle_rad) * groove_depth
    # Mindestens VGROOVE_MIN_FLAT_WIDTH_MM Flachstirn an jeder Seite stehen lassen.
    half_groove_w = min(half_groove_w, half_w - VGROOVE_MIN_FLAT_WIDTH_MM)
    if half_groove_w <= PROFILE_EPSILON:
        return ball_outer_ring_profile(
            shoulder_d=shoulder_d,
            outer_d=outer_d,
            width=width,
            ball_d=ball_d,
            pitch_d=pitch_d,
            conformity=conformity,
            arc_segments=arc_segments,
            chamfer_mm=chamfer_mm,
        )
    groove_bottom_r = max(shoulder_r + PROFILE_EPSILON, outer_r - groove_depth)

    # --- Innere Laufbahn-Rille (Kugel) --------------------------------------
    groove_r = conformity * ball_d
    radial_gap = shoulder_r - pitch_r
    z_arc = 0.0
    inner_arc: Profile = []
    if radial_gap > PROFILE_EPSILON:
        z_arc = _ball_groove_z_arc(
            radial_gap=radial_gap, groove_r=groove_r, ball_d=ball_d, width=width
        )
        if z_arc > PROFILE_EPSILON:
            inner_arc = _arc_points_outer(pitch_r, groove_r, z_arc, arc_segments)

    # --- OD-Fase: nur soweit Flachstirn links/rechts der V-Rille bleibt ----
    flat_face = max(0.0, half_w - half_groove_w)
    chamfer = _clamp_chamfer(chamfer_mm, wall, flat_face)

    # --- Profil aufbauen ----------------------------------------------------
    # Reihenfolge analog ball_outer_ring_profile, aber mit V-Kerbe im Außen-
    # mantel (von -half_w nach +half_w, mittig). Bei vorhandener inneren Rille
    # wird der Bogen am Ende eingehängt; ohne Rille bleibt die Innenfläche
    # zylindrisch (shoulder_r).
    profile: Profile = [(shoulder_r, -half_w)]
    if chamfer > PROFILE_EPSILON:
        profile.extend([
            (outer_r - chamfer, -half_w),
            (outer_r, -half_w + chamfer),
        ])
    else:
        profile.append((outer_r, -half_w))
    profile.extend([
        (outer_r, -half_groove_w),
        (groove_bottom_r, 0.0),
        (outer_r, half_groove_w),
    ])
    if chamfer > PROFILE_EPSILON:
        profile.extend([
            (outer_r, half_w - chamfer),
            (outer_r - chamfer, half_w),
        ])
    else:
        profile.append((outer_r, half_w))
    profile.append((shoulder_r, half_w))
    if inner_arc:
        profile.append((shoulder_r, z_arc))
        profile.extend(reversed(inner_arc))
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
    large_flange_height_mm: float = 0.0,
    large_flange_axial_mm: float | None = None,
) -> Profile:
    """Innenring (Kegel) eines Kegelrollenlagers.

    Die Außenfläche tapert: am +z-Ende größer, am -z-Ende kleiner, passend zum
    typischen Aufstellsinn von Kegelrollenlagern (kleine Stirn der Rolle nach
    -z). ``contact_angle_rad`` ist der Kontaktwinkel α; die Flanke der
    Innenlaufbahn wird mit α gegen die Lagerachse geneigt.

    Mit ``large_flange_height_mm > 0`` wird an der großen Stirnseite (+z) ein
    radial nach außen stehender Bord (Rib) ergänzt, der die Kegelrollen axial
    führt (DIN 720 / ISO 355). ``large_flange_axial_mm`` setzt die axiale
    Stärke des Bordes; ohne Angabe wird sie aus der Bordhöhe geschätzt.
    """
    bore_r = bore_d * 0.5
    shoulder_r = shoulder_d * 0.5
    half_w = width * 0.5

    # Halbe radiale Verschiebung der Konusenden gegenüber dem Mittenradius.
    delta = math.tan(max(0.0, contact_angle_rad)) * half_w
    r_minus = max(bore_r + PROFILE_EPSILON, shoulder_r - delta)
    r_plus = shoulder_r + delta

    flange_h = max(0.0, large_flange_height_mm)
    if flange_h <= PROFILE_EPSILON:
        return _dedupe_profile([
            (bore_r, -half_w),
            (r_minus, -half_w),
            (r_plus, half_w),
            (bore_r, half_w),
        ])

    if large_flange_axial_mm is None:
        flange_axial = min(half_w * 0.25, max(0.5, flange_h))
    else:
        flange_axial = large_flange_axial_mm
    flange_axial = max(PROFILE_EPSILON, min(flange_axial, half_w * 0.5))

    return _dedupe_profile([
        (bore_r, -half_w),
        (r_minus, -half_w),
        (r_plus, half_w - flange_axial),
        (r_plus + flange_h, half_w - flange_axial),
        (r_plus + flange_h, half_w),
        (bore_r, half_w),
    ])


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
    "vgroove_outer_ring_profile",
]
