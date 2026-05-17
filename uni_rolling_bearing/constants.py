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
# Hauptreihen (DIN 625, 5412, 720, 635) werden aus den Maßtabellen in
# ``din623.py`` generiert. Nadellager und SG-Reihe bleiben manuell, da sie
# nicht der DIN 623-Codegenerierung folgen.
from . import din623  # noqa: E402

SERIES_PRESETS: Dict[str, Dict[str, Tuple[float, float, float]]] = {
    BALL: din623.build_ball_presets(),
    CYLINDRICAL: din623.build_cylindrical_presets(),
    NEEDLE: {
        "HK0808": (8.0, 12.0, 8.0),
        "HK1010": (10.0, 14.0, 10.0),
        "HK1212": (12.0, 16.0, 12.0),
        "HK1512": (15.0, 21.0, 12.0),
        "HK1612": (16.0, 22.0, 12.0),
        "HK2012": (20.0, 26.0, 12.0),
        "HK2020": (20.0, 26.0, 20.0),
        "HK2516": (25.0, 32.0, 16.0),
        "HK3020": (30.0, 37.0, 20.0),
    },
    TAPERED: din623.build_tapered_presets(),
    SPHERICAL: din623.build_spherical_presets(),
    # U-/V-Rillen-Führungsrollen-Kugellager (SG- bzw. W-Reihe).
    # Hauptmaße orientieren sich an handelsüblichen Katalogwerten der
    # Bishop-Wisecarver "DualVee"-/Misumi "SG"-Familien (d, D, B in mm).
    # Die Rille selbst sitzt im Außenmantel des Außenrings; Innenmaße
    # entsprechen einem Standard-Rillenkugellager.
    VGROOVE: {
        "SG10": (4.0, 13.0, 6.0),
        "SG15": (5.0, 17.0, 8.0),
        "SG20": (6.0, 24.0, 11.0),
        "SG25": (8.0, 30.73, 11.1),
        "SG35": (12.0, 45.72, 15.88),
        "SG66": (15.0, 62.0, 20.0),
    },
}

# Normhinweis, der als Metadatum am erzeugten Assembly gespeichert wird.
NORM_HINTS: Dict[str, str] = {
    BALL: "DIN 625 / ISO 15 (Preset-basiert)",
    CYLINDRICAL: "DIN 5412 / ISO 15 (Preset-basiert)",
    NEEDLE: "DIN 617 / ISO 15 (Preset-basiert)",
    TAPERED: "DIN 720 / ISO 355 (Preset-basiert)",
    SPHERICAL: "DIN 635 / ISO 15 (Preset-basiert)",
    VGROOVE: "Führungsrolle SG/W-Reihe (Hersteller-Katalogwerte)",
}

# Anteil der Lagerbreite, der von der Wälzkörperlänge ausgefüllt wird.
# Empirische Werte, die zu plausibler Optik ohne Kollision mit Borden führen.
ROLLER_LENGTH_RATIO: Dict[str, float] = {
    NEEDLE: 0.98,
    CYLINDRICAL: 0.82,
    TAPERED: 0.90,
    SPHERICAL: 0.85,
}

# Empfohlene Ringstärke als Anteil von (D − d). Praxisorientierte Faustwerte:
# Standardlager bei ≈ 1/6, Nadellager dünnwandig bei ≈ 1/12.
TYPE_RING_THICKNESS_RATIO: Dict[str, float] = {
    BALL: 1.0 / 6.0,
    CYLINDRICAL: 1.0 / 7.0,
    NEEDLE: 1.0 / 12.0,
    TAPERED: 1.0 / 6.0,
    SPHERICAL: 1.0 / 6.0,
    # SG-Führungsrollen sind klein gebaut – gleiche Wandstärke-Faustregel wie
    # bei Standard-Rillenkugellagern, sonst bleibt für die Kugel kein Spalt.
    VGROOVE: 1.0 / 6.0,
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

# Ziel-Umfangsspalt-Faktor pro Typ (relative Lücke zwischen Wälzkörpern auf
# dem Teilkreis). Nadellager sitzen dichter, Kugellager großzügiger.
TYPE_GAP_FACTOR: Dict[str, float] = {
    BALL: 0.12,
    CYLINDRICAL: 0.10,
    NEEDLE: 0.06,
    TAPERED: 0.10,
    SPHERICAL: 0.10,
    VGROOVE: 0.12,
}
