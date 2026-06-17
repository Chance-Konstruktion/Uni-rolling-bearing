"""Tests für den FreeCAD-Frontend – ohne laufendes FreeCAD.

Drei Ebenen, analog zur Skill-Erfahrung beim Uni-Pulley-Port:

1. **Host-freier Bauplan** (`freecad_backend.plan`): für jeden Lagertyp über
   reale Presets liefert der Plan revolvier-fähige Ringprofile (geschlossen,
   ``r > 0``, keine Doppelpunkte) und die erwartete Wälzkörperzahl. Das ist
   exakt dieselbe Sauberkeits-Bedingung wie für den Blender-Mesh.

2. **Part-Backend mit gemocktem ``Part``/``FreeCAD``**: ``build_bearing`` baut
   Ringe über **gerade Polygon-Revolve** (Blocker 6) – niemals BSpline – und
   erzeugt pro Typ die richtigen Wälzkörper-Primitive; Käfig-Pockets über
   Boolean-Cut.

3. **FreeCAD-Ausführungspfad von ``InitGui.py``** (Blocker 2/3): ohne
   ``__file__`` und mit getrennten globals/locals registriert sich die
   Workbench ohne ``NameError``.
"""

from __future__ import annotations

import math
import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from uni_rolling_bearing import constants  # noqa: E402
from freecad_backend import plan as plan_mod  # noqa: E402
from freecad_backend.params import BearingParams  # noqa: E402


def _is_clean_revolve_profile(points, tol=1e-9):
    """≥3 Punkte, alle ``r > 0``, finit, keine aufeinanderfolgenden Doppelpunkte."""
    if len(points) < 3:
        return False, f"nur {len(points)} Punkte"
    for r, z in points:
        if not (math.isfinite(r) and math.isfinite(z)):
            return False, f"nicht-finiter Punkt ({r}, {z})"
        if r <= 0.0:
            return False, f"r={r} ≤ 0 (kollabiert auf Achse)"
    ring = list(points) + [points[0]]
    for (r0, z0), (r1, z1) in zip(ring, ring[1:]):
        if abs(r0 - r1) <= tol and abs(z0 - z1) <= tol:
            return False, f"Doppelpunkt bei ({r0}, {z0})"
    return True, "ok"


# (Lagertyp, d, D, B) – reale Hauptmaße je Typ.
_PRESETS = [
    (constants.BALL, 20.0, 47.0, 14.0),
    (constants.BALL, 10.0, 30.0, 9.0),
    (constants.VGROOVE, 17.0, 40.0, 12.0),
    (constants.CYLINDRICAL, 25.0, 52.0, 15.0),
    (constants.NEEDLE, 20.0, 32.0, 20.0),
    (constants.TAPERED, 30.0, 62.0, 17.25),
    (constants.SPHERICAL, 30.0, 72.0, 19.0),
]


def _params(bt, d, big_d, b, **extra) -> BearingParams:
    p = BearingParams(bearing_type=bt, bore_diameter=d, outer_diameter=big_d, width=b)
    for k, v in extra.items():
        setattr(p, k, v)
    return p.apply_suggested_defaults()


# --------------------------------------------------------------------------- #
# 1) Host-freier Bauplan                                                       #
# --------------------------------------------------------------------------- #


