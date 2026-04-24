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
