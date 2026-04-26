"""Reine Geometrieberechnungen – ohne Blender-Abhängigkeit, daher testbar."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from . import constants

# Mindesthöhe [mm] für den nutzbaren Ringspalt, damit ein Wälzkörper sinnvoll passt.
MIN_USABLE_SPACE_MM = 0.2

# Sicherheitsabschlag am maximal erlaubten Wälzkörper-Ø – verhindert 0-Spalt
# zwischen Wälzkörper und Laufbahn.
ROLLER_SAFETY_FRACTION = 0.98

# Verhältnis Ringstärke zu Radial-Bereich (D-d) für Preset-Vorschläge:
# entspricht etwa der Praxis bei Standard-Wälzlagern.
SUGGESTED_RING_THICKNESS_FRACTION = 1.0 / 6.0
MIN_SUGGESTED_RING_THICKNESS_MM = 0.5
MAX_SUGGESTED_RING_THICKNESS_MM = 8.0

# Wie viel des nutzbaren Spalts (nach Abzug der Lagerluft) der vorgeschlagene
# Wälzkörper-Ø einnimmt. Lässt etwas Spielraum gegenüber dem harten Maximum.
SUGGESTED_ROLLER_FILL = 0.90


@dataclass(frozen=True)
class BearingDims:
    """Abgeleitete Hauptmaße in mm."""

    inner_outer_d: float  # Außen-Ø des Innenrings = Innenlaufbahn
    outer_inner_d: float  # Innen-Ø des Außenrings = Außenlaufbahn
    radial_space: float  # Roher Laufbahnspalt (ohne Lagerluft-Abzug)


@dataclass(frozen=True)
class ResolvedBearing:
    """Ergebnis des Geometrie-Resolvers – alle Werte in mm bzw. Stückzahl."""

    inner_outer_d: float
    outer_inner_d: float
    roller_d: float
    roller_length: float
    pitch_d: float
    element_count: int


def compute_dims(
    bore_diameter: float,
    outer_diameter: float,
    ring_thickness: float,
) -> BearingDims:
    """Leitet Laufbahn-Durchmesser und radialen Rohspalt aus den Hauptmaßen ab."""
    inner_outer_d = bore_diameter + 2.0 * ring_thickness
    outer_inner_d = outer_diameter - 2.0 * ring_thickness
    radial_space = outer_inner_d - inner_outer_d
    return BearingDims(inner_outer_d, outer_inner_d, radial_space)


def max_elements_for_pitch(
    pitch_diameter: float,
    element_diameter: float,
    gap_factor: float,
) -> int:
    """Maximale Wälzkörperanzahl, bei der sie sich auf dem Teilkreis nicht überlappen.

    ``gap_factor`` ist der relative Zusatzabstand (z. B. 0.1 = 10 % Spalt).
    """
    circumference = math.pi * pitch_diameter
    element_pitch = max(0.1, element_diameter * (1.0 + gap_factor))
    return max(3, int(circumference // element_pitch))


def roller_length_for_type(bearing_type: str, width: float, roller_d: float) -> float:
    """Liefert die Rollenlänge in Abhängigkeit vom Lagertyp.

    Für Kugellager wird die Länge gleich dem Ø gesetzt (Kugel).
    """
    if bearing_type == constants.BALL:
        return roller_d
    ratio = constants.ROLLER_LENGTH_RATIO.get(bearing_type)
    if ratio is None:
        return roller_d
    return width * ratio


def resolve_geometry(
    *,
    bearing_type: str,
    bore_diameter: float,
    outer_diameter: float,
    width: float,
    ring_thickness: float,
    roller_diameter: float,
    element_count: int,
    radial_clearance: float,
    gap_factor: float,
    auto_fit: bool,
) -> Tuple[Optional[ResolvedBearing], Optional[str]]:
    """Löst alle Parameter zu einer funktionsfähigen Geometrie auf.

    Gibt ``(spec, None)`` bei Erfolg oder ``(None, error_message)`` zurück.
    Mit ``auto_fit=True`` werden unplausible Werte stillschweigend korrigiert.
    """
    if bore_diameter >= outer_diameter:
        return None, "Innendurchmesser muss kleiner als Außendurchmesser sein."

    dims = compute_dims(bore_diameter, outer_diameter, ring_thickness)
    if dims.radial_space <= 0.0:
        return None, "Ringstärke/Abmessungen erzeugen keinen Laufbahnspalt."

    usable_space = dims.radial_space - 2.0 * radial_clearance
    if usable_space <= MIN_USABLE_SPACE_MM:
        return None, "Zu wenig Platz zwischen den Ringen nach Abzug der Lagerluft."

    max_roller_d = usable_space * ROLLER_SAFETY_FRACTION
    if roller_diameter > max_roller_d:
        if not auto_fit:
            return None, (
                f"Wälzkörper-Ø ({roller_diameter:.2f} mm) ist zu groß. "
                f"Maximal zulässig: {max_roller_d:.2f} mm."
            )
        roller_d = max_roller_d
    else:
        roller_d = roller_diameter

    pitch_d = dims.inner_outer_d + roller_d + 2.0 * radial_clearance
    max_count = max_elements_for_pitch(pitch_d, roller_d, gap_factor)
    if element_count > max_count:
        if not auto_fit:
            return None, (
                f"Zu viele Wälzkörper ({element_count}). "
                f"Maximal zulässig: {max_count} für aktuellen Pitch/Ø."
            )
        resolved_count = max_count
    else:
        resolved_count = element_count

    roller_length = roller_length_for_type(bearing_type, width, roller_d)

    spec = ResolvedBearing(
        inner_outer_d=dims.inner_outer_d,
        outer_inner_d=dims.outer_inner_d,
        roller_d=roller_d,
        roller_length=roller_length,
        pitch_d=pitch_d,
        element_count=max(3, resolved_count),
    )
    return spec, None


@dataclass(frozen=True)
class SuggestedDefaults:
    """Geometrisch plausible Defaults zu einer Hauptmaß-Vorgabe."""

    ring_thickness: float
    roller_diameter: float
    element_count: int


def suggest_defaults(
    bearing_type: str,
    bore_diameter: float,
    outer_diameter: float,
    *,
    radial_clearance: float = 0.02,
    gap_factor: float = 0.10,
) -> SuggestedDefaults:
    """Liefert ring_thickness/roller_d/Anzahl, mit denen ein Preset sofort funktioniert.

    Der Wälzkörper-Ø nimmt rund 90 % des nutzbaren Spalts ein, die Anzahl wird auf den
    maximalen umfangskonformen Wert gesetzt.
    """
    if bore_diameter >= outer_diameter:
        # Degenerate Eingabe – minimaler Default damit nichts crasht.
        return SuggestedDefaults(MIN_SUGGESTED_RING_THICKNESS_MM, 0.5, 3)

    radial_band = outer_diameter - bore_diameter
    ring_thickness = max(
        MIN_SUGGESTED_RING_THICKNESS_MM,
        min(
            MAX_SUGGESTED_RING_THICKNESS_MM,
            radial_band * SUGGESTED_RING_THICKNESS_FRACTION,
        ),
    )

    dims = compute_dims(bore_diameter, outer_diameter, ring_thickness)
    usable = max(MIN_USABLE_SPACE_MM, dims.radial_space - 2.0 * radial_clearance)
    roller_d = max(0.5, usable * SUGGESTED_ROLLER_FILL)
    pitch_d = dims.inner_outer_d + roller_d + 2.0 * radial_clearance
    count = max_elements_for_pitch(pitch_d, roller_d, gap_factor)

    # bearing_type beeinflusst nur die Rollenlänge (über width); die Vorschläge
    # für d/Anzahl/Ringstärke sind typunabhängig. Argument bleibt für künftige
    # typabhängige Heuristiken erhalten.
    del bearing_type

    return SuggestedDefaults(
        ring_thickness=ring_thickness,
        roller_diameter=roller_d,
        element_count=count,
    )


# ---------------------------------------------------------------------------
# Kegelrollenlager (Tapered)
# ---------------------------------------------------------------------------


def tapered_apex_z(pitch_d: float, roller_length: float, contact_angle_rad: float) -> float:
    """Z-Position des Apex (gemeinsamer Treffpunkt aller Kegelrollen-Achsen).

    Annahmen: Roller-Mittelpunkt liegt auf dem Teilkreis-Radius bei z=0 und ist um
    ``contact_angle_rad`` um die lokale Y-Achse gekippt (kleine Stirnseite zur
    Lagerachse hin, große von ihr weg). Der Apex liegt auf der Lagerachse (x=y=0)
    auf der Seite der kleinen Stirn.

    Für ``contact_angle_rad <= 0`` ist die Roller-Achse parallel zur Lagerachse;
    in dem Fall liefert die Funktion ``-inf``.
    """
    if contact_angle_rad <= 0.0:
        return float("-inf")
    pitch_r = pitch_d * 0.5
    sin_a = math.sin(contact_angle_rad)
    cos_a = math.cos(contact_angle_rad)
    # Kleine Stirn nach dem Tilt liegt bei (pitch_r - sin α · L/2, 0, -cos α · L/2).
    # Apex erreicht man durch Verlängern der Achse bis x=0:
    small_x = pitch_r - sin_a * roller_length * 0.5
    small_z = -cos_a * roller_length * 0.5
    if sin_a == 0.0:
        return float("-inf")
    t = small_x / sin_a  # Schritte entlang der negativen Achsenrichtung
    return small_z - t * cos_a


# ---------------------------------------------------------------------------
# Käfig (Cage)
# ---------------------------------------------------------------------------

# Mindestmaße in mm, damit die Käfig-Geometrie nicht in degenerate Zustände kippt.
MIN_CAGE_PLATE_THICKNESS_MM = 0.2
MIN_CAGE_WEB_RADIAL_MM = 0.4
MIN_CAGE_WEB_TANGENTIAL_MM = 0.3
# Axiales Spiel zwischen Wälzkörperende und innerer Plattenfläche.
CAGE_AXIAL_CLEARANCE_MM = 0.1
# Radialer Sicherheitsabstand zwischen Käfig und Laufbahn (an Innen-/Außenring).
CAGE_RACE_CLEARANCE_MM = 0.2
# Radialer Überstand der Endplatten gegenüber dem Wälzkörper-Querschnitt – wird
# notfalls durch die Laufbahn-Clearance gedeckelt.
CAGE_PLATE_RADIAL_OVERHANG_FACTOR = 0.15
# Anteil des tangentialen Spalts zwischen Wälzkörpern, den ein Web ausnutzt.
CAGE_WEB_TANGENTIAL_FILL = 0.6


@dataclass(frozen=True)
class CageDims:
    """Geometrie eines simplen 'Leiter'-Käfigs (zwei Endplatten + Webs)."""

    plate_inner_d: float        # Innen-Ø der Endplatten (an beiden Lagerenden)
    plate_outer_d: float        # Außen-Ø der Endplatten
    plate_thickness: float      # Axiale Stärke je Platte
    plate_z_offset: float       # |z| Mittenposition jeder Platte
    web_pitch_r: float          # Radius, auf dem die Webs sitzen
    web_radial_size: float      # Radialdicke je Web
    web_tangential_size: float  # Tangentialbreite je Web
    web_axial_length: float     # Gesamt-Z-Länge eines Webs (Plattenmitte zu Plattenmitte)
    web_count: int              # Anzahl Webs (= Anzahl Wälzkörper)


def cage_dimensions(
    *,
    pitch_d: float,
    roller_d: float,
    roller_length: float,
    width: float,
    element_count: int,
    inner_race_d: float,
    outer_race_d: float,
) -> Optional[CageDims]:
    """Berechnet die Käfigmaße. Liefert ``None``, wenn kein Platz vorhanden ist.

    ``inner_race_d`` ist der Außen-Ø des Innenrings (Innenlaufbahn-Ø),
    ``outer_race_d`` ist der Innen-Ø des Außenrings (Außenlaufbahn-Ø).
    Die Endplatten werden so dimensioniert, dass sie den Wälzkörper-Querschnitt
    radial abdecken, ohne die Laufbahnen zu berühren.
    """
    if element_count < 3 or pitch_d <= 0.0 or roller_d <= 0.0 or width <= 0.0:
        return None
    if inner_race_d <= 0.0 or outer_race_d <= inner_race_d:
        return None

    pitch_r = pitch_d * 0.5
    roller_r = roller_d * 0.5

    # Wunschmaße: Plattenrand reicht knapp über den Wälzkörper-Querschnitt hinaus,
    # bleibt aber mit ``CAGE_RACE_CLEARANCE_MM`` Abstand zur Laufbahn.
    overhang = roller_d * CAGE_PLATE_RADIAL_OVERHANG_FACTOR
    plate_inner_d_target = pitch_d - roller_d - overhang
    plate_outer_d_target = pitch_d + roller_d + overhang

    plate_inner_d = max(plate_inner_d_target, inner_race_d + 2.0 * CAGE_RACE_CLEARANCE_MM)
    plate_outer_d = min(plate_outer_d_target, outer_race_d - 2.0 * CAGE_RACE_CLEARANCE_MM)
    if plate_outer_d - plate_inner_d <= 2.0 * MIN_CAGE_WEB_RADIAL_MM:
        return None

    # Axialer Restraum zwischen Wälzkörperende und Lagerstirn.
    half_elem = max(roller_r, roller_length * 0.5)
    bearing_half_w = width * 0.5
    free_axial = bearing_half_w - half_elem - CAGE_AXIAL_CLEARANCE_MM
    if free_axial <= MIN_CAGE_PLATE_THICKNESS_MM:
        return None

    plate_thickness = max(MIN_CAGE_PLATE_THICKNESS_MM, min(2.0, free_axial * 0.8))
    plate_z_offset = half_elem + CAGE_AXIAL_CLEARANCE_MM + plate_thickness * 0.5

    # Tangentiale Lücke zwischen Wälzkörpern auf dem Teilkreis.
    angular_pitch = 2.0 * math.pi / element_count
    tangential_gap = pitch_r * angular_pitch - roller_d
    if tangential_gap <= MIN_CAGE_WEB_TANGENTIAL_MM:
        return None

    web_radial_size = max(MIN_CAGE_WEB_RADIAL_MM, min(2.0, roller_r * 0.4))
    web_tangential_size = max(
        MIN_CAGE_WEB_TANGENTIAL_MM,
        tangential_gap * CAGE_WEB_TANGENTIAL_FILL,
    )
    # Web reicht zwischen die Plattenmittel (mit leichter Überlappung).
    web_axial_length = 2.0 * plate_z_offset

    return CageDims(
        plate_inner_d=plate_inner_d,
        plate_outer_d=plate_outer_d,
        plate_thickness=plate_thickness,
        plate_z_offset=plate_z_offset,
        web_pitch_r=pitch_r,
        web_radial_size=web_radial_size,
        web_tangential_size=web_tangential_size,
        web_axial_length=web_axial_length,
        web_count=element_count,
    )
