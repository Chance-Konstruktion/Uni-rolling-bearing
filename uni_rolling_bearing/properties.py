"""PropertyGroup für Lagerparameter im N-Panel."""

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
    bearing_type: EnumProperty(name="Lagertyp", items=BEARING_TYPES, default="BALL")
    series_code: EnumProperty(name="Normreihe", items=_series_items)

    use_preset: BoolProperty(name="Norm-Preset verwenden", default=True)
    bore_diameter: FloatProperty(name="Innendurchmesser d [mm]", default=20.0, min=1.0)
    outer_diameter: FloatProperty(name="Außendurchmesser D [mm]", default=47.0, min=2.0)
    width: FloatProperty(name="Breite B [mm]", default=14.0, min=1.0)

    ring_thickness: FloatProperty(name="Ringstärke [mm]", default=4.0, min=0.5)
    roller_diameter: FloatProperty(name="Wälzkörper-Ø [mm]", default=7.0, min=0.5)
    element_count: IntProperty(name="Wälzkörper Anzahl", default=10, min=3, max=256)
    gap_factor: FloatProperty(
        name="Umfangsspalt Faktor",
        description="Zusätzlicher Umfangsabstand zwischen Wälzkörpern",
        default=0.10,
        min=0.0,
        max=0.8,
    )
    auto_fit: BoolProperty(
        name="Auto-Fit aktiv",
        description="Passt Wälzkörper-Ø und Anzahl automatisch an, damit das Lager funktionsfähig bleibt",
        default=True,
    )

    use_cage: BoolProperty(
        name="Käfig erzeugen",
        description="Erzeugt einen einfachen parametrischen Käfig (zwei Endplatten + Webs zwischen den Wälzkörpern)",
        default=False,
    )

    segments: IntProperty(name="Auflösung Segmente", default=48, min=12, max=256)
    precision_class: EnumProperty(name="Toleranzklasse", items=PRECISION_CLASSES, default="NORMAL")
    radial_clearance: FloatProperty(name="Radiale Lagerluft [mm]", default=0.02, min=0.0)
