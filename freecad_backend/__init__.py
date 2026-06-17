"""FreeCAD-Frontend für den UNI Rolling Bearing Generator.

Dünne Brücke zwischen dem host-freien Geometrie-Kern (``uni_rolling_bearing``)
und FreeCAD/Part. Aufbau:

* ``params``           – host-freie Parameter-Datenklasse (spiegelt die UI).
* ``plan``             – host-freier Bauplan (Profile + Platzierungen).
* ``backend_freecad``  – baut aus dem Plan ``Part``-Solids (lazy ``import Part``).

Die GUI/Workbench (Commands, Toolbar) folgt in ``freecad_backend/workbench/``.
"""

from __future__ import annotations

from .params import BearingParams
from .plan import BearingPlan, build_plan

__all__ = ["BearingParams", "BearingPlan", "build_plan"]
