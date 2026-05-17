"""Tragzahlen und Lebensdauer nach ISO 76 / ISO 281.

Berechnung ist bewusst als ingenieurmäßige Näherung ausgeführt: die
ISO-Tabellen für ``f0`` (statisch) und ``fc`` (dynamisch) hängen von
Innengeometrie (Konformität, Hüllkurvenverhältnis γ = Dw·cosα / dm) ab,
die das Mesh-Modell nicht vollständig auflöst. Für eine plausible Anzeige
am erzeugten Lager-Empty werden gemittelte Werte aus den ISO-Tabellen
verwendet; das Ergebnis liegt typischerweise innerhalb von ±15 % der
Hersteller-Katalogwerte.

Alle Eingaben in mm, Ausgaben in Newton bzw. Stunden (L10h).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional

from . import constants


_F0_BALL = 14.7
_F0_ROLLER = 44.0
_FC_BALL = 70.0
_FC_ROLLER = 88.0
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


@dataclass(frozen=True)
class Ratings:
    static_C0_N: float
    dynamic_C_N: float
    life_exponent: float
    L10h: Optional[float] = None


def static_load_rating(
    bearing_type: str,
    roller_d_mm: float,
    roller_length_mm: float,
    element_count: int,
    contact_angle_deg: float = 0.0,
) -> float:
    alpha = _contact_angle_rad(bearing_type, contact_angle_deg)
    i = _rows(bearing_type)
    if element_count <= 0 or roller_d_mm <= 0.0:
        return 0.0
    if _is_ball(bearing_type):
        return _F0_BALL * i * element_count * roller_d_mm**2 * math.cos(alpha)
    if roller_length_mm <= 0.0:
        return 0.0
    return (
        _F0_ROLLER * i * element_count * roller_length_mm * roller_d_mm * math.cos(alpha)
    )


def dynamic_load_rating(
    bearing_type: str,
    roller_d_mm: float,
    roller_length_mm: float,
    element_count: int,
    contact_angle_deg: float = 0.0,
) -> float:
    alpha = _contact_angle_rad(bearing_type, contact_angle_deg)
    i = _rows(bearing_type)
    if element_count <= 0 or roller_d_mm <= 0.0:
        return 0.0
    if _is_ball(bearing_type):
        return (
            _BM_BALL
            * _FC_BALL
            * (i * math.cos(alpha)) ** 0.7
            * element_count ** (2.0 / 3.0)
            * roller_d_mm ** 1.8
        )
    if roller_length_mm <= 0.0:
        return 0.0
    return (
        _BM_ROLLER
        * _FC_ROLLER
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
    contact_angle_deg: float = 0.0,
    equivalent_load_P_N: float = 0.0,
    speed_rpm: float = 0.0,
) -> Ratings:
    c0 = static_load_rating(
        bearing_type, roller_d_mm, roller_length_mm, element_count, contact_angle_deg
    )
    cr = dynamic_load_rating(
        bearing_type, roller_d_mm, roller_length_mm, element_count, contact_angle_deg
    )
    p = _life_exponent(bearing_type)
    l10h = nominal_life_hours(cr, equivalent_load_P_N, speed_rpm, p)
    return Ratings(static_C0_N=c0, dynamic_C_N=cr, life_exponent=p, L10h=l10h)
