"""Static Bezeichnungen, Lagertypen und Norm-Presets."""

from __future__ import annotations

from typing import Dict, Tuple

# Lagertyp-IDs
BALL = "BALL"
CYLINDRICAL = "CYLINDRICAL"
NEEDLE = "NEEDLE"
TAPERED = "TAPERED"
SPHERICAL = "SPHERICAL"
VGROOVE = "VGROOVE"

BEARING_TYPES = [
    (BALL, "Kugellager", "Rillenkugellager nach DIN 625 / ISO 15"),
    (CYLINDRICAL, "Zylinderrollenlager", "Zylinderrollenlager nach DIN 5412 / ISO 15 Maßreihen"),
    (NEEDLE, "Nadellager", "Nadellager nach DIN 617 / ISO 15 Maßreihen"),
    (TAPERED, "Kegelrollenlager", "Kegelrollenlager nach DIN 720 / ISO 355"),
    (SPHERICAL, "Tonnenlager", "Pendelrollenlager (Tonnenlager) nach DIN 635 / ISO 15"),
    (VGROOVE, "U-Rillen-Kugellager (SG)", "Führungsrollen-Kugellager mit V-/U-Rille am Außenring (SG/W-Reihe)"),
]

PRECISION_CLASSES = [
    ("NORMAL", "Normal", "ISO 492 Normal"),
    ("P6", "P6", "ISO 492 Klasse P6"),
    ("P5", "P5", "ISO 492 Klasse P5"),
    ("P4", "P4", "ISO 492 Klasse P4"),
]

# (d, D, B) in mm – Norm-Presets je Baureihe.
# Werden zur Importzeit aus den JSON-Dateien unter ``data/`` geladen
# (siehe ``norm_engine.load_all_presets``). Eigene Erweiterungen können
# als gleichnamige JSON unter ``<Blender-Scripts>/uni_bearing/`` abgelegt
# werden – sie werden über die Defaults gemerged.
from . import norm_engine  # noqa: E402

SERIES_PRESETS: Dict[str, Dict[str, Tuple[float, float, float]]] = norm_engine.load_all_presets()

# Normhinweis, der als Metadatum am erzeugten Assembly gespeichert wird.
NORM_HINTS: Dict[str, str] = {
    bt: norm_engine.norm_hint_for(bt) or "" for bt in (
        BALL, CYLINDRICAL, NEEDLE, TAPERED, SPHERICAL, VGROOVE,
    )
}

# Anteil der Lagerbreite, der von der Wälzkörperlänge ausgefüllt wird.
# Empirische Werte, die zu plausibler Optik ohne Kollision mit Borden führen.
# Pendelrollenlager sind zweireihig (DIN 635-2) – jede Rolle füllt nur
# rund ein Drittel der Lagerbreite, nicht die ganze Breite.
ROLLER_LENGTH_RATIO: Dict[str, float] = {
    NEEDLE: 0.98,
    CYLINDRICAL: 0.82,
    TAPERED: 0.90,
    SPHERICAL: 0.38,
}

# Empfohlene Ringstärke als Anteil von (D − d). Praxisorientierte Faustwerte:
# Rillenkugellager bei ≈ 1/12 – der Wert wird zusammen mit der Rillen-Formel
# in ``geometry.resolve_geometry`` ausgelegt: ``ring_thickness`` ist die
# Mindestwand zwischen Bohrung und Rillenboden (nicht die Schulterhöhe), die
# Kugel sinkt mit ``f·d_ball`` in die Rille ein. So treffen die Defaults
# reale Maßreihen (6204 → ø7.94 mm).
TYPE_RING_THICKNESS_RATIO: Dict[str, float] = {
    BALL: 1.0 / 12.0,
    CYLINDRICAL: 1.0 / 7.0,
    NEEDLE: 1.0 / 12.0,
    TAPERED: 1.0 / 6.0,
    SPHERICAL: 1.0 / 6.0,
    # SG-Führungsrollen sind Rillenkugellager mit zusätzlicher V-Rille im
    # Außenmantel – dieselbe Wand-Faustregel wie beim Standard-Kugellager.
    VGROOVE: 1.0 / 12.0,
}

# Empfohlener Anteil des nutzbaren Radial-Spalts, den der Wälzkörper-Ø
# einnimmt. Höhere Werte = mehr Tragfähigkeit, weniger Schmierfilmreserve.
# Kugellager: hoher Wert nötig, damit die Rille (groove arc) die Schulter
# tatsächlich schneidet und sichtbar ins Material taucht; reale Rillenkugellager
# füllen den Spalt knapp, der Rest sind Lagerluft + Konformitätsreserve.
TYPE_ROLLER_FILL: Dict[str, float] = {
    BALL: 0.95,
    CYLINDRICAL: 0.78,
    NEEDLE: 0.88,
    TAPERED: 0.62,
    SPHERICAL: 0.70,
    VGROOVE: 0.92,
}
