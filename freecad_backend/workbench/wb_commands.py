"""GUI-Commands der UNI-Bearing-Workbench.

Zwei Commands:

* „Lager erzeugen" legt direkt ein parametrisches Lager-Objekt mit Defaults an.
* „Aus Katalog…" öffnet ein Task-Panel zur Lagertyp-/Baureihen-Auswahl
  (siehe :mod:`freecad_backend.workbench.wb_panel`).

``FreeCAD``/``FreeCADGui`` werden lazy importiert, damit das Modul ohne
laufendes FreeCAD testbar bleibt.
"""

from __future__ import annotations

import os

_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "bearing.svg")

CREATE_COMMAND = "UniBearing_Create"
CATALOG_COMMAND = "UniBearing_Catalog"


class CreateBearingCommand:
    """Erzeugt ein neues parametrisches Wälzlager."""

    def GetResources(self):
        return {
            "Pixmap": _ICON,
            "MenuText": "Lager erzeugen",
            "ToolTip": "Ein parametrisches Wälzlager (DIN/ISO) im aktiven Dokument anlegen",
        }

    def IsActive(self):
        # Immer aktiv: legt bei Bedarf ein neues Dokument an.
        return True

    def Activated(self):
        from .wb_bearing import make_bearing

        make_bearing()


class CatalogBearingCommand:
    """Öffnet das Katalog-Task-Panel (Lagertyp + Baureihe wählen)."""

    def GetResources(self):
        return {
            "Pixmap": _ICON,
            "MenuText": "Aus Katalog…",
            "ToolTip": "Lagertyp und Baureihe aus dem Norm-Katalog wählen und erzeugen",
        }

    def IsActive(self):
        return True

    def Activated(self):
        from .wb_panel import show_catalog_panel

        show_catalog_panel()


def register_commands():
    """Registriert alle Commands und liefert ihre IDs (für Toolbar/Menü)."""
    import FreeCADGui as Gui

    Gui.addCommand(CREATE_COMMAND, CreateBearingCommand())
    Gui.addCommand(CATALOG_COMMAND, CatalogBearingCommand())
    return [CATALOG_COMMAND, CREATE_COMMAND]


__all__ = [
    "CreateBearingCommand",
    "CatalogBearingCommand",
    "register_commands",
    "CREATE_COMMAND",
    "CATALOG_COMMAND",
]
