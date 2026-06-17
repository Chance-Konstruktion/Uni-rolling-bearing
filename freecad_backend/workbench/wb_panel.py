"""FreeCAD-Task-Panel: Lagertyp-Katalog.

Ein klassisches FreeCAD-Task-Dialog (links angedockt), mit dem der Nutzer einen
**Lagertyp** und eine **Baureihe/Kennzahl** aus dem Norm-Katalog wählt. Beim
Bestätigen wird ein parametrisches Lager-Objekt angelegt, das Preset (d/D/B plus
katalognahe Wälzkörper-Defaults) übernommen und die Geometrie neu gebaut.

Die Auswahl-/Übernahme-Logik liegt host-frei in :mod:`freecad_backend.catalog`;
dieses Modul ist die reine Qt-Hülle. ``FreeCAD``/``FreeCADGui``/Qt werden nur in
den Methoden importiert, damit das Modul ohne laufendes FreeCAD importierbar
bleibt.
"""

from __future__ import annotations

from .. import catalog
from ..params import BearingParams


def _qt():
    """Liefert das ``QtGui``-Modul von FreeCAD (PySide), lazy importiert."""
    from PySide import QtGui  # noqa: PLC0415

    return QtGui


class CatalogTaskPanel:
    """Task-Panel zur Lagertyp-/Baureihen-Auswahl."""

    def __init__(self):
        QtGui = _qt()

        self.form = QtGui.QWidget()
        self.form.setWindowTitle("UNI Lager – Katalog")
        layout = QtGui.QFormLayout(self.form)

        # Lagertyp-Auswahl (Label sichtbar, ID in UserData).
        self.type_combo = QtGui.QComboBox()
        for bid, label, desc in catalog.bearing_type_choices():
            self.type_combo.addItem(label, bid)
            self.type_combo.setItemData(
                self.type_combo.count() - 1, desc, int(QtGui.Qt.ToolTipRole)
            )
        layout.addRow("Lagertyp", self.type_combo)

        # Baureihe / Kennzahl (wird je Typ neu befüllt).
        self.series_combo = QtGui.QComboBox()
        layout.addRow("Baureihe / Code", self.series_combo)

        # Maß-Vorschau d / D / B.
        self.dims_label = QtGui.QLabel("–")
        layout.addRow("Maße d × D × B", self.dims_label)

        # Käfig erzeugen?
        self.cage_check = QtGui.QCheckBox("Käfig erzeugen")
        layout.addRow("", self.cage_check)

        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.series_combo.currentIndexChanged.connect(self._update_dims)

        self._on_type_changed()

    # --- Eventhandler ------------------------------------------------------- #
    def _current_type(self) -> str:
        return str(self.type_combo.currentData())

    def _current_code(self) -> str:
        return str(self.series_combo.currentText()) if self.series_combo.count() else ""

    def _on_type_changed(self, *_):
        self.series_combo.blockSignals(True)
        self.series_combo.clear()
        for code in catalog.series_codes(self._current_type()):
            self.series_combo.addItem(code)
        self.series_combo.blockSignals(False)
        self._update_dims()

    def _update_dims(self, *_):
        dims = catalog.preset_dims(self._current_type(), self._current_code())
        if dims is None:
            self.dims_label.setText("–")
        else:
            d, D, B = dims
            self.dims_label.setText(f"{d:g} × {D:g} × {B:g} mm")

    # --- FreeCAD-Task-Dialog-Protokoll -------------------------------------- #
    def accept(self):
        """OK: Lager erzeugen, Preset anwenden, Dialog schließen."""
        from .wb_bearing import make_bearing, set_params_on_obj, apply_visibility

        params = catalog.apply_preset(
            BearingParams(), self._current_type(), self._current_code()
        )
        params.use_cage = bool(self.cage_check.isChecked())

        obj = make_bearing()
        set_params_on_obj(obj, params)
        apply_visibility(obj)
        obj.Document.recompute()

        self._close()
        return True

    def reject(self):
        self._close()
        return True

    @staticmethod
    def _close():
        import FreeCADGui as Gui

        Gui.Control.closeDialog()


def show_catalog_panel():
    """Öffnet das Katalog-Task-Panel in FreeCAD."""
    import FreeCADGui as Gui

    Gui.Control.showDialog(CatalogTaskPanel())


__all__ = ["CatalogTaskPanel", "show_catalog_panel"]
