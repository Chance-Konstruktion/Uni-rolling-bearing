"""Host-freier Katalog-Helfer für das FreeCAD-Task-Panel.

Kapselt die Lagertyp-/Baureihen-Auswahl und das Anwenden eines Norm-Presets
auf :class:`~freecad_backend.params.BearingParams` – **ohne** ``FreeCAD``,
``FreeCADGui`` oder ``bpy``. So bleibt die Katalog-Logik (die das Qt-Panel nur
noch anzeigt) eigenständig testbar.

Die eigentlichen Presets liegen im geteilten Kern (``constants.SERIES_PRESETS``,
aus den JSON-Dateien unter ``data/``). Dieses Modul spiegelt die Auswahl- und
Übernahme-Logik des Blender-Operators (``operators.py``) für FreeCAD.
"""

from __future__ import annotations

from dataclasses import replace
from typing import List, Optional, Tuple

from uni_rolling_bearing import constants, norm_engine
from uni_rolling_bearing.geometry import suggest_defaults

from .params import BearingParams


def bearing_type_choices() -> List[Tuple[str, str, str]]:
    """Alle Lagertypen als ``(id, label, beschreibung)`` (für das Typ-Dropdown)."""
    return [(bid, label, desc) for bid, label, desc in constants.BEARING_TYPES]


def coding_for(bearing_type: str) -> str:
    """Coding-Schema des Lagertyps: ``'din623'`` (Reihe+Kennzahl) oder ``'direct'``."""
    return norm_engine.coding_for(bearing_type)


def norm_hint_for(bearing_type: str) -> str:
    """Normhinweis-Text für die Beschriftung unter dem Lagertyp (z. B. DIN 625 / ISO 15)."""
    return norm_engine.norm_hint_for(bearing_type) or ""


def mass_series_for(bearing_type: str) -> List[str]:
    """Maßreihen-Codes (mit Prefix) eines DIN-623-Lagertyps – sonst leer."""
    return list(norm_engine.load_series_for(bearing_type))


def bore_codes_for(bearing_type: str, mass_series: str) -> List[str]:
    """Bohrungskennzahlen einer Maßreihe (sortiert nach Bohrungs-Ø) – sonst leer."""
    if not mass_series:
        return []
    return list(norm_engine.load_bore_codes_for(bearing_type, mass_series))


def combined_code(mass_series: str, bore_code: str) -> str:
    """Setzt Maßreihe + Bohrungskennzahl zur DIN-Bezeichnung zusammen (z. B. ``6204``)."""
    return f"{mass_series}{bore_code}"


def series_codes(bearing_type: str) -> List[str]:
    """Sortierte Liste der Katalog-Codes (Baureihen) für einen Lagertyp."""
    presets = constants.SERIES_PRESETS.get(bearing_type, {})
    return sorted(presets.keys())


def preset_dims(bearing_type: str, code: str) -> Optional[Tuple[float, float, float]]:
    """Hauptmaße ``(d, D, B)`` eines Katalog-Codes – oder ``None``, wenn unbekannt."""
    return constants.SERIES_PRESETS.get(bearing_type, {}).get(code)


def apply_preset(params: BearingParams, bearing_type: str, code: str) -> BearingParams:
    """Wendet Lagertyp + Katalog-Code auf ``params`` an und liefert eine neue Instanz.

    Setzt Hauptmaße (d/D/B) aus dem Preset, zieht für Kegelrollenlager die
    getrennten Cone-/Cup-Breiten nach und ergänzt geometrisch plausible
    Wälzkörper-Defaults (Ringstärke, Wälzkörper-Ø, Anzahl) – genau wie der
    Blender-Operator ``apply_suggested_defaults``. Unbekannte Kombinationen
    lassen ``params`` (bis auf den Lagertyp) unverändert.
    """
    dims = preset_dims(bearing_type, code)
    if dims is None:
        return replace(params, bearing_type=bearing_type)

    bore, outer, width = dims
    updated = replace(
        params,
        bearing_type=bearing_type,
        bore_diameter=float(bore),
        outer_diameter=float(outer),
        width=float(width),
    )

    # Kegelrollenlager: getrennte Cone-/Cup-Breiten (B, C) aus den Ring-Daten.
    if bearing_type == constants.TAPERED:
        from uni_rolling_bearing import norm_engine

        ring_widths = norm_engine.load_ring_widths_for(constants.TAPERED)
        entry = ring_widths.get(code)
        if entry is not None:
            updated = replace(
                updated,
                tapered_cone_width_mm=float(entry[0]),
                tapered_cup_width_mm=float(entry[1]),
            )
        else:
            updated = replace(updated, tapered_cone_width_mm=0.0, tapered_cup_width_mm=0.0)

    # Ringstärke / Wälzkörper-Ø / Anzahl katalognah nachziehen.
    suggested = suggest_defaults(
        bearing_type,
        updated.bore_diameter,
        updated.outer_diameter,
        radial_clearance=updated.radial_clearance,
        gap_factor=updated.gap_factor,
        contact_angle_deg=updated.contact_angle_deg,
    )
    updated = replace(
        updated,
        ring_thickness=suggested.ring_thickness,
        roller_diameter=suggested.roller_diameter,
        element_count=suggested.element_count,
    )
    return updated


__all__ = [
    "bearing_type_choices",
    "coding_for",
    "norm_hint_for",
    "mass_series_for",
    "bore_codes_for",
    "combined_code",
    "series_codes",
    "preset_dims",
    "apply_preset",
]