class TestBuildPlan(unittest.TestCase):
    def test_rings_are_clean_revolve_profiles(self):
        for bt, d, big_d, b in _PRESETS:
            with self.subTest(type=bt, d=d):
                plan = plan_mod.build_plan(_params(bt, d, big_d, b))
                self.assertIsNone(plan.error, f"{bt}: {plan.error}")
                for label, ring in (("inner", plan.inner_ring), ("outer", plan.outer_ring)):
                    self.assertIsNotNone(ring, f"{bt}: {label} fehlt")
                    ok, reason = _is_clean_revolve_profile(ring.profile)
                    self.assertTrue(ok, f"{bt} {label}-Ring: {reason}")

    def test_element_count_matches_spec(self):
        for bt, d, big_d, b in _PRESETS:
            with self.subTest(type=bt, d=d):
                p = _params(bt, d, big_d, b)
                plan = plan_mod.build_plan(p)
                self.assertGreaterEqual(plan.spec.element_count, 3)
                self.assertEqual(len(plan.elements), plan.spec.element_count)

    def test_spherical_two_row_doubles_elements(self):
        p = _params(constants.SPHERICAL, 30.0, 72.0, 19.0, spherical_rows="2")
        plan = plan_mod.build_plan(p)
        self.assertEqual(len(plan.elements), 2 * plan.spec.element_count)
        for el in plan.elements:
            self.assertIsInstance(el, plan_mod.Barrel)

    def test_element_types_per_bearing(self):
        cases = {
            constants.BALL: plan_mod.Ball,
            constants.VGROOVE: plan_mod.Ball,
            constants.CYLINDRICAL: plan_mod.Roller,
            constants.NEEDLE: plan_mod.Roller,
            constants.TAPERED: plan_mod.Roller,
            constants.SPHERICAL: plan_mod.Barrel,
        }
        for bt, expected in cases.items():
            with self.subTest(type=bt):
                d, big_d, b = 30.0, 72.0, 19.0
                plan = plan_mod.build_plan(_params(bt, d, big_d, b))
                self.assertTrue(all(isinstance(e, expected) for e in plan.elements))

    def test_cage_pocket_plan_has_cutters(self):
        p = _params(constants.BALL, 20.0, 47.0, 14.0, use_cage=True, cage_style="POCKET")
        plan = plan_mod.build_plan(p)
        self.assertEqual(plan.cage_style, "pocket")
        self.assertEqual(len(plan.cage_parts), 1)
        self.assertEqual(len(plan.cage_parts[0].cutters), plan.spec.element_count)

    def test_invalid_geometry_returns_error(self):
        # Bohrung ≥ Außen-Ø ist unlösbar.
        p = BearingParams(bearing_type=constants.BALL, bore_diameter=50.0,
                          outer_diameter=40.0, width=12.0)
        plan = plan_mod.build_plan(p)
        self.assertIsNotNone(plan.error)
        self.assertIsNone(plan.spec)


# --------------------------------------------------------------------------- #
# 2) Part-Backend mit gemocktem FreeCAD/Part                                   #
# --------------------------------------------------------------------------- #


class _FakeShape:
    def __init__(self, log, kind):
        self._log = log
        self.kind = kind
        self.Placement = None

    def revolve(self, *a):
        self._log.append("revolve")
        return _FakeShape(self._log, "solid")

    def cut(self, other):
        self._log.append("cut")
        return _FakeShape(self._log, "cut")


def _install_fake_freecad():
    """Installiert minimal gemockte ``Part``- und ``FreeCAD``-Module.

    Liefert (call_log, restore) – ``call_log`` ist eine Liste der ausgelösten
    ``Part``-Operationen; ``restore()`` entfernt die Mocks wieder.
    """
    log = []

    part = types.ModuleType("Part")
    part.makePolygon = lambda pts: (log.append("makePolygon"), _FakeShape(log, "wire"))[1]
    part.Face = lambda wire: (log.append("Face"), _FakeShape(log, "face"))[1]
    part.makeSphere = lambda r: (log.append("makeSphere"), _FakeShape(log, "sphere"))[1]
    part.makeCone = lambda r1, r2, h: (log.append("makeCone"), _FakeShape(log, "cone"))[1]
    part.makeBox = lambda sx, sy, sz, base=None: (log.append("makeBox"), _FakeShape(log, "box"))[1]
    part.makeCompound = lambda shapes: (log.append("makeCompound"), _FakeShape(log, "compound"))[1]
    # Bewusst KEINE BSpline-Helfer – ein Aufruf würde sofort als AttributeError
    # auffallen und genau den Blocker-6-Fehler markieren.

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
    fc.Vector = _Vec
    fc.Rotation = _Rot
    fc.Placement = _Plc

    saved = {name: sys.modules.get(name) for name in ("Part", "FreeCAD")}
    sys.modules["Part"] = part
    sys.modules["FreeCAD"] = fc

    def restore():
        for name, mod in saved.items():
            if mod is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod

    return log, restore


