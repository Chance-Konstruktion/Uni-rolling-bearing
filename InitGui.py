# UNI Rolling Bearing Generator – FreeCAD Workbench (GUI-Einstiegspunkt).
#
# FreeCAD führt diese Datei beim Start über ``RunInitGuiPy`` aus. Zwei
# FreeCAD-spezifische Stolperfallen werden hier bewusst behandelt:
#
#   * Blocker 2: FreeCAD setzt ``__file__`` nicht → robuste Pfadermittlung.
#   * Blocker 3: ``InitGui.py`` läuft mit getrennten globals/locals; Werte, die
#     im Klassen-Body referenziert würden, werden NACH der Klasse auf Modulebene
#     gesetzt (sonst NameError).
#
# Die eigentliche Geometrie liegt host-frei in ``uni_rolling_bearing`` und wird
# über ``freecad_backend`` zu Part-Solids verarbeitet. Die Workbench bündelt das
# unter „UNI Bearings"; die GUI-Commands/Toolbar werden in einem Folgeschritt
# unter ``freecad_backend/workbench/`` ergänzt.

import os
import sys
import inspect

# --- Robuste Pfadermittlung (Blocker 2) ------------------------------------- #
try:
    _THIS = __file__
except NameError:  # FreeCAD-spezifischer Ausführungspfad ohne __file__
    _THIS = inspect.getfile(inspect.currentframe())
_DIR = os.path.dirname(os.path.abspath(_THIS))

# --- sys.path-Bootstrap ----------------------------------------------------- #
# Repo-Wurzel auf den Pfad, damit ``uni_rolling_bearing`` (Kern) und
# ``freecad_backend`` (Brücke) unabhängig vom Aufrufer importierbar sind.
for _p in (_DIR,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

_ICON = os.path.join(_DIR, "freecad_backend", "workbench", "icons", "bearing.svg")


import FreeCADGui as Gui


class UniBearingWorkbench(Gui.Workbench):
    """Parametrische Wälzlager nach Norm – FreeCAD-Workbench."""

    MenuText = "UNI Bearings"
    ToolTip = "Parametrische, normgerechte Wälzlager erzeugen"
    # KEIN ``Icon = _ICON`` im Klassen-Body (Blocker 3) – siehe unten.

    def Initialize(self):
        """Wird beim ersten Aktivieren der Workbench aufgerufen.

        Registriert die GUI-Commands und hängt sie in Toolbar und Menü. Der
        Bootstrap oben stellt sicher, dass Kern und Brücke importierbar sind.
        """
        from freecad_backend.workbench import wb_commands

        commands = wb_commands.register_commands()
        self.appendToolbar("UNI Bearings", commands)
        self.appendMenu("UNI Bearings", commands)
        self._commands = commands

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


# Modulvariablen erst NACH der Klassendefinition auf Modulebene zuweisen
# (Blocker 3: Klassen-Body sieht nur globals + builtins, nicht das locals-Dict).
UniBearingWorkbench.Icon = _ICON

Gui.addWorkbench(UniBearingWorkbench())
