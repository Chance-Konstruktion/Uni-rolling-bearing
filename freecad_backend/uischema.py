"""Host-freies UI-Schema für den FreeCAD-Eigenschaften-Editor.

Beschreibt **deklarativ**, welche Eigenschaften ein Lager-Objekt in FreeCAD hat
(Typ, Gruppe, Label) und – kontextabhängig – welche davon für den aktuell
gewählten Lagertyp / die Käfig-Optionen *sichtbar* sind.

Beide Aspekte sind ohne FreeCAD testbar:

* :data:`SCHEMA` spiegelt 1:1 die Felder der :class:`~freecad_backend.params.BearingParams`
  (Defaults werden direkt aus ``BearingParams()`` gezogen – keine Doppelpflege).
* :func:`visible_fields` spiegelt die Sichtbarkeitslogik des Blender-N-Panels
  (``panel.py``): nur Felder, die der gewählte Lagertyp wirklich nutzt.

Der FreeCAD-Proxy (``workbench/wb_bearing.py``) iteriert :data:`SCHEMA` für
``addProperty`` und nutzt :func:`visible_fields` für ``setEditorMode`` – mehr
FreeCAD-spezifischer Code ist dafür nicht nötig.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence, Set, Tuple

from uni_rolling_bearing import constants
from uni_rolling_bearing.tolerances import TOLERANCE_POSITIONS

from .params import BearingParams

# Enum-Optionen, die nur im Blender-``properties``-Modul (mit ``bpy``) leben,
# werden hier host-frei gespiegelt.
_CAGE_STYLES = ["AUTO", "POCKET", "MASSIVE", "RIBBON", "LADDER"]
_CAGE_MATERIALS = ["STEEL", "BRASS", "POLYMER"]
_VGROOVE_SHAPES = ["V", "U"]
_SPHERICAL_ROWS = ["1", "2"]


@dataclass(frozen=True)
class FieldSpec:
    """Eine FreeCAD-Eigenschaft eines Lager-Objekts."""

    name: str           # = BearingParams-Attribut UND FreeCAD-Property-Name
    fc_type: str        # FreeCAD-Property-Typ (App::PropertyLength, …)
    py_kind: str        # 'length' | 'angle' | 'float' | 'int' | 'bool' | 'enum'
    group: str          # Gruppe im Eigenschaften-Editor
    label: str          # Kurzbeschreibung
    enum: Optional[Tuple[str, ...]] = None  # Optionen bei py_kind == 'enum'


_BEARING_TYPE_IDS = tuple(item[0] for item in constants.BEARING_TYPES)
_PRECISION_IDS = tuple(item[0] for item in constants.PRECISION_CLASSES)
_TOLERANCE_IDS = tuple(item[0] for item in TOLERANCE_POSITIONS)


SCHEMA: List[FieldSpec] = [
    FieldSpec("bearing_type", "App::PropertyEnumeration", "enum", "Lager", "Lagertyp", tuple(_BEARING_TYPE_IDS)),

    FieldSpec("bore_diameter", "App::PropertyLength", "length", "Geometrie", "Innen-Ø d [mm]"),
    FieldSpec("outer_diameter", "App::PropertyLength", "length", "Geometrie", "Außen-Ø D [mm]"),
    FieldSpec("width", "App::PropertyLength", "length", "Geometrie", "Breite B [mm]"),
    FieldSpec("ring_thickness", "App::PropertyLength", "length", "Geometrie", "Ringstärke [mm]"),

    FieldSpec("roller_diameter", "App::PropertyLength", "length", "Waelzkoerper", "Wälzkörper-Ø [mm]"),
    FieldSpec("element_count", "App::PropertyInteger", "int", "Waelzkoerper", "Anzahl"),
    FieldSpec("gap_factor", "App::PropertyFloat", "float", "Waelzkoerper", "Umfangsspalt-Faktor"),
    FieldSpec("auto_fit", "App::PropertyBool", "bool", "Waelzkoerper", "Auto-Fit"),

    FieldSpec("contact_angle_deg", "App::PropertyAngle", "angle", "Kegelrolle", "Kontaktwinkel α [°]"),
    FieldSpec("tapered_flange_height_mm", "App::PropertyLength", "length", "Kegelrolle", "Bord-Höhe [mm]"),
    FieldSpec("tapered_cone_width_mm", "App::PropertyLength", "length", "Kegelrolle", "Cone-Breite B [mm]"),
    FieldSpec("tapered_cup_width_mm", "App::PropertyLength", "length", "Kegelrolle", "Cup-Breite C [mm]"),

    FieldSpec("spherical_rows", "App::PropertyEnumeration", "enum", "Pendelrolle", "Rollenreihen", tuple(_SPHERICAL_ROWS)),
    FieldSpec("spherical_contact_angle_deg", "App::PropertyAngle", "angle", "Pendelrolle", "Pendel-Winkel α [°]"),

    FieldSpec("vgroove_shape", "App::PropertyEnumeration", "enum", "VRille", "Rillenform", tuple(_VGROOVE_SHAPES)),
    FieldSpec("vgroove_depth_mm", "App::PropertyLength", "length", "VRille", "Rillentiefe [mm]"),
    FieldSpec("vgroove_half_angle_deg", "App::PropertyAngle", "angle", "VRille", "Halbwinkel [°]"),

    FieldSpec("groove_conformity_inner", "App::PropertyFloat", "float", "Laufrille", "Konformität f_i"),
    FieldSpec("groove_conformity_outer", "App::PropertyFloat", "float", "Laufrille", "Konformität f_o"),
    FieldSpec("bearing_chamfer_mm", "App::PropertyLength", "length", "Laufrille", "Kantenfase r_s [mm]"),

    FieldSpec("use_cage", "App::PropertyBool", "bool", "Kaefig", "Käfig erzeugen"),
    FieldSpec("cage_style", "App::PropertyEnumeration", "enum", "Kaefig", "Bauart", tuple(_CAGE_STYLES)),
    FieldSpec("cage_material", "App::PropertyEnumeration", "enum", "Kaefig", "Werkstoff", tuple(_CAGE_MATERIALS)),
    FieldSpec("pocket_clearance_mm", "App::PropertyLength", "length", "Kaefig", "Pocket-Spiel [mm]"),
    FieldSpec("oil_pocket_diameter_mm", "App::PropertyLength", "length", "Kaefig", "Schmiertaschen-Ø [mm]"),

    FieldSpec("precision_class", "App::PropertyEnumeration", "enum", "Toleranzen", "Toleranzklasse", tuple(_PRECISION_IDS)),
    FieldSpec("tolerance_position", "App::PropertyEnumeration", "enum", "Toleranzen", "Toleranzlage", tuple(_TOLERANCE_IDS)),
    FieldSpec("radial_clearance", "App::PropertyLength", "length", "Toleranzen", "Radiale Lagerluft [mm]"),

    FieldSpec("segments", "App::PropertyInteger", "int", "Qualitaet", "Auflösung Segmente"),
]


# Felder, deren Änderung die Sichtbarkeit anderer Felder umschaltet.
DRIVER_FIELDS: Tuple[str, ...] = ("bearing_type", "use_cage", "cage_style", "spherical_rows")

_ALWAYS: Set[str] = {
    "bearing_type",
    "bore_diameter", "outer_diameter", "width", "ring_thickness",
    "roller_diameter", "element_count", "gap_factor", "auto_fit",
    "precision_class", "tolerance_position", "radial_clearance",
    "segments", "use_cage",
}


def default_for(name: str):
    """Default-Wert eines Feldes – direkt aus ``BearingParams`` (keine Doppelpflege)."""
    return getattr(BearingParams(), name)


def schema_names() -> Set[str]:
    return {spec.name for spec in SCHEMA}


def visible_fields(
    bearing_type: str,
    use_cage: bool = False,
    cage_style: str = "AUTO",
    spherical_rows: str = "1",
) -> Set[str]:
    """Welche Felder der gewählte Lagertyp/-aufbau tatsächlich nutzt.

    Spiegelt die Zeichenlogik von ``panel.py``: typ- und optionsabhängige
    Felder erscheinen nur, wenn sie relevant sind.
    """
    vis = set(_ALWAYS)

    if bearing_type == constants.TAPERED:
        vis |= {"contact_angle_deg", "tapered_flange_height_mm",
                "tapered_cone_width_mm", "tapered_cup_width_mm"}
    elif bearing_type == constants.SPHERICAL:
        vis.add("spherical_rows")
        if str(spherical_rows) == "2":
            vis.add("spherical_contact_angle_deg")
    elif bearing_type == constants.VGROOVE:
        vis |= {"vgroove_shape", "vgroove_depth_mm", "vgroove_half_angle_deg"}

    if bearing_type in (constants.BALL, constants.VGROOVE):
        vis |= {"groove_conformity_inner", "groove_conformity_outer", "bearing_chamfer_mm"}

    if use_cage:
        vis |= {"cage_style", "cage_material", "pocket_clearance_mm"}
        if str(cage_style) == "MASSIVE":
            vis.add("oil_pocket_diameter_mm")

    return vis


def hidden_fields(*args, **kwargs) -> Set[str]:
    """Komplement zu :func:`visible_fields` über alle Schema-Felder."""
    return schema_names() - visible_fields(*args, **kwargs)


__all__ = [
    "FieldSpec",
    "SCHEMA",
    "DRIVER_FIELDS",
    "default_for",
    "schema_names",
    "visible_fields",
    "hidden_fields",
]
