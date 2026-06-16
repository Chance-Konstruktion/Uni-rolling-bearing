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
# Beim Tonnen-/Pendelrollenlager ist dies die EINREIHIGE Tonnenlänge
# (Default-Bauart). Für die zweireihige Variante halbiert der Operator den
# Wert über ``SPHERICAL_TWO_ROW_LENGTH_FACTOR``, damit zwei Reihen plus
# Mittelbord in die Lagerbreite passen.
ROLLER_LENGTH_RATIO: Dict[str, float] = {
    NEEDLE: 0.98,
    CYLINDRICAL: 0.82,
    # Kegelrollen werden um α−β gekippt; eine zu lange Rolle ragt dann über die
    # Stirnflächen / den großen Bord hinaus. 0.78 lässt nach dem Kippen Luft.
    TAPERED: 0.78,
    SPHERICAL: 0.58,
}

# Längenfaktor je Reihe bei der zweireihigen Pendelrollen-Variante (relativ zur
# einreihigen Tonnenlänge): zwei Reihen + Mittelbord teilen sich die Breite.
# 0.70 hält die Tonnen noch tonnenförmig (Länge ≳ Ø), ohne dass sich die
# beiden Reihen am Mittelband überlappen.
SPHERICAL_TWO_ROW_LENGTH_FACTOR = 0.70

# Empfohlene Ringstärke als Anteil von (D − d). Praxisorientierte Faustwerte.
#
# Bei Rillenkugellagern ist ``ring_thickness`` die radiale Wand von der Bohrung
# (bzw. dem Außen-Ø) bis zur **Schulter** (dem zylindrischen Laufbahnsteg neben
# der Rille). Die Kugel überspannt anschließend den Schulterabstand PLUS die
# innere und äußere Rillentiefe (DIN-625-Rillenformel, siehe
# ``geometry.ball_diameter_from_groove``). Damit die Schultern – und über die
# Rillenformel die Kugel – reale Maßreihen treffen (6204 → ø≈7.9 mm), sitzt die
# Schulterwand bei ≈ 2/15·(D−d); die frühere 1/12-Wand legte die „Schulter“
# faktisch auf den Rillenboden und ließ die Kugel zwischen den Schultern
# schweben (zu klein/lose wirkend).
TYPE_RING_THICKNESS_RATIO: Dict[str, float] = {
    BALL: 2.0 / 15.0,
    CYLINDRICAL: 1.0 / 7.0,
    NEEDLE: 1.0 / 12.0,
    # Kegel- und Pendelrollenlager haben vergleichsweise dünne Ringe und
    # entsprechend große Wälzkörper. Ein Anteil von 1/9 (statt früher 1/6)
    # weitet den Laufbahnspalt so, dass die Rollenanzahl in den realen
    # Katalogbereich fällt (z. B. 30206 → 17 Rollen statt ~40).
    TAPERED: 1.0 / 9.0,
    SPHERICAL: 1.0 / 9.0,
    # SG-Führungsrollen sind Rillenkugellager mit zusätzlicher V-Rille im
    # Außenmantel – dieselbe Schulterwand-Faustregel wie beim Standard-Kugellager.
    VGROOVE: 2.0 / 15.0,
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
    # Kegel-/Pendelrollen füllen den (durch die dünneren Ringe verbreiterten)
    # Laufbahnspalt fast vollständig – große Rollen, wenige Stück, wie im Katalog.
    # Kegelrollen reichen damit (mittig auf dem Teilkreis) bis an beide
    # Laufbahnen, statt mit Spiel in der Mitte zu schweben.
    TAPERED: 0.94,
    SPHERICAL: 0.86,
    VGROOVE: 0.92,
}
