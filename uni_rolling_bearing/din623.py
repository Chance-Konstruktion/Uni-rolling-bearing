"""DIN 623 / ISO 15 Bezeichnungssystem und Maßreihen-Tabellen.

DIN 623 legt die Bezeichnung von Wälzlagern fest. Die Kurzbezeichnung besteht
aus einer Bauart-Kennziffer, einer Maßreihen-Kennzahl und einer
Bohrungskennzahl. Aus dieser Kennzahl ergibt sich der Bohrungs-Ø ``d`` nach
festen Regeln; Außen-Ø ``D`` und Breite ``B`` folgen aus der Maßreihe nach
ISO 15.

Dieses Modul stellt:

* :func:`bore_code_to_diameter` – DIN 623 Bohrungskennzahl → ``d`` in mm.
* ``DIN625_SERIES`` u. a. – tabellarische Maße ``(D, B)`` je Reihe und
  Bohrungskennzahl.
* :func:`build_presets` – generiert die ``SERIES_PRESETS``-Tabelle aus den
  Reihendaten, sodass neue Größen nur einmal eingetragen werden müssen.
"""

from __future__ import annotations

from typing import Dict, Tuple


def bore_code_to_diameter(code: str) -> float:
    """DIN 623 Bohrungskennzahl → Bohrungs-Ø in mm.

    Sonderfälle 00..03 entsprechen 10/12/15/17 mm; ab 04 gilt ``d = n * 5``
    bis Kennzahl 96 (d = 480 mm). Größere Lager werden mit ``/d`` angehängt
    bezeichnet und sind hier nicht abgedeckt.
    """
    special = {"00": 10.0, "01": 12.0, "02": 15.0, "03": 17.0}
    if code in special:
        return special[code]
    n = int(code)
    if n < 4 or n > 96:
        raise ValueError(f"Bohrungskennzahl ausserhalb 04..96: {code}")
    return float(n * 5)


# ISO 15 / DIN 625-1 – Rillenkugellager.
# Werte (D, B) in mm, Schlüssel = Bohrungskennzahl.
# Quelle: ISO 15 Maßtabellen; gerundet auf Norm-Sollmaße.
DIN625_SERIES: Dict[str, Dict[str, Tuple[float, float]]] = {
    # Reihe 60 (leicht)
    "60": {
        "00": (26.0, 8.0), "01": (28.0, 8.0), "02": (32.0, 9.0),
        "03": (35.0, 10.0), "04": (42.0, 12.0), "05": (47.0, 12.0),
        "06": (55.0, 13.0), "07": (62.0, 14.0), "08": (68.0, 15.0),
        "09": (75.0, 16.0), "10": (80.0, 16.0), "11": (90.0, 18.0),
        "12": (95.0, 18.0), "13": (100.0, 18.0), "14": (110.0, 20.0),
        "15": (115.0, 20.0), "16": (125.0, 22.0), "17": (130.0, 22.0),
        "18": (140.0, 24.0), "19": (145.0, 24.0), "20": (150.0, 24.0),
    },
    # Reihe 62 (mittel)
    "62": {
        "00": (30.0, 9.0), "01": (32.0, 10.0), "02": (35.0, 11.0),
        "03": (40.0, 12.0), "04": (47.0, 14.0), "05": (52.0, 15.0),
        "06": (62.0, 16.0), "07": (72.0, 17.0), "08": (80.0, 18.0),
        "09": (85.0, 19.0), "10": (90.0, 20.0), "11": (100.0, 21.0),
        "12": (110.0, 22.0), "13": (120.0, 23.0), "14": (125.0, 24.0),
        "15": (130.0, 25.0), "16": (140.0, 26.0), "17": (150.0, 28.0),
        "18": (160.0, 30.0), "19": (170.0, 32.0), "20": (180.0, 34.0),
    },
    # Reihe 63 (schwer)
    "63": {
        "00": (35.0, 11.0), "01": (37.0, 12.0), "02": (42.0, 13.0),
        "03": (47.0, 14.0), "04": (52.0, 15.0), "05": (62.0, 17.0),
        "06": (72.0, 19.0), "07": (80.0, 21.0), "08": (90.0, 23.0),
        "09": (100.0, 25.0), "10": (110.0, 27.0), "11": (120.0, 29.0),
        "12": (130.0, 31.0), "13": (140.0, 33.0), "14": (150.0, 35.0),
        "15": (160.0, 37.0), "16": (170.0, 39.0), "17": (180.0, 41.0),
        "18": (190.0, 43.0), "19": (200.0, 45.0), "20": (215.0, 47.0),
    },
    # Reihe 64 (extra schwer) – nur die gängigen kleinen Größen.
    "64": {
        "03": (52.0, 15.0), "04": (60.0, 17.0), "05": (70.0, 20.0),
        "06": (80.0, 21.0), "07": (90.0, 24.0), "08": (100.0, 25.0),
    },
    # Reihe 618 (extra leicht, dünnwandig)
    "618": {
        "04": (37.0, 9.0), "05": (42.0, 9.0), "06": (47.0, 9.0),
        "07": (55.0, 10.0), "08": (62.0, 12.0), "09": (68.0, 12.0),
        "10": (72.0, 12.0), "11": (80.0, 13.0), "12": (85.0, 13.0),
    },
    # Reihe 619 (leicht, schmal)
    "619": {
        "04": (42.0, 10.0), "05": (47.0, 10.0), "06": (55.0, 10.0),
        "07": (62.0, 12.0), "08": (68.0, 12.0), "09": (75.0, 13.0),
        "10": (80.0, 13.0),
    },
}


