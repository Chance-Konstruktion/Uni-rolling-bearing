"""ISO 492 / DIN 620 Maßtoleranzen – auf Hauptmaße angewendet.

Diese Schicht setzt die in der UI gewählte Toleranzklasse (NORMAL, P6, P5, P4)
tatsächlich in einen Maß-Versatz um. Real liegen die Abweichungen im
Mikrometer-Bereich; der Versatz wird auf die nominalen Hauptmaße d, D und B
addiert und fließt von dort durch den Geometrie-Resolver in das erzeugte
Mesh ein.

Konvention nach ISO 492: Obere Abweichung = 0 (Nennmaß ist Maximum), untere
Abweichung negativ. Wert ``Δdmp`` ist die mittlere Bohrungs-/Außen-Ø-
Abweichung, ``ΔBs`` die Breitenabweichung.

Die Tabellen sind eine kompakte, praxisorientierte Untermenge der Norm
(kleine bis mittlere Lager, einreihig). Werte in Mikrometer.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Tuple

# (Ø-Obergrenze in mm, untere Abweichung in µm) für Innenring-Bohrung d.
_BORE_NORMAL_UM: List[Tuple[float, float]] = [
    (18.0,   -8.0),
    (30.0,  -10.0),
    (50.0,  -12.0),
    (80.0,  -15.0),
    (120.0, -20.0),
    (180.0, -25.0),
    (250.0, -30.0),
]

# Außenring-Ø D.
_OD_NORMAL_UM: List[Tuple[float, float]] = [
    (30.0,   -9.0),
    (50.0,  -11.0),
    (80.0,  -13.0),
    (120.0, -15.0),
    (150.0, -18.0),
    (180.0, -25.0),
    (250.0, -30.0),
]

# Breite B (einreihig). Die Norm gibt für Normal die gleiche Spanne wie
# für die Bohrung d innerhalb derselben Größenbucket; hier vereinfacht.
_WIDTH_NORMAL_UM: List[Tuple[float, float]] = [
    (50.0,  -120.0),
    (120.0, -150.0),
    (250.0, -200.0),
]

# Skalierungsfaktor relativ zu Klasse NORMAL. P6 ≈ 0.7, P5 ≈ 0.5, P4 ≈ 0.3 –
# praxisnahe Mittelwerte aus DIN 620 / ISO 492.
_CLASS_FACTOR = {
    "NORMAL": 1.00,
    "P6":     0.70,
    "P5":     0.50,
    "P4":     0.30,
}

# UI-Optionen für die *Lage* innerhalb des Toleranzfensters (oberes, mittleres
# oder unteres Maß).
TOLERANCE_POSITIONS = [
    ("MAX",  "Oberes Maß",  "Maße auf oberer Toleranzgrenze (= Nennmaß)"),
    ("MEAN", "Mittenmaß",   "Maße in der Mitte des Toleranzfensters (Standardlage)"),
    ("MIN",  "Unteres Maß", "Maße auf unterer Toleranzgrenze"),
]


def _lookup_um(table: List[Tuple[float, float]], diameter_mm: float) -> float:
    for upper, dev in table:
        if diameter_mm <= upper:
            return dev
    raise ValueError(
        f"Toleranztabelle ist nur bis {table[-1][0]:g} mm abgedeckt; "
        f"Nennmaß {diameter_mm:g} mm liegt außerhalb dieses Bereichs."
    )


@dataclass(frozen=True)
class ToleranceWindow:
    """Zulässige Abweichungen in mm (negativ oder null) für ein Lager.

    ``upper`` ist immer 0 (Nennmaß). ``lower`` enthält die untere Abweichung.
    """
    bore_lower_mm: float
    od_lower_mm: float
    width_lower_mm: float

    @property
    def bore_lower_um(self) -> float:
        return self.bore_lower_mm * 1000.0

    @property
    def od_lower_um(self) -> float:
        return self.od_lower_mm * 1000.0

    @property
    def width_lower_um(self) -> float:
        return self.width_lower_mm * 1000.0


def window_for(
    precision_class: str,
    bore_d_mm: float,
    outer_d_mm: float,
    width_mm: float,
) -> ToleranceWindow:
    """Liefert das Toleranzfenster für die gewählte Klasse."""
    if not isinstance(precision_class, str) or precision_class not in _CLASS_FACTOR:
        raise ValueError(
            f"Unbekannte Präzisionsklasse {precision_class!r}; "
            f"erlaubt sind {', '.join(_CLASS_FACTOR)}."
        )
    for name, value in (
        ("Bohrungsdurchmesser", bore_d_mm),
        ("Außendurchmesser", outer_d_mm),
        ("Lagerbreite", width_mm),
    ):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value <= 0.0
        ):
            raise ValueError(f"{name} muss ein endlicher positiver Zahlenwert sein.")

    factor = _CLASS_FACTOR[precision_class]
    return ToleranceWindow(
        bore_lower_mm=_lookup_um(_BORE_NORMAL_UM, bore_d_mm) * factor / 1000.0,
        od_lower_mm=_lookup_um(_OD_NORMAL_UM, outer_d_mm) * factor / 1000.0,
        width_lower_mm=_lookup_um(_WIDTH_NORMAL_UM, width_mm) * factor / 1000.0,
    )


def _position_factor(position: str) -> float:
    """0.0 = oberes Maß (= Nennmaß), 0.5 = Mitte, 1.0 = unteres Maß."""
    if position == "MAX":
        return 0.0
    if position == "MEAN":
        return 0.5
    if position == "MIN":
        return 1.0
    raise ValueError(
        f"Unbekannte Toleranzlage {position!r}; erlaubt sind MAX, MEAN, MIN."
    )


@dataclass(frozen=True)
class EffectiveDimensions:
    """Effektive Hauptmaße nach Toleranzanwendung (in mm)."""
    bore_diameter: float
    outer_diameter: float
    width: float
    bore_offset_um: float
    od_offset_um: float
    width_offset_um: float


def apply_tolerances(
    *,
    bore_diameter_mm: float,
    outer_diameter_mm: float,
    width_mm: float,
    precision_class: str,
    position: str,
) -> EffectiveDimensions:
    """Wendet das Toleranzfenster und die gewählte Lage auf d, D, B an.

    Die untere Abweichung ist negativ; ``position`` skaliert sie zwischen 0
    (oberes Maß = Nennmaß) und 1 (volle untere Abweichung).
    """
    window = window_for(precision_class, bore_diameter_mm, outer_diameter_mm, width_mm)
    f = _position_factor(position)
    bore_off = window.bore_lower_mm * f
    od_off = window.od_lower_mm * f
    width_off = window.width_lower_mm * f
    return EffectiveDimensions(
        bore_diameter=bore_diameter_mm + bore_off,
        outer_diameter=outer_diameter_mm + od_off,
        width=width_mm + width_off,
        bore_offset_um=bore_off * 1000.0,
        od_offset_um=od_off * 1000.0,
        width_offset_um=width_off * 1000.0,
    )


__all__ = [
    "TOLERANCE_POSITIONS",
    "ToleranceWindow",
    "EffectiveDimensions",
    "window_for",
    "apply_tolerances",
]