class TestPartBackend(unittest.TestCase):
    def _build(self, params):
        log, restore = _install_fake_freecad()
        try:
            from freecad_backend import backend_freecad

            result = backend_freecad.build_bearing(params)
        finally:
            restore()
        return result, log

    def test_rings_use_polygon_not_bspline(self):
        # Blocker 6: gerade Polygonkanten, exakt wie der Blender-Mesh.
        for bt, d, big_d, b in _PRESETS:
            with self.subTest(type=bt):
                _, log = self._build(_params(bt, d, big_d, b))
                self.assertGreaterEqual(log.count("makePolygon"), 2,
                                        "Innen-/Außenring müssen revolvierte Polygone sein")
                self.assertNotIn("BSpline", " ".join(log))

    def test_ball_bearing_builds_spheres(self):
        result, log = self._build(_params(constants.BALL, 20.0, 47.0, 14.0))
        self.assertIsNotNone(result.inner_ring)
        self.assertIsNotNone(result.outer_ring)
        n = len(result.elements)
        self.assertEqual(log.count("makeSphere"), n)
        self.assertEqual(log.count("makeCone"), 0)

    def test_tapered_bearing_builds_cones(self):
        result, log = self._build(_params(constants.TAPERED, 30.0, 62.0, 17.25))
        self.assertEqual(log.count("makeCone"), len(result.elements))
        self.assertEqual(log.count("makeSphere"), 0)

    def test_cage_pockets_use_boolean_cut(self):
        params = _params(constants.BALL, 20.0, 47.0, 14.0, use_cage=True, cage_style="POCKET")
        result, log = self._build(params)
        self.assertEqual(len(result.cage), 1)
        self.assertGreaterEqual(log.count("cut"), 1)

    def test_invalid_geometry_raises(self):
        bad = BearingParams(bearing_type=constants.BALL, bore_diameter=50.0,
                            outer_diameter=40.0, width=12.0)
        with self.assertRaises(ValueError):
            self._build(bad)


# --------------------------------------------------------------------------- #
# 3) InitGui.py-Ausführungspfad (Blocker 2/3)                                  #
# --------------------------------------------------------------------------- #


class TestInitGuiExecPath(unittest.TestCase):
    def test_registers_without_file_and_split_namespaces(self):
        init_gui = ROOT / "InitGui.py"
        src = init_gui.read_text(encoding="utf-8")

        registered = []

        class _Workbench:  # gemockte FreeCADGui.Workbench-Basis
            pass

        fake_gui = types.ModuleType("FreeCADGui")
        fake_gui.Workbench = _Workbench
        fake_gui.addWorkbench = lambda wb: registered.append(wb)

        saved = sys.modules.get("FreeCADGui")
        sys.modules["FreeCADGui"] = fake_gui
        try:
            # Echter Dateiname beim Kompilieren, damit der inspect-Fallback
            # (Blocker 2) einen Pfad findet; getrennte globals/locals (Blocker 3).
            code = compile(src, str(init_gui), "exec")
            g, l = {}, {}
            exec(code, g, l)  # darf nicht NameError werfen
        finally:
            if saved is None:
                sys.modules.pop("FreeCADGui", None)
            else:
                sys.modules["FreeCADGui"] = saved

        self.assertEqual(len(registered), 1, "Workbench wurde nicht registriert")
        wb = registered[0]
        self.assertTrue(str(getattr(wb, "Icon", "")).endswith("bearing.svg"))
        self.assertEqual(wb.MenuText, "UNI Bearings")


if __name__ == "__main__":
    unittest.main()
