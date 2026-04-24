"""Static Bezeichnungen, Lagertypen und Norm-Presets."""

from __future__ import annotations

from typing import Dict, Tuple

# Lagertyp-IDs
BALL = "BALL"
CYLINDRICAL = "CYLINDRICAL"
NEEDLE = "NEEDLE"
TAPERED = "TAPERED"
SPHERICAL = "SPHERICAL"

BEARING_TYPES = [
    (BALL, "Kugellager", "Rillenkugellager nach DIN 625 / ISO 15"),
    (CYLINDRICAL, "Zylinderrollenlager", "Zylinderrollenlager nach DIN 5412 / ISO 15 Maßreihen"),
    (NEEDLE, "Nadellager", "Nadellager nach DIN 617 / ISO 15 Maßreihen"),
    (TAPERED, "Kegelrollenlager", "Kegelrollenlager nach DIN 720 / ISO 355"),
    (SPHERICAL, "Tonnenlager", "Pendelrollenlager (Tonnenlager) nach DIN 635 / ISO 15"),
]

PRECISION_CLASSES = [
    ("NORMAL", "Normal", "ISO 492 Normal"),
    ("P6", "P6", "ISO 492 Klasse P6"),
    ("P5", "P5", "ISO 492 Klasse P5"),
    ("P4", "P4", "ISO 492 Klasse P4"),
]

# (d, D, B) in mm – praxisnahe Startwerte je Baureihe.
SERIES_PRESETS: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    BALL: {
        "6000": (10.0, 26.0, 8.0),
        "6204": (20.0, 47.0, 14.0),
        "6306": (30.0, 72.0, 19.0),
    },
    CYLINDRICAL: {
        "NU204": (20.0, 47.0, 14.0),
        "NU306": (30.0, 72.0, 19.0),
    },
    NEEDLE: {
        "HK1010": (10.0, 14.0, 10.0),
        "HK2020": (20.0, 26.0, 20.0),
    },
    TAPERED: {
        "30204": (20.0, 47.0, 15.25),
        "30206": (30.0, 62.0, 17.25),
    },
    SPHERICAL: {
        "22206": (30.0, 62.0, 20.0),
        "22210": (50.0, 90.0, 23.0),
    },
}

# Normhinweis, der als Metadatum am erzeugten Assembly gespeichert wird.
NORM_HINTS: Dict[str, str] = {
    BALL: "DIN 625 / ISO 15 (Preset-basiert)",
    CYLINDRICAL: "DIN 5412 / ISO 15 (Preset-basiert)",
    NEEDLE: "DIN 617 / ISO 15 (Preset-basiert)",
    TAPERED: "DIN 720 / ISO 355 (Preset-basiert)",
    SPHERICAL: "DIN 635 / ISO 15 (Preset-basiert)",
}

# Anteil der Lagerbreite, der von der Wälzkörperlänge ausgefüllt wird.
# Empirische Werte, die zu plausibler Optik ohne Kollision mit Borden führen.
ROLLER_LENGTH_RATIO: Dict[str, float] = {
    NEEDLE: 0.98,
    CYLINDRICAL: 0.82,
    TAPERED: 0.90,
    SPHERICAL: 0.85,
}
