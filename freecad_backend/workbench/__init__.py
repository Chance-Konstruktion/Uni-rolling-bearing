"""FreeCAD-GUI-Schicht der UNI-Bearing-Workbench.

* ``wb_bearing``  – ``Part::FeaturePython``-Proxy mit Live-Rebuild und
  kontextabhängigem Eigenschaften-Editor; Factory ``make_bearing``.
* ``wb_commands`` – GUI-Command „Lager erzeugen" + ``register_commands``.

Die Geometrie selbst stammt aus ``freecad_backend.backend_freecad`` (geteilter
Kern). FreeCAD-Importe erfolgen lazy, damit die Logik ohne Host testbar bleibt.
"""

from __future__ import annotations
