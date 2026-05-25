"""Tragzahlen und Lebensdauer nach ISO 76 / ISO 281.

Die Berechnung folgt den ISO-Standardformeln, die Beiwerte ``f0`` (statisch)
und ``fc`` (dynamisch) werden über das Hüllkurvenverhältnis

    γ = Dw · cos(α) / dm

aus tabellierten Werten linear interpoliert (Auszug aus ISO 76 Annex und
ISO 281 Annex A). Reicht γ über den tabellierten Bereich hinaus, wird der
Randwert verwendet. Für die Pendel- bzw. Kegelrollenlager-Geometrie wird
ein konstanter Kontaktwinkel angesetzt.

Alle Eingaben in mm, Ausgaben in Newton bzw. Stunden (L10h).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

from . import constants


# ISO 76 Annex – Beiwert f0(γ) für die statische radiale Tragzahl C0r.
# Gerundet auf eine Nachkommastelle; ausgewählte γ-Stützstellen, dazwischen
# wird linear interpoliert.
_F0_BALL_TABLE: List[Tuple[float, float]] = [
    (0.05, 12.7), (0.06, 13.0), (0.07, 13.2), (0.08, 13.4),
    (0.09, 13.6), (0.10, 13.7), (0.12, 13.9), (0.14, 14.1),
    (0.16, 14.2), (0.18, 14.3), (0.20, 14.4), (0.22, 14.4),
    (0.24, 14.5), (0.26, 14.5), (0.28, 14.5), (0.30, 14.5),
    (0.32, 14.5), (0.34, 14.4),
]
_F0_ROLLER_TABLE: List[Tuple[float, float]] = [
    (0.05, 44.0), (0.06, 44.4), (0.07, 44.7), (0.08, 45.0),
    (0.09, 45.2), (0.10, 45.4), (0.12, 45.5), (0.14, 45.4),
    (0.16, 45.3), (0.18, 45.0), (0.20, 44.6), (0.22, 44.1),
    (0.24, 43.5), (0.26, 42.8), (0.28, 41.9), (0.30, 40.9),
]

# ISO 281 Annex A – Beiwert fc(γ) für die dynamische radiale Tragzahl Cr.
_FC_BALL_TABLE: List[Tuple[float, float]] = [
    (0.05, 46.7), (0.06, 49.1), (0.07, 51.1), (0.08, 52.8),
    (0.09, 54.3), (0.10, 55.5), (0.12, 57.5), (0.14, 58.8),
    (0.16, 59.6), (0.18, 59.9), (0.20, 59.9), (0.22, 59.6),
    (0.24, 59.0), (0.26, 58.2), (0.28, 57.1), (0.30, 55.8),
    (0.32, 54.3), (0.34, 52.7),
]
_FC_ROLLER_TABLE: List[Tuple[float, float]] = [
    (0.05, 75.2), (0.06, 77.4), (0.07, 79.2), (0.08, 80.6),
    (0.09, 81.7), (0.10, 82.6), (0.12, 84.0), (0.14, 84.7),
    (0.16, 84.8), (0.18, 84.6), (0.20, 84.0), (0.22, 83.0),
    (0.24, 81.7), (0.26, 80.2), (0.28, 78.5), (0.30, 76.5),
]

# bm – Materialfaktor nach ISO 281 (Normal-Stahl). 1.3 für Kugel-, 1.1 für
# Rollenlager.
_BM_BALL = 1.3
_BM_ROLLER = 1.1


def _contact_angle_rad(bearing_type: str, contact_angle_deg: float) -> float:
    if bearing_type == constants.TAPERED:
        return math.radians(contact_angle_deg)
    if bearing_type == constants.SPHERICAL:
        return math.radians(10.0)
    return 0.0


def _rows(bearing_type: str) -> int:
    return 2 if bearing_type == constants.SPHERICAL else 1


def _is_ball(bearing_type: str) -> bool:
    return bearing_type in (constants.BALL, constants.VGROOVE)


def _life_exponent(bearing_type: str) -> float:
    return 3.0 if _is_ball(bearing_type) else 10.0 / 3.0


def _interpolate(table: List[Tuple[float, float]], x: float) -> float:
    """Lineare Interpolation in einer (x, y)-Tabelle, an den Rändern geclampt."""
    if not table:
        return 0.0
    if x <= table[0][0]:
        return table[0][1]
    if x >= table[-1][0]:
        return table[-1][1]
    for (x0, y0), (x1, y1) in zip(table, table[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return table[-1][1]


def gamma(roller_d_mm: float, contact_angle_rad: float, pitch_d_mm: float) -> float:
    """Hüllkurvenverhältnis γ = Dw · cos(α) / dm nach ISO 281.

    Liefert ``0.0``, wenn ``pitch_d_mm`` nicht positiv ist; das wirkt im
    Tabellen-Lookup wie der untere Randwert (γ = kleinste Stützstelle).
    """
    if pitch_d_mm <= 0.0:
        return 0.0
    return roller_d_mm * math.cos(contact_angle_rad) / pitch_d_mm


def f0_for(bearing_type: str, gamma_val: float) -> float:
    """ISO 76-Beiwert ``f0(γ)`` für die statische Tragzahl."""
    table = _F0_BALL_TABLE if _is_ball(bearing_type) else _F0_ROLLER_TABLE
    return _interpolate(table, gamma_val)


def fc_for(bearing_type: str, gamma_val: float) -> float:
    """ISO 281-Beiwert ``fc(γ)`` für die dynamische Tragzahl."""
    table = _FC_BALL_TABLE if _is_ball(bearing_type) else _FC_ROLLER_TABLE
    return _interpolate(table, gamma_val)


@dataclass(frozen=True)
class Ratings:
    static_C0_N: float
    dynamic_C_N: float
    life_exponent: float
    gamma: float
    f0: float
    fc: float
    X: float = 1.0
    Y: float = 0.0
    e: float = 0.0
    P_N: float = 0.0
    L10h: Optional[float] = None


# ISO 281 Tabelle 4 (Auszug, einreihiges Rillenkugellager): Werte für die
# Beiwerte e und Y als Funktion von Fa/C0r. Stützstellen aus Schaeffler/
# FAG- und SKF-Standardkatalogen; reale Lager weichen je Hersteller leicht
# ab. Zwischen den Punkten wird linear interpoliert, außerhalb des Bereichs
# an den Randwerten geclampt.
_BALL_E_Y_TABLE: List[Tuple[float, float, float]] = [
    # (Fa/C0,  e,    Y  )
    (0.025,   0.22, 2.00),
    (0.040,   0.24, 1.80),
    (0.070,   0.27, 1.60),
    (0.130,   0.31, 1.40),
    (0.250,   0.37, 1.20),
    (0.500,   0.44, 1.00),
]


def _ball_e_y(fa_over_c0: float) -> Tuple[float, float]:
    """Interpoliert (e, Y) aus der Fa/C0-Tabelle für einreihige Kugellager."""
    if not _BALL_E_Y_TABLE:
        return 0.22, 2.0
    if fa_over_c0 <= _BALL_E_Y_TABLE[0][0]:
        return _BALL_E_Y_TABLE[0][1], _BALL_E_Y_TABLE[0][2]
    if fa_over_c0 >= _BALL_E_Y_TABLE[-1][0]:
        return _BALL_E_Y_TABLE[-1][1], _BALL_E_Y_TABLE[-1][2]
    for (x0, e0, y0), (x1, e1, y1) in zip(_BALL_E_Y_TABLE, _BALL_E_Y_TABLE[1:]):
        if x0 <= fa_over_c0 <= x1:
            t = (fa_over_c0 - x0) / (x1 - x0)
            return e0 + t * (e1 - e0), y0 + t * (y1 - y0)
    return _BALL_E_Y_TABLE[-1][1], _BALL_E_Y_TABLE[-1][2]


@dataclass(frozen=True)
class LoadFactors:
    """Ergebnis der X-/Y-Faktor-Bestimmung nach ISO 281 (Tabelle 4)."""
    X: float
    Y: float
    e: float
    P_N: float


def equivalent_load(
    bearing_type: str,
    radial_load_Fr_N: float,
    axial_load_Fa_N: float,
    static_C0_N: float,
    contact_angle_deg: float = 0.0,
) -> LoadFactors:
    """Liefert X, Y, e und das äquivalente ``P = X·Fr + Y·Fa`` nach ISO 281.

    Lagertyp-abhängige Regeln:

    * Rillenkugellager (BALL/VGROOVE): e und Y aus Tabelle 4 (Fa/C0r-
      interpoliert); X = 1 für Fa/Fr ≤ e, sonst X = 0.56.
    * Kegelrollenlager (TAPERED): e = 1.5·tan(α), Y = 0.4/tan(α);
      X = 1 für Fa/Fr ≤ e, sonst X = 0.4.
    * Pendelrollenlager (SPHERICAL): e = 1.5·tan(α); für Fa/Fr ≤ e gilt
      X = 1, Y1 ≈ 0.45/tan(α); darüber X = 0.67, Y2 ≈ 0.67/tan(α).
    * Zylinderrollen-/Nadellager (CYLINDRICAL/NEEDLE): rein radial.
      ``Fa`` wird ignoriert; P = Fr.
    """
    Fr = max(0.0, radial_load_Fr_N)
    Fa = max(0.0, axial_load_Fa_N)
    alpha = _contact_angle_rad(bearing_type, contact_angle_deg)

    if _is_ball(bearing_type):
        if static_C0_N <= 0.0:
            e, Y = _BALL_E_Y_TABLE[0][1], _BALL_E_Y_TABLE[0][2]
        else:
            e, Y = _ball_e_y(Fa / static_C0_N)
        if Fr <= 0.0:
            # Rein axiale Belastung: dominiert von Y·Fa.
            return LoadFactors(0.56, Y, e, 0.56 * Fr + Y * Fa)
        if (Fa / Fr) <= e:
            return LoadFactors(1.0, 0.0, e, Fr)
        return LoadFactors(0.56, Y, e, 0.56 * Fr + Y * Fa)

    if bearing_type == constants.TAPERED:
        # Bei α = 0 fällt die Rolle in den Zylinderfall zurück (kein axial).
        if alpha <= 0.0:
            return LoadFactors(1.0, 0.0, 0.0, Fr)
        tan_a = math.tan(alpha)
        e = 1.5 * tan_a
        Y = 0.4 / tan_a
        if Fr <= 0.0 or (Fa / Fr) <= e:
            return LoadFactors(1.0, 0.0, e, Fr)
        return LoadFactors(0.4, Y, e, 0.4 * Fr + Y * Fa)

    if bearing_type == constants.SPHERICAL:
        # Pendellager-Default α=10° wird in _contact_angle_rad gesetzt.
        if alpha <= 0.0:
            return LoadFactors(1.0, 0.0, 0.0, Fr)
        tan_a = math.tan(alpha)
        e = 1.5 * tan_a
        Y_low = 0.45 / tan_a
        Y_high = 0.67 / tan_a
        if Fr <= 0.0 or (Fa / Fr) <= e:
            return LoadFactors(1.0, Y_low, e, Fr + Y_low * Fa)
        return LoadFactors(0.67, Y_high, e, 0.67 * Fr + Y_high * Fa)

    # CYLINDRICAL, NEEDLE: rein radial.
    return LoadFactors(1.0, 0.0, 0.0, Fr)


def static_load_rating(
    bearing_type: str,
    roller_d_mm: float,
    roller_length_mm: float,
    element_count: int,
    pitch_d_mm: float,
    contact_angle_deg: float = 0.0,
    rows: Optional[int] = None,
) -> float:
    """Statische radiale Tragzahl C0r nach ISO 76 mit γ-abhängigem ``f0``."""
    alpha = _contact_angle_rad(bearing_type, contact_angle_deg)
    i = rows if rows is not None else _rows(bearing_type)
    if element_count <= 0 or roller_d_mm <= 0.0:
        return 0.0
    g = gamma(roller_d_mm, alpha, pitch_d_mm)
    f0 = f0_for(bearing_type, g)
    if _is_ball(bearing_type):
        return f0 * i * element_count * roller_d_mm**2 * math.cos(alpha)
    if roller_length_mm <= 0.0:
        return 0.0
    return f0 * i * element_count * roller_length_mm * roller_d_mm * math.cos(alpha)


def dynamic_load_rating(
    bearing_type: str,
    roller_d_mm: float,
    roller_length_mm: float,
    element_count: int,
    pitch_d_mm: float,
    contact_angle_deg: float = 0.0,
    rows: Optional[int] = None,
) -> float:
    """Dynamische radiale Tragzahl Cr nach ISO 281 mit γ-abhängigem ``fc``."""
    alpha = _contact_angle_rad(bearing_type, contact_angle_deg)
    i = rows if rows is not None else _rows(bearing_type)
    if element_count <= 0 or roller_d_mm <= 0.0:
        return 0.0
    g = gamma(roller_d_mm, alpha, pitch_d_mm)
    fc = fc_for(bearing_type, g)
    if _is_ball(bearing_type):
        return (
            _BM_BALL
            * fc
            * (i * math.cos(alpha)) ** 0.7
            * element_count ** (2.0 / 3.0)
            * roller_d_mm ** 1.8
        )
    if roller_length_mm <= 0.0:
        return 0.0
    return (
        _BM_ROLLER
        * fc
        * (i * roller_length_mm * math.cos(alpha)) ** (7.0 / 9.0)
        * element_count ** 0.75
        * roller_d_mm ** (29.0 / 27.0)
    )


def nominal_life_hours(
    dynamic_C_N: float,
    equivalent_load_P_N: float,
    speed_rpm: float,
    life_exponent: float,
) -> Optional[float]:
    if equivalent_load_P_N <= 0.0 or speed_rpm <= 0.0 or dynamic_C_N <= 0.0:
        return None
    l10_million_rev = (dynamic_C_N / equivalent_load_P_N) ** life_exponent
    return l10_million_rev * 1.0e6 / (60.0 * speed_rpm)


def compute_ratings(
    bearing_type: str,
    roller_d_mm: float,
    roller_length_mm: float,
    element_count: int,
    pitch_d_mm: float,
    contact_angle_deg: float = 0.0,
    radial_load_Fr_N: float = 0.0,
    axial_load_Fa_N: float = 0.0,
    speed_rpm: float = 0.0,
    rows: Optional[int] = None,
) -> Ratings:
    alpha = _contact_angle_rad(bearing_type, contact_angle_deg)
    g = gamma(roller_d_mm, alpha, pitch_d_mm)
    f0 = f0_for(bearing_type, g)
    fc = fc_for(bearing_type, g)
    c0 = static_load_rating(
        bearing_type, roller_d_mm, roller_length_mm, element_count,
        pitch_d_mm, contact_angle_deg, rows=rows,
    )
    cr = dynamic_load_rating(
        bearing_type, roller_d_mm, roller_length_mm, element_count,
        pitch_d_mm, contact_angle_deg, rows=rows,
    )
    p = _life_exponent(bearing_type)
    load = equivalent_load(
        bearing_type,
        radial_load_Fr_N=radial_load_Fr_N,
        axial_load_Fa_N=axial_load_Fa_N,
        static_C0_N=c0,
        contact_angle_deg=contact_angle_deg,
    )
    l10h = nominal_life_hours(cr, load.P_N, speed_rpm, p)
    return Ratings(
        static_C0_N=c0,
        dynamic_C_N=cr,
        life_exponent=p,
        gamma=g,
        f0=f0,
        fc=fc,
        X=load.X,
        Y=load.Y,
        e=load.e,
        P_N=load.P_N,
        L10h=l10h,
    )
