"""Tests für die FreeCAD-Workbench-GUI – ohne laufendes FreeCAD.

Drei Ebenen:

1. **Host-freies UI-Schema** (`freecad_backend.uischema`): das Schema deckt exakt
   die `BearingParams`-Felder ab, und die Sichtbarkeitsregeln spiegeln das
   Blender-N-Panel (nur relevante Felder je Lagertyp/Käfig-Option).

2. **Part::FeaturePython-Proxy** (`workbench.wb_bearing`) mit gemocktem
   FreeCAD/Part: Eigenschaften werden angelegt, Defaults gesetzt, der
   Editor kontextabhängig auf-/zugeblendet (`setEditorMode`), und der
   Live-Rebuild (`execute`) erzeugt eine Shape.

3. **Command + InitGui** (Blocker 3-Pfad): `register_commands` meldet den
   Command an; `InitGui.Initialize()` hängt ihn in Toolbar und Menü.
"""

from __future__ import annotations

import dataclasses
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from uni_rolling_bearing import constants  # noqa: E402
from freecad_backend import uischema  # noqa: E402
from freecad_backend.params import BearingParams  # noqa: E402


# --------------------------------------------------------------------------- #
# 1) UI-Schema + Sichtbarkeit                                                  #
# --------------------------------------------------------------------------- #


class TestUISchema(unittest.TestCase):
    def test_schema_covers_all_params(self):
        param_fields = {f.name for f in dataclasses.fields(BearingParams)}
        self.assertEqual(uischema.schema_names(), param_fields)

    def test_enum_specs_have_options(self):
        for spec in uischema.SCHEMA:
            if spec.py_kind == "enum":
                self.assertTrue(spec.enum, f"{spec.name}: Enum ohne Optionen")
                # Default muss eine gültige Option sein.
                self.assertIn(str(uischema.default_for(spec.name)), spec.enum)

    def test_ball_visibility(self):
        vis = uischema.visible_fields(constants.BALL)
        self.assertIn("groove_conformity_inner", vis)
        self.assertIn("bearing_chamfer_mm", vis)
        self.assertNotIn("contact_angle_deg", vis)
        self.assertNotIn("vgroove_depth_mm", vis)
        self.assertNotIn("spherical_rows", vis)
        self.assertNotIn("cage_style", vis)  # use_cage default False

    def test_tapered_visibility(self):
        vis = uischema.visible_fields(constants.TAPERED)
        self.assertIn("contact_angle_deg", vis)
        self.assertIn("tapered_cup_width_mm", vis)
        self.assertNotIn("groove_conformity_inner", vis)
        self.assertNotIn("vgroove_depth_mm", vis)

    def test_spherical_rows_gates_contact_angle(self):
        one = uischema.visible_fields(constants.SPHERICAL, spherical_rows="1")
        two = uischema.visible_fields(constants.SPHERICAL, spherical_rows="2")
        self.assertIn("spherical_rows", one)
        self.assertNotIn("spherical_contact_angle_deg", one)
        self.assertIn("spherical_contact_angle_deg", two)

    def test_vgroove_visibility(self):
        vis = uischema.visible_fields(constants.VGROOVE)
        self.assertIn("vgroove_shape", vis)
        self.assertIn("groove_conformity_inner", vis)  # auch Kugel-Bauart

    def test_cage_visibility(self):
        off = uischema.visible_fields(constants.BALL, use_cage=False)
        on = uischema.visible_fields(constants.BALL, use_cage=True, cage_style="POCKET")
        massive = uischema.visible_fields(constants.BALL, use_cage=True, cage_style="MASSIVE")
        self.assertNotIn("cage_style", off)
        self.assertIn("cage_style", on)
        self.assertNotIn("oil_pocket_diameter_mm", on)
        self.assertIn("oil_pocket_diameter_mm", massive)

    def test_visible_and_hidden_partition_schema(self):
        for bt in (constants.BALL, constants.TAPERED, constants.SPHERICAL, constants.VGROOVE):
            vis = uischema.visible_fields(bt)
            hid = uischema.hidden_fields(bt)
            self.assertEqual(vis | hid, uischema.schema_names())
            self.assertEqual(vis & hid, set())


# --------------------------------------------------------------------------- #
# Gemockte FreeCAD-Umgebung                                                    #
# --------------------------------------------------------------------------- #


class _FakeShape:
    def __init__(self, log, kind):
        self._log, self.kind, self.Placement = log, kind, None

    def revolve(self, *a):
        self._log.append("revolve")
        return _FakeShape(self._log, "solid")

    def cut(self, other):
        self._log.append("cut")
        return _FakeShape(self._log, "cut")


