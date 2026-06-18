"""FreeCAD-Task-Panel: Lagertyp-Katalog.

Ein klassisches FreeCAD-Task-Dialog (links angedockt), das den Katalog-Workflow
des Blender-N-Panels 1:1 spiegelt:

* **1) Lagertyp** wählen – mit Normhinweis-Text darunter.
* **2) Katalog** – je nach Coding des Typs:
    * ``din623`` (Kugel-, Zylinderrollen-, Kegelrollen-, Tonnenlager):
      zwei Dropdowns **Maßreihe** + **Bohrungskennzahl**, die zur DIN-Bezeichnung
      (z. B. ``6204``) zusammengesetzt werden.
    * ``direct`` (Nadel-, U-Rillen-Lager): ein **Code**-Dropdown (HK0808, SG10 …).
* **Maß-Vorschau** d × D × B.
* **3) Normen & Toleranzen** – Toleranzklasse (ISO 492) + Toleranzlage mit
  Live-Vorschau der wirksamen Offsets (Δd/ΔD/ΔB in µm) und Radialluft.
* **4) Tragzahlen & Lebensdauer** – Radial-/Axiallast und Drehzahl (ISO 281).
* **5) Passungen (DIN 5418)** – Belastungsfall.
* **Live-Ergebnisse** – Plausibilität, Tragzahlen (C0r/Cr/P/L10h) und
  Passungs-Empfehlung, laufend aktualisiert (Blender-Abschnitt „Ergebnisse").
* **Käfig-Option.**

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

        # 3) Normen & Toleranzen (wie Blender-Abschnitt „2) Normen & Presets").
        defaults = BearingParams()
        self.precision_combo = QtGui.QComboBox()
        for pid, label, desc in catalog.precision_class_choices():
            self.precision_combo.addItem(label, pid)
            self.precision_combo.setItemData(
                self.precision_combo.count() - 1, desc, int(QtGui.Qt.ToolTipRole)
            )
        self._select_by_data(self.precision_combo, defaults.precision_class)
        layout.addRow("Toleranzklasse", self.precision_combo)

        self.tol_pos_combo = QtGui.QComboBox()
        for tid, label, desc in catalog.tolerance_position_choices():
            self.tol_pos_combo.addItem(label, tid)
            self.tol_pos_combo.setItemData(
                self.tol_pos_combo.count() - 1, desc, int(QtGui.Qt.ToolTipRole)
            )
        self._select_by_data(self.tol_pos_combo, defaults.tolerance_position)
        layout.addRow("Toleranzlage", self.tol_pos_combo)

        # Live-Vorschau der wirksamen Toleranz-Offsets (Δd/ΔD/ΔB).
        self.tol_offset_label = QtGui.QLabel("")
        self.tol_offset_label.setWordWrap(True)
        layout.addRow("", self.tol_offset_label)

        # Radialluft.
        self.clearance_spin = QtGui.QDoubleSpinBox()
        self.clearance_spin.setDecimals(3)
        self.clearance_spin.setRange(0.0, 1.0)
        self.clearance_spin.setSingleStep(0.005)
        self.clearance_spin.setSuffix(" mm")
        self.clearance_spin.setValue(defaults.radial_clearance)
        layout.addRow("Radialluft", self.clearance_spin)

        # 4) Tragzahlen & Lebensdauer (Blender-Abschnitt „6) …").
        self.fr_spin = self._force_spin(QtGui, defaults.radial_load_fr_n)
        layout.addRow("Radiallast Fr", self.fr_spin)
        self.fa_spin = self._force_spin(QtGui, defaults.axial_load_fa_n)
        layout.addRow("Axiallast Fa", self.fa_spin)
        self.speed_spin = QtGui.QDoubleSpinBox()
        self.speed_spin.setDecimals(0)
        self.speed_spin.setRange(0.0, 1.0e6)
        self.speed_spin.setSingleStep(100.0)
        self.speed_spin.setSuffix(" 1/min")
        self.speed_spin.setValue(defaults.speed_rpm)
        layout.addRow("Drehzahl n", self.speed_spin)

        # 5) Passungen (DIN 5418).
        self.load_case_combo = QtGui.QComboBox()
        for lid, label, desc in catalog.load_case_choices():
            self.load_case_combo.addItem(label, lid)
            self.load_case_combo.setItemData(
                self.load_case_combo.count() - 1, desc, int(QtGui.Qt.ToolTipRole)
            )
        self._select_by_data(self.load_case_combo, defaults.load_case)
        layout.addRow("Belastungsfall", self.load_case_combo)

        # Live-Ergebnisse (Plausibilität / Tragzahlen / Passungen).
        self.results_label = QtGui.QLabel("")
        self.results_label.setWordWrap(True)
        self.results_label.setTextFormat(int(QtGui.Qt.RichText))
        layout.addRow("Ergebnisse", self.results_label)

        # Käfig erzeugen?
        self.cage_check = QtGui.QCheckBox("Käfig erzeugen")
        layout.addRow("", self.cage_check)

        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.series_combo.currentIndexChanged.connect(self._on_series_changed)
        self.bore_combo.currentIndexChanged.connect(self._update_preview)
        self.code_combo.currentIndexChanged.connect(self._update_preview)
        self.precision_combo.currentIndexChanged.connect(self._update_tolerance_preview)
        self.tol_pos_combo.currentIndexChanged.connect(self._update_tolerance_preview)
        self.precision_combo.currentIndexChanged.connect(self._update_results)
        self.tol_pos_combo.currentIndexChanged.connect(self._update_results)
        self.clearance_spin.valueChanged.connect(self._update_results)
        self.fr_spin.valueChanged.connect(self._update_results)
        self.fa_spin.valueChanged.connect(self._update_results)
        self.speed_spin.valueChanged.connect(self._update_results)
        self.load_case_combo.currentIndexChanged.connect(self._update_results)

        self._on_type_changed()

    @staticmethod
    def _select_by_data(combo, value: str):
        """Wählt den Eintrag mit ``UserData == value`` (sonst Index 0)."""
        idx = combo.findData(value)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    @staticmethod
    def _force_spin(QtGui, value: float):
        """Spinbox für eine Last in Newton (0 … 1e9 N)."""
        spin = QtGui.QDoubleSpinBox()
        spin.setDecimals(0)
        spin.setRange(0.0, 1.0e9)
        spin.setSingleStep(50.0)
        spin.setSuffix(" N")
        spin.setValue(value)
        return spin

    # --- Auswahl-Zustand ---------------------------------------------------- #
    def _current_type(self) -> str:
        return str(self.type_combo.currentData())

    def _current_precision(self) -> str:
        return str(self.precision_combo.currentData())

    def _current_tolerance_position(self) -> str:
        return str(self.tol_pos_combo.currentData())

    def _current_load_case(self) -> str:
        return str(self.load_case_combo.currentData())

    def _build_params(self) -> BearingParams:
        """Baut die ``BearingParams`` aus dem aktuellen Panel-Zustand.

        Quelle der Wahrheit für **Vorschau und Erzeugen** – Radialluft wird vor
        dem Preset gesetzt, damit ``suggest_defaults`` (in ``apply_preset``) sie
        berücksichtigt (wie im Blender-Workflow).
        """
        base = BearingParams(radial_clearance=float(self.clearance_spin.value()))
        params = catalog.apply_preset(base, self._current_type(), self.selected_code())
        params.precision_class = self._current_precision()
        params.tolerance_position = self._current_tolerance_position()
        params.radial_load_fr_n = float(self.fr_spin.value())
        params.axial_load_fa_n = float(self.fa_spin.value())
        params.speed_rpm = float(self.speed_spin.value())
        params.load_case = self._current_load_case()
        params.use_cage = bool(self.cage_check.isChecked())
        return params

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
        self._update_tolerance_preview()
        self._update_results()

    def _update_results(self, *_):
        """Live-Auswertung (Plausibilität / Tragzahlen / Passungen) anzeigen."""
        from .. import analysis  # noqa: PLC0415

        try:
            res = analysis.analyze(self._build_params())
        except Exception as exc:  # pragma: no cover - defensiv gegen Rechen-Edge-Cases
            self.results_label.setText(f"<i>Auswertung nicht möglich: {exc}</i>")
            return

        blocks = []
        if res.error:
            blocks.append(f"<b>Plausibilität</b><br>⚠ {res.error}")
        elif res.plausibility:
            blocks.append("<b>Plausibilität</b><br>" + "<br>".join(res.plausibility))
        if res.ratings:
            blocks.append("<b>Tragzahlen</b><br>" + "<br>".join(res.ratings))
        if res.fits:
            blocks.append("<b>Passungen</b><br>" + "<br>".join(res.fits))
        self.results_label.setText("<br><br>".join(blocks))

    def _update_tolerance_preview(self, *_):
        """Aktualisiert die Δd/ΔD/ΔB-Anzeige aus dem aktuellen Preset + Toleranz."""
        dims = catalog.preset_dims(self._current_type(), self.selected_code())
        if dims is None:
            self.tol_offset_label.setText("")
            return
        d, D, B = dims
        self.tol_offset_label.setText(
            catalog.tolerance_offset_text(
                d, D, B, self._current_precision(), self._current_tolerance_position()
            )
        )

    # --- FreeCAD-Task-Dialog-Protokoll -------------------------------------- #
    def accept(self):
        """OK: Lager erzeugen, Preset anwenden, Dialog schließen."""
        from .wb_bearing import make_bearing, set_params_on_obj, apply_visibility

        params = self._build_params()

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
