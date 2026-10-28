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

    Für Bohrungen ``d < 10 mm`` (z. B. Miniatur-/Skateboardlager wie 608) wird
    der Bohrungs-Ø nach DIN 623 *direkt* als einstellige Kennzahl angegeben:
    ``"4"`` → 4 mm … ``"9"`` → 9 mm.

    Ab ``d = 10 mm`` gilt das zweistellige Schema: Sonderfälle 00..03 entsprechen
    10/12/15/17 mm; ab 04 gilt ``d = n * 5`` bis Kennzahl 96 (d = 480 mm).
    Größere Lager werden mit ``/d`` angehängt bezeichnet und sind hier nicht
    abgedeckt.
    """
    token = str(code).strip()
    if not token or not token.isascii() or not token.isdigit():
        raise ValueError(f"Ungueltige Bohrungskennzahl: {code!r}")
    if len(token) > 2:
        raise ValueError(f"Bohrungskennzahl muss ein- oder zweistellig sein: {code!r}")

    # Einstellige Kennzahl: Bohrungs-Ø in mm direkt (Miniaturlager, d < 10 mm).
    if len(token) == 1:
        n = int(token)
        if n < 1 or n > 9:
            raise ValueError(f"Einstellige Bohrungskennzahl ausserhalb 1..9: {code}")
        return float(n)
    special = {"00": 10.0, "01": 12.0, "02": 15.0, "03": 17.0}
    if token in special:
        return special[token]
    n = int(token)
    if n < 4 or n > 96:
        raise ValueError(f"Bohrungskennzahl ausserhalb 04..96: {code}")
    return float(n * 5)
