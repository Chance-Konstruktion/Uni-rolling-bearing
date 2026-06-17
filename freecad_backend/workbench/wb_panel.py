"""FreeCAD-Task-Panel: Lagertyp-Katalog.

Ein klassisches FreeCAD-Task-Dialog (links angedockt), das den Katalog-Workflow
des Blender-N-Panels 1:1 spiegelt:

* **1) Lagertyp** wählen – mit Normhinweis-Text darunter.
* **2) Katalog** – je nach Coding des Typs:
    * ``din623`` (Kugel-, Zylinderrollen-, Kegelrollen-, Tonnenlager):
      zwei Dropdowns **Maßreihe** + **Bohrungskennzahl**, die zur DIN-Bezeichnung
      (z. B. ``6204``) zusammengesetzt werden.
    * ``direct`` (Nadel-, U-Rillen-Lager): ein **Code**-Dropdown (HK0808, SG10 …).
* **Maß-Vorschau** d × D × B und Käfig-Option.

Beim Bestätigen wird ein parametrisches Lager-Objekt angelegt, das Preset
(d/D/B plus katalognahe Wälzkörper-Defaults) übernommen und die Geometrie neu
gebaut. Die Auswahl-/Übernahme-Logik liegt host-frei in
:mod:`freecad_backend.catalog`; dieses Modul ist die reine Qt-Hülle.
``FreeCAD``/``FreeCADGui``/Qt werden nur in den Methoden importiert, damit das
Modul ohne laufendes FreeCAD importierbar bleibt.
"""

from __future__ import annotations

from .. import catalog
from ..params import BearingParams


def _qt():
    """Liefert das ``QtGui``-Modul von FreeCAD (PySide), lazy importiert."""
    from PySide import QtGui  # noqa: PLC0415

    return QtGui


class CatalogTaskPanel:
    """Task-Panel zur Lagertyp-/Baureihen-Auswahl (1:1 zum Blender-N-Panel)."""

    def __init__(self):
        QtGui = _qt()

        self.form = QtGui.QWidget()
        self.form.setWindowTitle("UNI Lager – Katalog")
        layout = QtGui.QFormLayout(self.form)

        # 1) Lagertyp (Label sichtbar, ID in UserData).
        self.type_combo = QtGui.QComboBox()
        for bid, label, desc in catalog.bearing_type_choices():
            self.type_combo.addItem(label, bid)
            self.type_combo.setItemData(
                self.type_combo.count() - 1, desc, int(QtGui.Qt.ToolTipRole)
            )
        layout.addRow("1) Lagertyp", self.type_combo)

        # Normhinweis unter dem Typ (wie im Blender-Panel).
        self.norm_label = QtGui.QLabel("")
        self.norm_label.setWordWrap(True)
        layout.addRow("", self.norm_label)

        # 2a) DIN-623-Modus: Maßreihe + Bohrungskennzahl.
        self.series_combo = QtGui.QComboBox()
        self.series_row_label = QtGui.QLabel("Maßreihe")
        layout.addRow(self.series_row_label, self.series_combo)

        self.bore_combo = QtGui.QComboBox()
        self.bore_row_label = QtGui.QLabel("Bohrungskennzahl")
        layout.addRow(self.bore_row_label, self.bore_combo)

        # 2b) Direct-Modus: ein Code-Dropdown.
        self.code_combo = QtGui.QComboBox()
        self.code_row_label = QtGui.QLabel("Code")
        layout.addRow(self.code_row_label, self.code_combo)

        # Bezeichnung + Maß-Vorschau.
        self.designation_label = QtGui.QLabel("–")
        layout.addRow("Bezeichnung", self.designation_label)
        self.dims_label = QtGui.QLabel("–")
        layout.addRow("Maße d × D × B", self.dims_label)

        # Käfig erzeugen?
        self.cage_check = QtGui.QCheckBox("Käfig erzeugen")
        layout.addRow("", self.cage_check)

        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.series_combo.currentIndexChanged.connect(self._on_series_changed)
        self.bore_combo.currentIndexChanged.connect(self._update_preview)
        self.code_combo.currentIndexChanged.connect(self._update_preview)

        self._on_type_changed()

    # --- Auswahl-Zustand ---------------------------------------------------- #
    def _current_type(self) -> str:
        return str(self.type_combo.currentData())

    def _is_din623(self) -> bool:
        return catalog.coding_for(self._current_type()) == "din623"

    def selected_code(self) -> str:
        """Aktuell gewählter Katalog-Code (kombiniert bzw. direkt)."""
        if self._is_din623():
            series = str(self.series_combo.currentText()) if self.series_combo.count() else ""
            bore = str(self.bore_combo.currentText()) if self.bore_combo.count() else ""
            if not series or not bore:
                return ""
            return catalog.combined_code(series, bore)
        return str(self.code_combo.currentText()) if self.code_combo.count() else ""

    # --- Eventhandler ------------------------------------------------------- #
    def _set_mode(self, din623: bool):
        for w in (self.series_combo, self.series_row_label, self.bore_combo, self.bore_row_label):
            w.setVisible(din623)
        for w in (self.code_combo, self.code_row_label):
            w.setVisible(not din623)

    def _on_type_changed(self, *_):
        bt = self._current_type()
        self.norm_label.setText(catalog.norm_hint_for(bt))
        din623 = self._is_din623()
        self._set_mode(din623)

        if din623:
            self.series_combo.blockSignals(True)
            self.series_combo.clear()
            for s in catalog.mass_series_for(bt):
                self.series_combo.addItem(s)
            self.series_combo.blockSignals(False)
            self._on_series_changed()
        else:
            self.code_combo.blockSignals(True)
            self.code_combo.clear()
            for code in catalog.series_codes(bt):
                self.code_combo.addItem(code)
            self.code_combo.blockSignals(False)
            self._update_preview()

    def _on_series_changed(self, *_):
        bt = self._current_type()
        series = str(self.series_combo.currentText()) if self.series_combo.count() else ""
        self.bore_combo.blockSignals(True)
        self.bore_combo.clear()
        for code in catalog.bore_codes_for(bt, series):
            self.bore_combo.addItem(code)
        self.bore_combo.blockSignals(False)
        self._update_preview()

    def _update_preview(self, *_):
        code = self.selected_code()
        self.designation_label.setText(code or "–")
        dims = catalog.preset_dims(self._current_type(), code)
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
            BearingParams(), self._current_type(), self.selected_code()
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
