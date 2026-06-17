"""FreeCAD ``Part::FeaturePython``-Proxy für ein parametrisches Wälzlager.

Ein Lager ist ein einzelnes Dokumentobjekt mit allen Lager-Parametern als
Eigenschaften. Ändert der Nutzer einen Wert, baut :meth:`UniBearingProxy.execute`
die Geometrie über den geteilten Kern neu (Live-Rebuild). Der
Eigenschaften-Editor wird kontextabhängig aufgeräumt: nur Felder, die der
gewählte Lagertyp wirklich nutzt, sind sichtbar (``setEditorMode``) – die übrigen
bleiben erhalten, werden aber ausgeblendet.

``FreeCAD``/``Part`` werden nur in den Methoden importiert, damit dieses Modul
ohne laufendes FreeCAD importier- und (mit Mocks) testbar bleibt.
"""

from __future__ import annotations

import os

from ..backend_freecad import build_bearing
from ..params import BearingParams
from .. import uischema

_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "bearing.svg")


def _to_float(value) -> float:
    """FreeCAD-``Quantity`` (mm/°) → float; einfache Zahlen unverändert."""
    if hasattr(value, "Value"):
        return float(value.Value)
    return float(value)


def add_properties(obj) -> None:
    """Legt alle Lager-Eigenschaften gemäß :data:`uischema.SCHEMA` an."""
    for spec in uischema.SCHEMA:
        obj.addProperty(spec.fc_type, spec.name, spec.group, spec.label)
        default = uischema.default_for(spec.name)
        if spec.py_kind == "enum":
            # Erst Optionsliste setzen, dann Auswahl (FreeCAD-Konvention).
            setattr(obj, spec.name, list(spec.enum))
            setattr(obj, spec.name, str(default))
        else:
            setattr(obj, spec.name, default)


def params_from_obj(obj) -> BearingParams:
    """Liest die FreeCAD-Eigenschaften in eine :class:`BearingParams`-Instanz."""
    kwargs = {}
    for spec in uischema.SCHEMA:
        raw = getattr(obj, spec.name)
        if spec.py_kind in ("length", "angle", "float"):
            kwargs[spec.name] = _to_float(raw)
        elif spec.py_kind == "int":
            kwargs[spec.name] = int(raw)
        elif spec.py_kind == "bool":
            kwargs[spec.name] = bool(raw)
        else:  # enum → String
            kwargs[spec.name] = str(raw)
    return BearingParams(**kwargs)


def apply_visibility(obj) -> None:
    """Blendet kontextabhängig nicht genutzte Felder aus (Werte bleiben erhalten)."""
    vis = uischema.visible_fields(
        str(obj.bearing_type),
        bool(obj.use_cage),
        str(obj.cage_style),
        str(obj.spherical_rows),
    )
    for spec in uischema.SCHEMA:
        # 0 = normal sichtbar, 2 = versteckt.
        obj.setEditorMode(spec.name, 0 if spec.name in vis else 2)


class UniBearingProxy:
    """Proxy-Klasse hinter ``Part::FeaturePython`` (``obj.Proxy``)."""

    def __init__(self, obj):
        self.Type = "UniBearing"
        self._loading = True
        try:
            add_properties(obj)
            obj.Proxy = self
        finally:
            self._loading = False
        apply_visibility(obj)

    # FreeCAD-Serialisierung: nur den Typ merken, Geometrie wird neu gebaut.
    def __getstate__(self):
        return {"Type": getattr(self, "Type", "UniBearing")}

    def __setstate__(self, state):
        self.Type = (state or {}).get("Type", "UniBearing")
        self._loading = False
        return None

    def onChanged(self, obj, prop):
        # Während des Property-Aufbaus keine Reaktion (Felder sind noch unvollständig).
        if getattr(self, "_loading", False):
            return
        if prop in uischema.DRIVER_FIELDS:
            apply_visibility(obj)

    def execute(self, obj):
        """Baut die Lager-Geometrie neu und legt sie als ``obj.Shape`` ab."""
        # Nach Datei-Laden ist die Sichtbarkeit ggf. noch nicht gesetzt.
        apply_visibility(obj)
        params = params_from_obj(obj)
        try:
            result = build_bearing(params)
        except ValueError:
            # Unlösbare Maße: vorhandene Shape stehen lassen statt zu crashen.
            return
        obj.Shape = result.compound()


class ViewProviderBearing:
    """Minimaler ViewProvider (Icon im Baum)."""

    def __init__(self, vobj):
        vobj.Proxy = self

    def getIcon(self):
        return _ICON

    def attach(self, vobj):
        self.ViewObject = vobj

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


def make_bearing(doc=None, name: str = "Bearing"):
    """Erstellt ein neues Lager-Objekt im (aktiven) Dokument und gibt es zurück."""
    import FreeCAD as App

    if doc is None:
        doc = App.ActiveDocument or App.newDocument("Bearing")
    obj = doc.addObject("Part::FeaturePython", name)
    UniBearingProxy(obj)
    if getattr(App, "GuiUp", False) and getattr(obj, "ViewObject", None) is not None:
        ViewProviderBearing(obj.ViewObject)
    doc.recompute()
    return obj


__all__ = [
    "UniBearingProxy",
    "ViewProviderBearing",
    "add_properties",
    "params_from_obj",
    "apply_visibility",
    "make_bearing",
]
