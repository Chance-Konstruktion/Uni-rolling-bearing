"""DIN 623 / ISO 15 Bezeichnungssystem.

DIN 623 legt die Bezeichnung von Wälzlagern fest. Die Kurzbezeichnung besteht
aus einer Bauart-Kennziffer, einer Maßreihen-Kennzahl und einer
Bohrungskennzahl. Aus dieser Kennzahl ergibt sich der Bohrungs-Ø ``d`` nach
festen Regeln; Außen-Ø ``D`` und Breite ``B`` folgen aus der Maßreihe nach
ISO 15.

Die Maßreihen-Tabellen selbst liegen seit v0.16 als JSON-Dateien unter
``data/`` und werden von :mod:`norm_engine` geladen. Dieses Modul stellt
daher nur noch die reine Bohrungskennzahl-Logik bereit:

* :func:`bore_code_to_diameter` – DIN 623 Bohrungskennzahl → ``d`` in mm.
"""

from __future__ import annotations


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
