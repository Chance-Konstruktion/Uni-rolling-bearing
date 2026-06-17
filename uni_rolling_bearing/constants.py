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
    # Zylinderrollenlager: 1/8 (statt 1/7) macht die Ringe etwas dünner, damit
    # die Rolle den Laufbahnspalt katalognah füllt (NU206 → ø≈7.5 mm statt ~5.3 mm,
    # vorher nur ~33 % des Radialbands).
    CYLINDRICAL: 1.0 / 8.0,
    NEEDLE: 1.0 / 12.0,
    # Kegel- und Pendelrollenlager haben vergleichsweise dünne Ringe und
    # entsprechend große Wälzkörper. 1/10 (statt früher 1/6 → 1/9) macht die
    # Kegelrollen sichtbar größer (≈ 57 % statt 53 % des Radialbands), ohne die
    # Rollenzahl aus dem Katalogbereich zu drücken; die Kegelrolle wird zusätzlich
    # über den Kontaktwinkel korrekt an die Cup-Laufbahn gesetzt
    # (``geometry.tapered_roller_diameter``).
    TAPERED: 1.0 / 10.0,
    SPHERICAL: 1.0 / 9.0,
    # SG-Führungsrollen sind Rillenkugellager mit zusätzlicher V-Rille im
    # Außenmantel – dieselbe Schulterwand-Faustregel wie beim Standard-Kugellager.
    VGROOVE: 2.0 / 15.0,
}

# Empfohlener Anteil des nutzbaren Radial-Spalts, den der Wälzkörper-Ø
# einnimmt. Rollen (Zylinder/Nadel/Tonne) sitzen ohne Rille direkt zwischen den
# Laufbahnen und sollen den Spalt fast vollständig füllen (snug, kein Schweben);
# der Rest ist Lagerluft + kleine Reserve. (Für Kugeln greift stattdessen die
# Rillenformel, für Kegelrollen der cos-α-Faktor – beide ignorieren diesen Wert.)
TYPE_ROLLER_FILL: Dict[str, float] = {
    BALL: 0.95,
    # 0.94 (statt 0.78): die Zylinderrolle füllt den Laufbahnspalt nahezu ganz
    # und schwebt nicht mehr mit großem Spiel zwischen den Schultern.
    CYLINDRICAL: 0.94,
    # 0.94 (statt 0.88): Nadeln liegen satt zwischen den Laufbahnen.
    NEEDLE: 0.94,
    TAPERED: 0.94,
    # 0.90 (statt 0.86): etwas größere Tonnenrolle, satter Sitz in der Mulde.
    SPHERICAL: 0.90,
    VGROOVE: 0.92,
}

# Umfangs-Spaltfaktor für die *vorgeschlagene* Wälzkörperzahl je Lagertyp.
# Reale Lager packen den Teilkreis nicht dichtest (Käfigstege!) – ein typgerechter
# Zusatzspalt liefert katalognahe Stückzahlen, statt den Umfang mit zu vielen
# Wälzkörpern zu füllen. Fehlt ein Eintrag, gilt der UI-``gap_factor``. (Der
# Resolver deckelt weiterhin über ``gap_factor``; dieser Wert steuert nur den
# Default-Vorschlag.)
TYPE_SUGGEST_PITCH_GAP: Dict[str, float] = {
    BALL: 0.55,        # 6204 → 8 Kugeln
    VGROOVE: 0.55,
    CYLINDRICAL: 0.45,  # NU206 → ~13 Rollen
    SPHERICAL: 0.20,    # 22210 → ~18, 22310 → ~13 je Reihe
}
