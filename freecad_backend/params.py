"""Host-freie Parameter-Datenklasse für den FreeCAD-Frontend.

Spiegelt 1:1 die Felder der Blender-``UNI_Bearing_Properties`` wider, ohne
``bpy`` zu importieren. Beide Frontends (Blender-PropertyGroup und FreeCAD-
``Part::FeaturePython``-Proxy) füllen dieselben Werte und reichen sie an den
geteilten Geometrie-Kern weiter. So bleibt die Logik testbar – ganz ohne
laufendes Blender oder FreeCAD.
"""

from __future__ import annotations

from dataclasses import dataclass

# Der Kern liegt im Schwester-Paket ``uni_rolling_bearing``. Der Import wird über
# den ``sys.path``-Bootstrap in ``InitGui.py`` bzw. den Tests sichergestellt.
from uni_rolling_bearing import constants
from uni_rolling_bearing.geometry import (
    DEFAULT_TAPERED_CONTACT_ANGLE_DEG,
    suggest_defaults,
)


@dataclass
class BearingParams:
    """Alle UI-Parameter eines Wälzlagers (Werte in mm / Stück / Grad).

    Die Defaults entsprechen den Blender-Property-Defaults, damit ein frisch
    angelegtes FreeCAD-Objekt dasselbe Beispiellager (6204-artig) erzeugt.
    """

    bearing_type: str = constants.BALL

    # Hauptmaße
    bore_diameter: float = 20.0
    outer_diameter: float = 47.0
    width: float = 14.0

    # Wälzkörper / Ring
    ring_thickness: float = 4.0
    roller_diameter: float = 7.0
    element_count: int = 10

    # Auslegung
    gap_factor: float = 0.10
    auto_fit: bool = True
    radial_clearance: float = 0.02

    # Toleranzen (ISO 492)
    precision_class: str = "NORMAL"
    tolerance_position: str = "MEAN"

    # Tragzahlen & Lebensdauer (ISO 281) / Passungen (DIN 5418)
    radial_load_fr_n: float = 0.0
    axial_load_fa_n: float = 0.0
    speed_rpm: float = 0.0
    load_case: str = "INNER_ROT_NORMAL"

    # Kugel-/Rillengeometrie
    groove_conformity_inner: float = 0.58
    groove_conformity_outer: float = 0.60
    bearing_chamfer_mm: float = 0.30

    # V-Rille (vgroove)
    vgroove_depth_mm: float = 0.0
    vgroove_half_angle_deg: float = 45.0
    vgroove_shape: str = "V"

    # Kegelrollen
    contact_angle_deg: float = 14.0
    tapered_cone_width_mm: float = 0.0
    tapered_cup_width_mm: float = 0.0
    tapered_flange_height_mm: float = 1.0

    # Pendel-/Tonnenrollen
    spherical_rows: str = "1"
    spherical_contact_angle_deg: float = 10.0

    # Käfig
    use_cage: bool = False
    cage_style: str = "AUTO"
    cage_material: str = "STEEL"
    pocket_clearance_mm: float = 0.20
    oil_pocket_diameter_mm: float = 0.0

    # Auflösung
    segments: int = 48

    def spherical_row_count(self) -> int:
        """Anzahl Wälzkörperreihen (1 oder 2)."""
        try:
            return int(self.spherical_rows)
        except (TypeError, ValueError):
            return 1

    def apply_suggested_defaults(self) -> "BearingParams":
        """Setzt typgerechte Ringstärke/Wälzkörper-Ø/Anzahl (wie 'Auto-Berechnen').

        Verändert das Objekt in-place und gibt es zur Verkettung zurück.
        """
        suggestion = suggest_defaults(
            self.bearing_type,
            self.bore_diameter,
            self.outer_diameter,
            radial_clearance=self.radial_clearance,
            gap_factor=self.gap_factor,
            contact_angle_deg=self.contact_angle_deg,
        )
        self.ring_thickness = suggestion.ring_thickness
        self.roller_diameter = suggestion.roller_diameter
        self.element_count = suggestion.element_count
        return self


__all__ = ["BearingParams", "DEFAULT_TAPERED_CONTACT_ANGLE_DEG"]
