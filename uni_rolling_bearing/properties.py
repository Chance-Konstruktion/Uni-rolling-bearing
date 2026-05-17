"""PropertyGroup für Lagerparameter im N-Panel.

Alle ``description``-Texte werden in Blender als Tooltip angezeigt, wenn der
Mauszeiger über das jeweilige Feld bewegt wird. Sie sollen ausreichen, um die
Funktion eines Feldes auch ohne Norm-Vorwissen zu verstehen.
"""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty

from .constants import BEARING_TYPES, PRECISION_CLASSES, SERIES_PRESETS
from .fits import LOAD_CASES
from .tolerances import TOLERANCE_POSITIONS


def _series_items(self, _context):
    """Dynamische EnumItems abhängig vom gewählten Lagertyp."""
    presets = SERIES_PRESETS.get(self.bearing_type, {})
    if not presets:
        return [("CUSTOM", "Custom", "Benutzerdefiniert")]
    return [(code, code, f"Preset {code}") for code in presets]


def _on_dimension_changed(self, _context):
    """Wenn 'Auto-Berechnen live' aktiv ist, Ringstärke/Roller/Anzahl
    automatisch aus den aktuellen Hauptmaßen ableiten."""
    if not getattr(self, "auto_recompute", False):
        return
    # Lazy-Import vermeidet Zyklus, da operators.py auf properties.py via
    # bpy.types.Scene zugreift.
    from .operators import apply_suggested_defaults
    apply_suggested_defaults(self)


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
        update=_on_dimension_changed,
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
        update=_on_dimension_changed,
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
        update=_on_dimension_changed,
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
    auto_recompute: BoolProperty(
        name="Auto-Berechnen live",
        description=(
            "Wenn aktiv, werden Ringstärke, Wälzkörper-Ø und Anzahl bei jeder "
            "Änderung von d, D oder Lagertyp automatisch neu aus typabhängigen "
            "Faustformeln (Industriewerte) berechnet. Deaktivieren, um nur "
            "manuell über den 'Auto-Berechnen'-Button zu rechnen."
        ),
        default=False,
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
    cage_style: EnumProperty(
        name="Käfig-Bauart",
        description=(
            "Bauart des Käfigs. 'Auto' wählt Pocket-Sleeve und fällt bei "
            "Boolean-Problemen auf den Leiter-Käfig zurück. 'Ribbon' erzeugt "
            "zwei genietete Halbringe wie ein klassischer Pressblech-Käfig."
        ),
        items=[
            ("AUTO", "Auto", "Pocket-Sleeve, Fallback Leiter"),
            ("POCKET", "Sleeve (Pocket)", "Einteiliger Sleeve-Käfig mit Boolean-Pockets"),
            ("RIBBON", "Ribbon (genietet)", "Zwei genietete Halbringe, Pressblech-Stil"),
            ("LADDER", "Leiter", "Zwei Endplatten + tangentiale Webs"),
        ],
        default="AUTO",
    )
    cage_material: EnumProperty(
        name="Käfig-Werkstoff",
        description=(
            "Werkstoff des Käfigs. Wird ausschließlich als Metadatum am "
            "Bearing-Empty hinterlegt (Stahlblech/Messing/Polymer); die "
            "Geometrie selbst hängt nicht vom Werkstoff ab."
        ),
        items=[
            ("STEEL", "Stahlblech", "Stahlblech-Käfig (Standard, geprägt)"),
            ("BRASS", "Messing", "Massiv-Messing-Käfig (höhere Drehzahlen)"),
            ("POLYMER", "Polymer", "Polyamid/PA66-Käfig (leise, leicht)"),
        ],
        default="STEEL",
    )
    pocket_clearance_mm: FloatProperty(
        name="Pocket-Spiel [mm]",
        description=(
            "Radiales Spiel zwischen Wälzkörper und Pocket-Wand des Sleeve-"
            "Käfigs. Größere Werte = sauberer Boolean-Schnitt, aber spürbar "
            "loseres Pocket. Reale Käfige liegen bei 0.05–0.30 mm."
        ),
        default=0.20,
        min=0.0,
        soft_max=1.0,
    )

    vgroove_depth_mm: FloatProperty(
        name="V-Rillen-Tiefe [mm]",
        description=(
            "Nur U-Rillen-Kugellager (SG-Reihe): radiale Tiefe der V-Rille im "
            "Außenmantel des Außenrings. 0 = automatisch (≈35 % der Außenring-"
            "Wandstärke). Wird auf den verfügbaren Bauraum begrenzt."
        ),
        default=0.0,
        min=0.0,
        soft_max=10.0,
    )
    vgroove_half_angle_deg: FloatProperty(
        name="V-Rillen-Halbwinkel [°]",
        description=(
            "Nur U-Rillen-Kugellager (SG-Reihe): Halber Öffnungswinkel der V-"
            "Flanke. 45° entspricht der klassischen 90°-V-Rille; kleinere Werte "
            "ergeben eine schmalere/spitzere Rille (Annäherung an U-Form)."
        ),
        default=45.0,
        min=5.0,
        max=80.0,
    )

    groove_conformity_inner: FloatProperty(
        name="Konformität f_i (Innenring)",
        description=(
            "Nur Kugellager (Standard und SG-Reihe): Verhältnis Rillenradius "
            "zu Kugel-Ø am Innenring (f_i = r_groove / d_ball). Reale Lager "
            "liegen bei 0.515–0.535 (engerer Bogen = höhere Tragzahl, mehr "
            "Reibung). Default 0.58 ist visualisierungsoptimiert."
        ),
        default=0.58,
        min=0.51,
        max=0.70,
        precision=3,
    )
    groove_conformity_outer: FloatProperty(
        name="Konformität f_o (Außenring)",
        description=(
            "Nur Kugellager (Standard und SG-Reihe): Verhältnis Rillenradius "
            "zu Kugel-Ø am Außenring (f_o = r_groove / d_ball). Traditionell "
            "etwas größer als f_i. Default 0.60."
        ),
        default=0.60,
        min=0.51,
        max=0.70,
        precision=3,
    )

    bearing_chamfer_mm: FloatProperty(
        name="Kantenfase r_s [mm]",
        description=(
            "Nur Kugellager (Standard und SG-Reihe): 45°-Fase an Bohrungs- "
            "und Außenring-Kanten nach DIN 620 / ISO 582. Typische Werte: "
            "0.15 (SG10), 0.3 (kleine Lager), 0.6 (6204), 1.0 (6306), "
            "1.5+ (große Lager). 0 = scharfe Kante. Wird bei zu wenig "
            "Bauraum automatisch auf einen sicheren Wert gekürzt."
        ),
        default=0.30,
        min=0.0,
        soft_max=3.0,
        precision=2,
    )

    tapered_flange_height_mm: FloatProperty(
        name="Bord-Höhe Innenring [mm]",
        description=(
            "Nur Kegelrollenlager: radiale Höhe des Bordes (Rib) an der "
            "großen Stirnseite des Innenrings (DIN 720 / ISO 355). Hält die "
            "Kegelrollen axial. 0 = ohne Bord. Wird auf den verbleibenden "
            "Bauraum bis zur Außenlaufbahn begrenzt."
        ),
        default=1.0,
        min=0.0,
        soft_max=5.0,
    )

    spherical_contact_angle_deg: FloatProperty(
        name="Pendel-Kontaktwinkel α [°]",
        description=(
            "Nur Pendelrollenlager: Kontaktwinkel der beiden Rollenreihen "
            "(Rollenachse ↔ Lagerachse, DIN 635-2). Typische Werte 8–15° für "
            "die 222xx-Reihe, 18–25° für die 223xx-Reihe. Steuert die axiale "
            "Tragfähigkeit und den Abstand der beiden Laufbahnen am Innenring."
        ),
        default=10.0,
        min=0.0,
        max=30.0,
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
            "Toleranzklasse nach ISO 492 / DIN 620. Verschiebt die effektiven "
            "Hauptmaße d, D und B innerhalb der zugehörigen Toleranzfenster "
            "(NORMAL: voll, P6: 70 %, P5: 50 %, P4: 30 %). Die Verschiebungen "
            "fließen direkt in das erzeugte Mesh ein und werden als µm-"
            "Abweichung am Bearing-Empty hinterlegt."
        ),
        items=PRECISION_CLASSES,
        default="NORMAL",
    )
    tolerance_position: EnumProperty(
        name="Toleranzlage",
        description=(
            "Lage innerhalb des Toleranzfensters: Oberes Maß entspricht dem "
            "Nennmaß (keine Abweichung), Mittenmaß rechnet mit der halben "
            "unteren Abweichung, Unteres Maß mit der vollen unteren Abweichung "
            "(Worst-Case-Verkleinerung von d, D, B)."
        ),
        items=TOLERANCE_POSITIONS,
        default="MEAN",
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
    equivalent_load_p_n: FloatProperty(
        name="Äquivalente Last P [N]",
        description=(
            "Dynamisch äquivalente radiale Belastung P für die "
            "L10-Lebensdauer nach ISO 281. 0 = Lebensdauer nicht berechnen."
        ),
        default=0.0,
        min=0.0,
    )
    speed_rpm: FloatProperty(
        name="Drehzahl n [1/min]",
        description=(
            "Betriebsdrehzahl für die nominelle Lebensdauer L10h nach "
            "ISO 281. 0 = nicht berechnen."
        ),
        default=0.0,
        min=0.0,
    )
    load_case: EnumProperty(
        name="Belastungsfall (DIN 5418)",
        description=(
            "Lastfall für die Passungs-Empfehlung an Welle und "
            "Gehäusebohrung nach DIN 5418."
        ),
        items=LOAD_CASES,
        default="INNER_ROT_NORMAL",
    )