class _FakeFeature:
    _RESERVED = {"Name", "Proxy", "Shape", "ViewObject", "Document"}

    def __init__(self, name="Bearing"):
        object.__setattr__(self, "_props", {})
        object.__setattr__(self, "_types", {})
        object.__setattr__(self, "_editor", {})
        object.__setattr__(self, "Name", name)
        object.__setattr__(self, "Proxy", None)
        object.__setattr__(self, "Shape", None)
        object.__setattr__(self, "ViewObject", None)
        object.__setattr__(self, "Document", None)

    def addProperty(self, fc_type, name, group="", doc=""):
        self._types[name] = fc_type
        self._props.setdefault(name, None)
        return self

    def setEditorMode(self, name, mode):
        self._editor[name] = mode

    def __getattr__(self, item):
        props = object.__getattribute__(self, "_props")
        if item in props:
            return props[item]
        raise AttributeError(item)

    def __setattr__(self, key, value):
        if key.startswith("_") or key in _FakeFeature._RESERVED:
            object.__setattr__(self, key, value)
        else:
            self._props[key] = value


class _FakeDocument:
    def __init__(self, name="Unnamed"):
        self.Name = name
        self.Objects = []

    def addObject(self, type_, name):
        f = _FakeFeature(name)
        f.Document = self
        self.Objects.append(f)
        return f

    def recompute(self):
        for o in self.Objects:
            if o.Proxy is not None and hasattr(o.Proxy, "execute"):
                o.Proxy.execute(o)
        return True


def _install_fakes():
    """Installiert gemockte ``Part``/``FreeCAD``-Module. Liefert (log, restore)."""
    log = []
    part = types.ModuleType("Part")
    part.makePolygon = lambda pts: (log.append("makePolygon"), _FakeShape(log, "wire"))[1]
    part.Face = lambda wire: _FakeShape(log, "face")
    part.makeSphere = lambda r: (log.append("makeSphere"), _FakeShape(log, "sphere"))[1]
    part.makeCone = lambda r1, r2, h: (log.append("makeCone"), _FakeShape(log, "cone"))[1]
    part.makeBox = lambda *a, **k: (log.append("makeBox"), _FakeShape(log, "box"))[1]
    part.makeCompound = lambda shapes: (log.append("makeCompound"), _FakeShape(log, "compound"))[1]

    class _Vec:
        def __init__(self, *a):
            self.a = a

    class _Rot:
        def __init__(self, *a):
            self.a = a

        def multiply(self, other):
            return _Rot("mul")

    class _Plc:
        def __init__(self, v=None, r=None):
            self.v, self.r = v, r

        def multiply(self, other):
            return _Plc("mul")

    fc = types.ModuleType("FreeCAD")
    fc.Vector, fc.Rotation, fc.Placement = _Vec, _Rot, _Plc
    fc.GuiUp = False
    fc.ActiveDocument = None
    fc.newDocument = lambda *a, **k: _FakeDocument(a[0] if a else "Unnamed")

    saved = {n: sys.modules.get(n) for n in ("Part", "FreeCAD")}
    sys.modules["Part"], sys.modules["FreeCAD"] = part, fc

    def restore():
        for n, m in saved.items():
            if m is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = m

    return log, restore


# --------------------------------------------------------------------------- #
# 2) Proxy                                                                     #
# --------------------------------------------------------------------------- #


class TestBearingProxy(unittest.TestCase):
    def _proxy_obj(self):
        from freecad_backend.workbench.wb_bearing import UniBearingProxy

        obj = _FakeFeature()
        proxy = UniBearingProxy(obj)
        return proxy, obj

    def test_adds_all_properties_with_defaults(self):
        _, obj = self._proxy_obj()
        self.assertEqual(set(obj._types), uischema.schema_names())
        self.assertEqual(str(obj.bearing_type), "BALL")
        self.assertAlmostEqual(float(obj.bore_diameter), 20.0)
        self.assertEqual(int(obj.element_count), 10)

    def test_initial_visibility_hides_irrelevant_fields(self):
        _, obj = self._proxy_obj()
        # BALL: Kontaktwinkel versteckt (2), Geometrie sichtbar (0).
        self.assertEqual(obj._editor["contact_angle_deg"], 2)
        self.assertEqual(obj._editor["bore_diameter"], 0)
        self.assertEqual(obj._editor["groove_conformity_inner"], 0)

    def test_params_from_obj_roundtrips_defaults(self):
        from freecad_backend.workbench.wb_bearing import params_from_obj

        _, obj = self._proxy_obj()
        self.assertEqual(params_from_obj(obj), BearingParams())

    def test_onchanged_type_updates_visibility(self):
        proxy, obj = self._proxy_obj()
        obj.bearing_type = "TAPERED"
        proxy.onChanged(obj, "bearing_type")
        self.assertEqual(obj._editor["contact_angle_deg"], 0)
        self.assertEqual(obj._editor["groove_conformity_inner"], 2)

    def test_execute_builds_shape(self):
        proxy, obj = self._proxy_obj()
        log, restore = _install_fakes()
        try:
            proxy.execute(obj)
        finally:
            restore()
        self.assertIsNotNone(obj.Shape)
        self.assertGreaterEqual(log.count("makeSphere"), 3)  # Kugellager
        self.assertIn("makeCompound", log)

    def test_make_bearing_creates_and_recomputes(self):
        from freecad_backend.workbench import wb_bearing

        log, restore = _install_fakes()
        try:
            obj = wb_bearing.make_bearing()
        finally:
            restore()
        self.assertIsNotNone(obj.Proxy)
        self.assertEqual(set(obj._types), uischema.schema_names())
        self.assertIsNotNone(obj.Shape)  # recompute() rief execute()