# Vereinfachte Maßtabelle Zylinderrollenlager NU-Bauart (DIN 5412 Reihe 2/3).
DIN5412_NU_SERIES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "2": {
        "04": (47.0, 14.0), "05": (52.0, 15.0), "06": (62.0, 16.0),
        "07": (72.0, 17.0), "08": (80.0, 18.0), "09": (85.0, 19.0),
        "10": (90.0, 20.0), "11": (100.0, 21.0), "12": (110.0, 22.0),
    },
    "3": {
        "04": (52.0, 15.0), "05": (62.0, 17.0), "06": (72.0, 19.0),
        "07": (80.0, 21.0), "08": (90.0, 23.0), "09": (100.0, 25.0),
        "10": (110.0, 27.0), "11": (120.0, 29.0), "12": (130.0, 31.0),
    },
}


# Kegelrollenlager DIN 720 / ISO 355, Reihen 302 und 303.
# B ist die Innenring-Gesamtbreite T (vereinfacht, da das Modell keine
# getrennte Außenring-Breite C kennt).
DIN720_SERIES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "302": {
        "04": (47.0, 15.25), "05": (52.0, 16.25), "06": (62.0, 17.25),
        "07": (72.0, 18.25), "08": (80.0, 19.75), "09": (85.0, 20.75),
        "10": (90.0, 21.75), "11": (100.0, 22.75), "12": (110.0, 23.75),
    },
    "303": {
        "04": (52.0, 16.25), "05": (62.0, 18.25), "06": (72.0, 20.75),
        "07": (80.0, 22.75), "08": (90.0, 25.25), "09": (100.0, 27.25),
        "10": (110.0, 29.25), "11": (120.0, 31.5), "12": (130.0, 33.5),
    },
}


# Pendelrollenlager DIN 635, Reihen 222 und 223.
DIN635_SERIES: Dict[str, Dict[str, Tuple[float, float]]] = {
    "222": {
        "06": (62.0, 20.0), "07": (72.0, 23.0), "08": (80.0, 23.0),
        "09": (85.0, 23.0), "10": (90.0, 23.0), "11": (100.0, 25.0),
        "12": (110.0, 28.0), "13": (120.0, 31.0),
    },
    "223": {
        "06": (72.0, 27.0), "07": (80.0, 31.0), "08": (90.0, 33.0),
        "09": (100.0, 36.0), "10": (110.0, 40.0), "11": (120.0, 43.0),
        "12": (130.0, 46.0),
    },
}


def designation(type_prefix: str, series: str, bore_code: str) -> str:
    """DIN 623-Kurzbezeichnung aus Bauart, Maßreihe und Bohrungskennzahl.

    Für Rillenkugellager (``type_prefix='6'``, ``series='02'``) ergibt z. B.
    Bohrungskennzahl ``'04'`` die Bezeichnung ``'6204'``. Die Maßreihe wird
    ohne führende Bauart-Stelle übergeben, die Bauart-Kennziffer separat.
    """
    return f"{type_prefix}{series.lstrip('0') or '0'}{bore_code}"


def _expand(prefix: str, table: Dict[str, Dict[str, Tuple[float, float]]],
            series_to_prefix: Dict[str, str] | None = None
            ) -> Dict[str, Tuple[float, float, float]]:
    """Wandelt eine Maßreihentabelle in einen ``code → (d, D, B)``-Dict um."""
    result: Dict[str, Tuple[float, float, float]] = {}
    for series, entries in table.items():
        for bore_code, (outer, width) in entries.items():
            d = bore_code_to_diameter(bore_code)
            if series_to_prefix is not None:
                code = f"{series_to_prefix[series]}{bore_code}"
            else:
                code = f"{prefix}{series}{bore_code}"
            result[code] = (d, outer, width)
    return result


def build_ball_presets() -> Dict[str, Tuple[float, float, float]]:
    """DIN 625 → ``{code: (d, D, B)}`` für alle bekannten Größen."""
    # Reihe 60/62/63/64 → Codes 60xx, 62xx, 63xx, 64xx.
    # Reihe 618/619 → Codes 618xx, 619xx (Bauart-Stelle entfällt im Code).
    result: Dict[str, Tuple[float, float, float]] = {}
    for series, entries in DIN625_SERIES.items():
        for bore_code, (outer, width) in entries.items():
            d = bore_code_to_diameter(bore_code)
            code = f"{series}{bore_code}" if series.startswith("6") else f"6{series}{bore_code}"
            result[code] = (d, outer, width)
    return result


def build_cylindrical_presets() -> Dict[str, Tuple[float, float, float]]:
    return _expand("NU", DIN5412_NU_SERIES)


def build_tapered_presets() -> Dict[str, Tuple[float, float, float]]:
    return _expand("", DIN720_SERIES)


def build_spherical_presets() -> Dict[str, Tuple[float, float, float]]:
    return _expand("", DIN635_SERIES)
