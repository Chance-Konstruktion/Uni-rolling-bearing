"""GUI-Commands der UNI-Bearing-Workbench.

Aktuell ein Command: „Lager erzeugen" legt ein parametrisches Lager-Objekt im
aktiven Dokument an. ``FreeCAD``/``FreeCADGui`` werden lazy importiert, damit das
Modul ohne laufendes FreeCAD testbar bleibt.
"""

from __future__ import annotations

import os

_ICON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons", "bearing.svg")

CREATE_COMMAND = "UniBearing_Create"


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


def register_commands():
    """Registriert alle Commands und liefert ihre IDs (für Toolbar/Menü)."""
    import FreeCADGui as Gui

    Gui.addCommand(CREATE_COMMAND, CreateBearingCommand())
    return [CREATE_COMMAND]


__all__ = ["CreateBearingCommand", "register_commands", "CREATE_COMMAND"]