# --------------------------------------------------------------------------- #
# 3) Command + InitGui                                                         #
# --------------------------------------------------------------------------- #


class TestCommands(unittest.TestCase):
    def test_register_commands(self):
        from freecad_backend.workbench import wb_commands

        gui = types.ModuleType("FreeCADGui")
        added = {}
        gui.addCommand = lambda name, cmd: added.__setitem__(name, cmd)
        saved = sys.modules.get("FreeCADGui")
        sys.modules["FreeCADGui"] = gui
        try:
            ids = wb_commands.register_commands()
        finally:
            if saved is None:
                sys.modules.pop("FreeCADGui", None)
            else:
                sys.modules["FreeCADGui"] = saved
        self.assertEqual(ids, [wb_commands.CATALOG_COMMAND, wb_commands.CREATE_COMMAND])
        self.assertIn(wb_commands.CREATE_COMMAND, added)
        self.assertIn(wb_commands.CATALOG_COMMAND, added)

    def test_command_resources_and_activate(self):
        from freecad_backend.workbench.wb_commands import CreateBearingCommand

        cmd = CreateBearingCommand()
        res = cmd.GetResources()
        self.assertEqual(res["MenuText"], "Lager erzeugen")
        self.assertTrue(res["Pixmap"].endswith("bearing.svg"))
        self.assertTrue(cmd.IsActive())

        log, restore = _install_fakes()
        try:
            cmd.Activated()  # darf ohne Fehler ein Dokument+Objekt anlegen
        finally:
            restore()
        self.assertIn("makeCompound", log)

    def test_initgui_initialize_wires_toolbar_and_menu(self):
        init_gui = ROOT / "InitGui.py"
        src = init_gui.read_text(encoding="utf-8")

        registered = []
        added = {}

        class _Workbench:
            def appendToolbar(self, name, cmds):
                self.__dict__.setdefault("_toolbars", {})[name] = cmds

            def appendMenu(self, name, cmds):
                self.__dict__.setdefault("_menus", {})[name] = cmds

        gui = types.ModuleType("FreeCADGui")
        gui.Workbench = _Workbench
        gui.addWorkbench = lambda wb: registered.append(wb)
        gui.addCommand = lambda name, cmd: added.__setitem__(name, cmd)

        saved = sys.modules.get("FreeCADGui")
        sys.modules["FreeCADGui"] = gui
        try:
            code = compile(src, str(init_gui), "exec")
            g, l = {}, {}
            exec(code, g, l)
            self.assertEqual(len(registered), 1)
            wb = registered[0]
            wb.Initialize()
        finally:
            if saved is None:
                sys.modules.pop("FreeCADGui", None)
            else:
                sys.modules["FreeCADGui"] = saved

        from freecad_backend.workbench.wb_commands import CREATE_COMMAND, CATALOG_COMMAND

        expected = [CATALOG_COMMAND, CREATE_COMMAND]
        self.assertIn(CREATE_COMMAND, added)
        self.assertIn(CATALOG_COMMAND, added)
        self.assertEqual(wb.__dict__["_toolbars"]["UNI Bearings"], expected)
        self.assertEqual(wb.__dict__["_menus"]["UNI Bearings"], expected)


# --------------------------------------------------------------------------- #
# 4) Host-freier Katalog-Helfer                                               #
# --------------------------------------------------------------------------- #


