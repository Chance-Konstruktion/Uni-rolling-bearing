"""Empfohlene Wellen- und Gehäusepassungen nach DIN 5418 / ISO 286.

DIN 5418 ordnet je nach Belastungsfall (rotierender Innenring, rotierender
Außenring, Punktlast vs. Umfangslast, Belastungshöhe) eine ISO 286-
Toleranzklasse zu. Die genauen Empfehlungen hängen zusätzlich vom
Bohrungsdurchmesser ``d`` bzw. Außendurchmesser ``D`` und vom Lagertyp ab.

Dieses Modul deckt den praxisrelevanten Mittelbereich ab (d, D in 1..250 mm)
und liefert für die typischen Lastfälle die empfohlene Klasse plus die
zugehörigen ISO 286-Abmaße in µm. Für Lager außerhalb der Tabelle wird
die Klasse weitergegeben, die Abmaße aber als ``None`` markiert.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


# Belastungsfälle nach DIN 5418.
LOAD_CASES = [
    ("INNER_ROT_LIGHT", "Innenring rotiert, leicht",
     "Umfangslast am Innenring, geringe Belastung (P ≤ 0.07·C)"),
    ("INNER_ROT_NORMAL", "Innenring rotiert, normal",
     "Umfangslast am Innenring, normale Belastung (0.07·C < P ≤ 0.15·C)"),
    ("INNER_ROT_HEAVY", "Innenring rotiert, schwer",
     "Umfangslast am Innenring, hohe Belastung oder Stöße (P > 0.15·C)"),
    ("OUTER_ROT", "Außenring rotiert",
     "Umfangslast am Außenring (z. B. Förderrollen)"),
    ("STATIONARY", "Stillstehend / unbestimmt",
     "Beide Ringe ohne Umfangslast oder Wechsellast"),
]


# ISO 286 Diameter-Bereiche (in mm, exklusiv-oberer Grenzwert).
_DIAMETER_RANGES: Tuple[Tuple[float, float], ...] = (
    (1.0, 3.0), (3.0, 6.0), (6.0, 10.0), (10.0, 18.0),
    (18.0, 30.0), (30.0, 50.0), (50.0, 80.0), (80.0, 120.0),
    (120.0, 180.0), (180.0, 250.0),
)


def _range_index(diameter_mm: float) -> Optional[int]:
    for i, (low, high) in enumerate(_DIAMETER_RANGES):
        if low < diameter_mm <= high:
            return i
    return None


# ISO 286-1 Toleranzklassen → (upper_es_µm, lower_ei_µm) je Diameter-Bracket.
# Werte aus ISO 286-1:2010, Tabellen 1/2.
# Reihenfolge entspricht ``_DIAMETER_RANGES``.
# fmt: off
_SHAFT_FITS: dict = {
    "g6": [(-2, -8), (-4, -12), (-5, -14), (-6, -17), (-7, -20),
           (-9, -25), (-10, -29), (-12, -34), (-14, -39), (-15, -44)],
    "h6": [(0, -6), (0, -8), (0, -9), (0, -11), (0, -13),
           (0, -16), (0, -19), (0, -22), (0, -25), (0, -29)],
    "j6": [(+4, -2), (+6, -2), (+7, -2), (+8, -3), (+9, -4),
           (+11, -5), (+12, -7), (+13, -9), (+14, -11), (+16, -13)],
    "k5": [(+4, 0), (+6, +1), (+7, +1), (+9, +1), (+11, +2),
           (+13, +2), (+15, +2), (+18, +3), (+21, +3), (+24, +4)],
    "k6": [(+6, 0), (+9, +1), (+10, +1), (+12, +1), (+15, +2),
           (+18, +2), (+21, +2), (+25, +3), (+28, +3), (+33, +4)],
    "m5": [(+6, +2), (+9, +4), (+12, +6), (+15, +7), (+17, +8),
           (+20, +9), (+24, +11), (+28, +13), (+33, +15), (+37, +17)],
    "m6": [(+8, +2), (+12, +4), (+15, +6), (+18, +7), (+21, +8),
           (+25, +9), (+30, +11), (+35, +13), (+40, +15), (+46, +17)],
    "n6": [(+10, +4), (+16, +8), (+19, +10), (+23, +12), (+28, +15),
           (+33, +17), (+39, +20), (+45, +23), (+52, +27), (+60, +31)],
    "p6": [(+12, +6), (+20, +12), (+24, +15), (+29, +18), (+35, +22),
           (+42, +26), (+51, +32), (+59, +37), (+68, +43), (+79, +50)],
}

_HOUSING_FITS: dict = {
    "G7": [(+12, +2), (+16, +4), (+20, +5), (+24, +6), (+28, +7),
           (+34, +9), (+40, +10), (+47, +12), (+54, +14), (+61, +15)],
    "H6": [(+6, 0), (+8, 0), (+9, 0), (+11, 0), (+13, 0),
           (+16, 0), (+19, 0), (+22, 0), (+25, 0), (+29, 0)],
    "H7": [(+10, 0), (+12, 0), (+15, 0), (+18, 0), (+21, 0),
           (+25, 0), (+30, 0), (+35, 0), (+40, 0), (+46, 0)],
    "J7": [(+4, -6), (+6, -6), (+8, -7), (+10, -8), (+12, -9),
           (+14, -11), (+18, -12), (+22, -13), (+26, -14), (+30, -16)],
    "K7": [(0, -10), (+3, -9), (+5, -10), (+6, -12), (+6, -15),
           (+7, -18), (+9, -21), (+10, -25), (+12, -28), (+13, -33)],
    "M7": [(-2, -12), (0, -12), (0, -15), (0, -18), (0, -21),
           (0, -25), (0, -30), (0, -35), (0, -40), (0, -46)],
    "N7": [(-4, -14), (-4, -16), (-4, -19), (-5, -23), (-7, -28),
           (-8, -33), (-9, -39), (-10, -45), (-12, -52), (-14, -60)],
    "P7": [(-6, -16), (-8, -20), (-9, -24), (-11, -29), (-14, -35),
           (-17, -42), (-21, -51), (-24, -59), (-28, -68), (-33, -79)],
}
# fmt: on


def _shaft_class_for(load_case: str, bore_mm: float) -> str:
    """DIN 5418-orientierte Empfehlung für die Welle."""
    if load_case == "STATIONARY":
        return "h6"
    if load_case == "OUTER_ROT":
        # Punktlast am Innenring → loser Sitz.
        return "g6"
    # Innenring rotiert: Übergangs-/Übermaßpassung, Stufung mit Last und d.
    if load_case == "INNER_ROT_LIGHT":
        if bore_mm <= 50.0:
            return "j6"
        return "k6"
    if load_case == "INNER_ROT_NORMAL":
        if bore_mm <= 18.0:
            return "j6"
        if bore_mm <= 100.0:
            return "k5" if bore_mm <= 50.0 else "k6"
        if bore_mm <= 200.0:
            return "m6"
        return "n6"
    # INNER_ROT_HEAVY
    if bore_mm <= 50.0:
        return "k6"
    if bore_mm <= 100.0:
        return "m6"
    if bore_mm <= 200.0:
        return "n6"
    return "p6"


def _housing_class_for(load_case: str) -> str:
    """DIN 5418-orientierte Empfehlung für die Gehäusebohrung."""
    if load_case == "OUTER_ROT":
        return "N7"
    if load_case == "INNER_ROT_HEAVY":
        return "K7"
    if load_case == "INNER_ROT_NORMAL":
        return "J7"
    if load_case == "STATIONARY":
        return "H7"
    # INNER_ROT_LIGHT – axial verschieblich erwünscht.
    return "H7"


def _deviations(class_name: str, diameter_mm: float, table: dict) -> Optional[Tuple[int, int]]:
    idx = _range_index(diameter_mm)
    if idx is None:
        return None
    entry = table.get(class_name)
    if entry is None or idx >= len(entry):
        return None
    upper, lower = entry[idx]
    return upper, lower


@dataclass(frozen=True)
class FitRecommendation:
    load_case: str
    shaft_class: str
    housing_class: str
    shaft_upper_um: Optional[int]
    shaft_lower_um: Optional[int]
    housing_upper_um: Optional[int]
    housing_lower_um: Optional[int]


def recommend_fits(
    load_case: str,
    bore_diameter_mm: float,
    outer_diameter_mm: float,
) -> FitRecommendation:
    """Liefert empfohlene Welle/Gehäuse-Klassen + Abmaße nach DIN 5418."""
    shaft_cls = _shaft_class_for(load_case, bore_diameter_mm)
    housing_cls = _housing_class_for(load_case)
    shaft_dev = _deviations(shaft_cls, bore_diameter_mm, _SHAFT_FITS)
    housing_dev = _deviations(housing_cls, outer_diameter_mm, _HOUSING_FITS)
    return FitRecommendation(
        load_case=load_case,
        shaft_class=shaft_cls,
        housing_class=housing_cls,
        shaft_upper_um=shaft_dev[0] if shaft_dev else None,
        shaft_lower_um=shaft_dev[1] if shaft_dev else None,
        housing_upper_um=housing_dev[0] if housing_dev else None,
        housing_lower_um=housing_dev[1] if housing_dev else None,
    )
