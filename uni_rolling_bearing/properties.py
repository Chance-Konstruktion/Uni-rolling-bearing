"""PropertyGroup für Lagerparameter im N-Panel.

Alle ``description``-Texte werden in Blender als Tooltip angezeigt, wenn der
Mauszeiger über das jeweilige Feld bewegt wird. Sie sollen ausreichen, um die
Funktion eines Feldes auch ohne Norm-Vorwissen zu verstehen.
"""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty

from .constants import BEARING_TYPES, PRECISION_CLASSES, SERIES_PRESETS


def _series_items(self, _context):
    """Dynamische EnumItems abhängig vom gewählten Lagertyp."""
    presets = SERIES_PRESETS.get(self.bearing_type, {})
    if not presets:
        return [("CUSTOM", "Custom", "Benutzerdefiniert")]
    return [(code, code, f"Preset {code}") for code in presets]


class UNI_Bearing_Properties(bpy.types.PropertyGroup):
    bearing_type: EnumProperty(
        name="Lagertyp",
        description=(
            "Auswahl der Lagerbauform. Bestimmt Wälzkörperform (Kugel, Zylinder, "
            "Nadel, Kegel, Tonne), die anwendbaren Norm-Presets und – bei "
            "Kegelrollenlagern – die Verfügbarkeit des Kontaktwinkels."
        ),
        items=BEARING_TYPES,
        default="BALL",
    )
    series_code: EnumProperty(
        name="Normreihe",
        description=(
            "Konkretes Norm-Preset (z. B. '6204' = Kugellager DIN 625, "
            "Bohrung 20 mm, Außen-Ø 47 mm, Breite 14 mm). Liefert ausschließlich "
            "Hauptmaße – Wälzkörper-Ø und Anzahl werden über 'Norm-Preset "
            "anwenden' geometrisch passend abgeleitet."
        ),
        items=_series_items,
    )

    use_preset: BoolProperty(
        name="Norm-Preset verwenden",
        description=(
            "Wenn aktiv, kann ein Reihen-Preset gewählt und übernommen werden. "
            "Deaktivieren, um d/D/B vollständig manuell einzugeben."
        ),
        default=True,
    )
    bore_diameter: FloatProperty(
        name="Innendurchmesser d [mm]",
        description=(
            "Bohrungs-Ø des Lagers (Wellensitz). Entspricht 'd' nach DIN ISO 15. "
            "Muss kleiner als der Außen-Ø D sein."
        ),
        default=20.0,
        min=1.0,
    )
    outer_diameter: FloatProperty(
        name="Außendurchmesser D [mm]",
        description=(
            "Außen-Ø des Lagers (Gehäusesitz). Entspricht 'D' nach DIN ISO 15. "
            "Die Differenz D−d steht für Ringe + Wälzkörper + Lagerluft zur "
            "Verfügung."
        ),
        default=47.0,
        min=2.0,
    )
    width: FloatProperty(
        name="Breite B [mm]",
        description=(
            "Lagerbreite in Achsrichtung ('B' nach DIN ISO 15). Bestimmt die "
            "Länge zylindrischer/kegliger Rollen und die maximale Endplatten-"
            "Position des Käfigs."
        ),
        default=14.0,
        min=1.0,
    )

    ring_thickness: FloatProperty(
        name="Ringstärke [mm]",
        description=(
            "Radiale Wandstärke je Ring (Innen- und Außenring identisch). "
            "Praxiswert ≈ 1/6 von (D−d). Größere Werte = stabilere Ringe, "
            "aber kleinerer Wälzkörperraum."
        ),
        default=4.0,
        min=0.5,
    )
    roller_diameter: FloatProperty(
        name="Wälzkörper-Ø [mm]",
        description=(
            "Durchmesser von Kugel/Zylinder/Nadel/Kegelmittel/Tonnenmittel. "
            "Wird vom Resolver auf den nutzbaren Laufbahnspalt begrenzt; "
            "Auto-Fit kürzt zu große Werte automatisch."
        ),
        default=7.0,
        min=0.5,
    )
    element_count: IntProperty(
        name="Wälzkörper Anzahl",
        description=(
            "Anzahl der Wälzkörper auf dem Teilkreis. Wird automatisch nach "
            "Umfang und 'Umfangsspalt-Faktor' begrenzt, damit sich die "
            "Wälzkörper nicht überlappen."
        ),
        default=10,
        min=3,
        max=256,
    )
    gap_factor: FloatProperty(
        name="Umfangsspalt-Faktor",
        description=(
            "Relativer Mindestabstand zwischen benachbarten Wälzkörpern auf "
            "dem Teilkreis (0.10 ≈ 10 % zusätzliche Lücke pro Wälzkörper-Ø). "
            "Höhere Werte = mehr Spiel, aber weniger Wälzkörper passen."
        ),
        default=0.10,
        min=0.0,
        max=0.8,
    )
    auto_fit: BoolProperty(
        name="Auto-Fit aktiv",
        description=(
            "Wenn aktiv, werden zu großer Wälzkörper-Ø und zu hohe Anzahl "
            "stillschweigend auf das geometrisch zulässige Maximum gekürzt. "
            "Deaktivieren, um stattdessen Fehler zu sehen."
        ),
        default=True,
    )

    use_cage: BoolProperty(
        name="Käfig erzeugen",
        description=(
            "Erzeugt einen einfachen Leiter-Käfig: zwei axiale Endplatten "
            "zwischen Wälzkörperende und Lagerstirn, dazwischen tangentiale "
            "Webs in den Lücken. Wird bei zu wenig Bauraum übersprungen."
        ),
        default=False,
    )

    contact_angle_deg: FloatProperty(
        name="Kontaktwinkel α [°]",
        description=(
            "Nur Kegelrollenlager: Winkel zwischen Wälzkörperachse und "
            "Lagerachse. Alle Rollenachsen treffen sich auf der Lagerachse "
            "in einem gemeinsamen Apex (DIN 720 / ISO 355). Typisch 10–18° "
            "für Standardreihen, 25–30° für steile Reihen."
        ),
        default=14.0,
        min=0.0,
        max=45.0,
        soft_max=30.0,
    )

    segments: IntProperty(
        name="Auflösung Segmente",
        description=(
            "Anzahl Umfangssegmente für Ringe und runde Wälzkörper. Mehr "
            "Segmente = glattere Optik, aber größere Mesh-Datei. 48 ist ein "
            "guter Kompromiss; ≥96 für Renderings."
        ),
        default=48,
        min=12,
        max=256,
    )
    precision_class: EnumProperty(
        name="Toleranzklasse",
        description=(
            "Toleranzklasse nach ISO 492 / DIN 620. Wird derzeit nur als "
            "Metadatum am Bearing-Empty hinterlegt; künftige Versionen sollen "
            "die Maßtoleranzen direkt aus dieser Auswahl ableiten."
        ),
        items=PRECISION_CLASSES,
        default="NORMAL",
    )
    radial_clearance: FloatProperty(
        name="Radiale Lagerluft [mm]",
        description=(
            "Spiel zwischen Wälzkörper und Laufbahnen in radialer Richtung "
            "(unbelastet). Wird beidseitig je zur Hälfte vom Spalt abgezogen "
            "(orientiert an DIN 620 / ISO 5753 Lagerluftgruppe C0)."
        ),
        default=0.02,
        min=0.0,
    )