class TestCatalog(unittest.TestCase):
    def test_bearing_type_choices_cover_constants(self):
        from freecad_backend import catalog

        ids = [bid for bid, _label, _desc in catalog.bearing_type_choices()]
        self.assertEqual(ids, [bid for bid, _l, _d in constants.BEARING_TYPES])

    def test_series_codes_sorted_and_nonempty(self):
        from freecad_backend import catalog

        codes = catalog.series_codes(constants.BALL)
        self.assertIn("6204", codes)
        self.assertEqual(codes, sorted(codes))

    def test_preset_dims_known_and_unknown(self):
        from freecad_backend import catalog

        self.assertIsNotNone(catalog.preset_dims(constants.BALL, "6204"))
        self.assertIsNone(catalog.preset_dims(constants.BALL, "NOPE"))

    def test_apply_preset_sets_main_dims_and_defaults(self):
        from freecad_backend import catalog

        d, D, B = catalog.preset_dims(constants.BALL, "6204")
        params = catalog.apply_preset(BearingParams(), constants.BALL, "6204")
        self.assertEqual(params.bearing_type, constants.BALL)
        self.assertAlmostEqual(params.bore_diameter, d)
        self.assertAlmostEqual(params.outer_diameter, D)
        self.assertAlmostEqual(params.width, B)
        # Wälzkörper-Defaults wurden katalognah nachgezogen.
        self.assertGreater(params.roller_diameter, 0.0)
        self.assertGreaterEqual(params.element_count, 3)

    def test_apply_preset_tapered_sets_cone_cup_widths(self):
        from freecad_backend import catalog

        codes = catalog.series_codes(constants.TAPERED)
        params = catalog.apply_preset(BearingParams(), constants.TAPERED, codes[0])
        self.assertEqual(params.bearing_type, constants.TAPERED)
        self.assertGreater(params.tapered_cone_width_mm, 0.0)

    def test_apply_preset_unknown_keeps_dims_but_sets_type(self):
        from freecad_backend import catalog

        base = BearingParams()
        params = catalog.apply_preset(base, constants.SPHERICAL, "NOPE")
        self.assertEqual(params.bearing_type, constants.SPHERICAL)
        self.assertAlmostEqual(params.bore_diameter, base.bore_diameter)

    def test_coding_matches_norm_engine(self):
        from freecad_backend import catalog
        from uni_rolling_bearing import norm_engine

        self.assertEqual(catalog.coding_for(constants.BALL), "din623")
        self.assertEqual(catalog.coding_for(constants.NEEDLE), "direct")
        for bid, _l, _d in constants.BEARING_TYPES:
            self.assertEqual(catalog.coding_for(bid), norm_engine.coding_for(bid))

    def test_din623_series_bore_combine_to_known_preset(self):
        from freecad_backend import catalog

        series = catalog.mass_series_for(constants.BALL)
        self.assertIn("62", series)
        bores = catalog.bore_codes_for(constants.BALL, "62")
        self.assertIn("04", bores)
        code = catalog.combined_code("62", "04")
        self.assertEqual(code, "6204")
        self.assertIsNotNone(catalog.preset_dims(constants.BALL, code))

    def test_direct_types_have_no_mass_series(self):
        from freecad_backend import catalog

        self.assertEqual(catalog.mass_series_for(constants.NEEDLE), [])
        self.assertEqual(catalog.bore_codes_for(constants.NEEDLE, ""), [])

    def test_norm_hint_nonempty_for_all_types(self):
        from freecad_backend import catalog

        for bid, _l, _d in constants.BEARING_TYPES:
            self.assertTrue(catalog.norm_hint_for(bid))

    def test_miniature_skateboard_bearing_available(self):
        from freecad_backend import catalog

        # Reihe 60 bietet die einstellige Bohrungskennzahl "8" → 608.
        bores = catalog.bore_codes_for(constants.BALL, "60")
        self.assertIn("8", bores)
        self.assertEqual(catalog.combined_code("60", "8"), "608")
        self.assertEqual(catalog.preset_dims(constants.BALL, "608"), (8.0, 22.0, 7.0))
        params = catalog.apply_preset(BearingParams(), constants.BALL, "608")
        self.assertAlmostEqual(params.bore_diameter, 8.0)
        self.assertAlmostEqual(params.outer_diameter, 22.0)
        self.assertGreater(params.element_count, 0)

    def test_precision_and_tolerance_choices_cover_norm(self):
        from freecad_backend import catalog
        from uni_rolling_bearing.tolerances import TOLERANCE_POSITIONS

        prec_ids = [pid for pid, _l, _d in catalog.precision_class_choices()]
        self.assertEqual(prec_ids, [pid for pid, _l, _d in constants.PRECISION_CLASSES])
        tol_ids = [tid for tid, _l, _d in catalog.tolerance_position_choices()]
        self.assertEqual(tol_ids, [tid for tid, _l, _d in TOLERANCE_POSITIONS])

    def test_tolerance_offset_text_blank_for_upper_position(self):
        from freecad_backend import catalog

        # Lage „oberes Maß" (MAX) = Nennmaß → keine Offsets → leerer String.
        self.assertEqual(catalog.tolerance_offset_text(20.0, 47.0, 14.0, "NORMAL", "MAX"), "")
        # Mittenmaß bei enger Klasse erzeugt eine sichtbare Offset-Zeile.
        text = catalog.tolerance_offset_text(20.0, 47.0, 14.0, "P4", "MIN")
        self.assertIn("Δd=", text)
        self.assertIn("µm", text)


if __name__ == "__main__":
    unittest.main()
