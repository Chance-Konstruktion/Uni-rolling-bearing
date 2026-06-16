"""Qualitäts-/Regressionstests für saubere, funktionsfähige Wälzlager.

Diese Suite prüft *ohne* laufendes Blender, dass die erzeugten Lager
geometrisch sauber sind, d. h. dass

1. **Kugellager** korrekt nach der DIN-625-Rillenformel ausgelegt werden
   (Kugel = Schulterspalt + innere + äußere Rillentiefe − Lagerluft) und damit
   in beide Rillen eintauchen statt zwischen den Schultern zu schweben –
   inklusive katalognaher Kugel-Ø und Kugelzahlen;
2. die Kugel real in die Laufbahn-Rille passt (Rille schneidet sichtbar unter
   die Schulter, Kugel nestelt mit Bodenspiel) – Konsistenz Sizing ↔ Laufbahn;
3. **alle Lagertypen** über alle Norm-Presets revolvier-fähige (manifold-taugliche)
   Querschnittsprofile liefern: geschlossene Polylinien mit ``r > 0`` und ohne
   aufeinanderfolgende Doppelpunkte – die Voraussetzung dafür, dass
   ``make_revolved_ring`` ein geschlossenes, manifold Mesh erzeugt.
"""

from __future__ import annotations

import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from uni_rolling_bearing import constants, raceway  # noqa: E402
from uni_rolling_bearing.geometry import (  # noqa: E402
    BALL_GROOVE_CONFORMITY_INNER,
    BALL_GROOVE_CONFORMITY_OUTER,
    BALL_GROOVE_DEPTH_FRACTION_INNER,
    BALL_GROOVE_DEPTH_FRACTION_OUTER,
    MIN_BALL_WALL_MM,
    ball_diameter_from_groove,
    compute_dims,
    is_ball_type,
    resolve_geometry,
    suggest_defaults,
)


# --------------------------------------------------------------------------- #
# Hilfen                                                                       #
# --------------------------------------------------------------------------- #


def _is_clean_revolve_profile(points, tol=1e-9):
    """Sauberes Revolve-Profil: ≥3 Punkte, alle ``r > 0``, keine Doppelpunkte.

    Liefert ``(ok, reason)``. ``r > 0`` ist zwingend, sonst kollabiert der
    revolvierte Ring auf der Drehachse (nicht-manifold). Aufeinanderfolgende
    identische Punkte (inkl. Schließkante letzter→erster) erzeugen
    Null-Flächen.
    """
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


def _resolve_for(bearing_type, d, big_d, b):
    """Wie das Addon: typgerechte Defaults vorschlagen und auflösen."""
    s = suggest_defaults(bearing_type, d, big_d)
    spec, error = resolve_geometry(
        bearing_type=bearing_type,
        bore_diameter=d,
        outer_diameter=big_d,
        width=b,
        ring_thickness=s.ring_thickness,
        roller_diameter=s.roller_diameter,
        element_count=s.element_count,
        radial_clearance=0.02,
        gap_factor=0.10,
        auto_fit=True,
    )
    return s, spec, error


# Reale Katalog-Referenzen (SKF/FAG) für Rillenkugellager: Kugel-Ø und Kugelzahl.
# d, D, B, Kugel-Ø[mm], Kugelzahl.
BALL_REFERENCE = [
    ("6204", 20.0, 47.0, 14.0, 7.94, 8),
    ("6206", 30.0, 62.0, 16.0, 9.53, 9),
    ("6304", 20.0, 52.0, 15.0, 9.53, 7),
    ("6306", 30.0, 72.0, 19.0, 11.91, 8),
]


# --------------------------------------------------------------------------- #
# 1) Kugel-Sizing nach der DIN-625-Rillenformel                               #
# --------------------------------------------------------------------------- #


class TestBallGrooveFormula(unittest.TestCase):
    def test_formula_matches_closed_form(self):
        # d_w = (Spalt − 2·Luft) / (1 − e_i − e_o)
        radial_space = 6.3
        clr = 0.02
        d_w = ball_diameter_from_groove(radial_space=radial_space, radial_clearance=clr)
        denom = 1.0 - BALL_GROOVE_DEPTH_FRACTION_INNER - BALL_GROOVE_DEPTH_FRACTION_OUTER
        self.assertAlmostEqual(d_w, (radial_space - 2.0 * clr) / denom, places=9)

    def test_ball_is_larger_than_shoulder_gap(self):
        # Kern des Fixes: die Kugel ist GRÖSSER als der reine Schulterspalt,
        # weil sie in beide Rillen eintaucht (vorher war sie ~0.95·Spalt → zu klein).
        radial_space = 6.3
        d_w = ball_diameter_from_groove(radial_space=radial_space, radial_clearance=0.02)
        self.assertGreater(d_w, radial_space)

    def test_zero_depth_reduces_to_gap(self):
        # Ohne Rillentiefe entartet die Formel zum reinen (luftbereinigten) Spalt.
        d_w = ball_diameter_from_groove(
            radial_space=6.3, radial_clearance=0.0,
            depth_fraction_inner=0.0, depth_fraction_outer=0.0,
        )
        self.assertAlmostEqual(d_w, 6.3, places=9)

    def test_more_depth_grows_ball(self):
        base = ball_diameter_from_groove(radial_space=6.0, radial_clearance=0.0)
        deeper = ball_diameter_from_groove(
            radial_space=6.0, radial_clearance=0.0,
            depth_fraction_inner=0.15, depth_fraction_outer=0.15,
        )
        self.assertGreater(deeper, base)


class TestBallSizingRealism(unittest.TestCase):
    def test_catalog_ball_diameter_and_count(self):
        for code, d, big_d, b, real_ball, real_n in BALL_REFERENCE:
            with self.subTest(code=code):
                _s, spec, error = _resolve_for(constants.BALL, d, big_d, b)
                self.assertIsNone(error, msg=f"{code}: {error}")
                # Kugel-Ø innerhalb 10 % des Katalogwerts.
                self.assertAlmostEqual(
                    spec.roller_d, real_ball, delta=0.10 * real_ball,
                    msg=f"{code}: Kugel-Ø {spec.roller_d:.2f} ≠ ~{real_ball}",
                )
                # Kugelzahl katalognah (±2 Kugeln).
                self.assertGreaterEqual(spec.element_count, real_n - 2, msg=f"{code} n zu klein")
                self.assertLessEqual(spec.element_count, real_n + 2, msg=f"{code} n zu groß")

    def test_ball_exceeds_shoulder_gap_for_all_ball_presets(self):
        presets = constants.SERIES_PRESETS.get(constants.BALL, {})
        self.assertTrue(presets)
        for code, (d, big_d, b) in presets.items():
            with self.subTest(code=code):
                s, spec, error = _resolve_for(constants.BALL, d, big_d, b)
                self.assertIsNone(error, msg=f"{code}: {error}")
                dims = compute_dims(d, big_d, s.ring_thickness)
                # Kugel taucht in die Rillen ein → Ø größer als der Schulterspalt.
                self.assertGreater(spec.roller_d, dims.radial_space, msg=f"{code}")

    def test_ball_stays_within_ring_walls_for_all_presets(self):
        presets = constants.SERIES_PRESETS.get(constants.BALL, {})
        for code, (d, big_d, b) in presets.items():
            with self.subTest(code=code):
                _s, spec, error = _resolve_for(constants.BALL, d, big_d, b)
                self.assertIsNone(error, msg=f"{code}: {error}")
                pitch_r = spec.pitch_d * 0.5
                inner_groove_bottom = pitch_r - BALL_GROOVE_CONFORMITY_INNER * spec.roller_d
                outer_groove_bottom = pitch_r + BALL_GROOVE_CONFORMITY_OUTER * spec.roller_d
                # Restwand bis Bohrung/Außenmantel bleibt erhalten.
                self.assertGreaterEqual(
                    inner_groove_bottom, d * 0.5 + MIN_BALL_WALL_MM - 1e-6,
                    msg=f"{code}: Innenrille durchsticht Bohrung",
                )
                self.assertLessEqual(
                    outer_groove_bottom, big_d * 0.5 - MIN_BALL_WALL_MM + 1e-6,
                    msg=f"{code}: Außenrille durchsticht Außenmantel",
                )


# --------------------------------------------------------------------------- #
# 2) Konsistenz Kugel-Sizing ↔ Laufbahn-Rille                                 #
# --------------------------------------------------------------------------- #


class TestBallNestlesInRaceGroove(unittest.TestCase):
    """Die ausgelegte Kugel muss tatsächlich in die gezeichnete Rille passen."""

    def _check(self, d, big_d, b, code):
        _s, spec, error = _resolve_for(constants.BALL, d, big_d, b)
        self.assertIsNone(error, msg=f"{code}: {error}")
        pitch_r = spec.pitch_d * 0.5
        shoulder_r_in = spec.inner_outer_d * 0.5
        shoulder_r_out = spec.outer_inner_d * 0.5

        inner = raceway.ball_inner_ring_profile(
            bore_d=d, shoulder_d=spec.inner_outer_d, width=b,
            ball_d=spec.roller_d, pitch_d=spec.pitch_d,
        )
        outer = raceway.ball_outer_ring_profile(
            shoulder_d=spec.outer_inner_d, outer_d=big_d, width=b,
            ball_d=spec.roller_d, pitch_d=spec.pitch_d,
        )
        for prof, name in ((inner, "inner"), (outer, "outer")):
            ok, reason = _is_clean_revolve_profile(prof)
            self.assertTrue(ok, msg=f"{code} {name}: {reason}")

        # Innenring: Rille schneidet sichtbar unter die Schulter.
        self.assertTrue(
            any(r < shoulder_r_in - 1e-3 for r, z in inner),
            msg=f"{code}: Innenrille nicht sichtbar",
        )
        # Außenring: Rille wölbt sich über die Schulter nach außen.
        self.assertTrue(
            any(r > shoulder_r_out + 1e-3 for r, z in outer),
            msg=f"{code}: Außenrille nicht sichtbar",
        )

        # Kugel nestelt: innerer/äußerer Kugel-Pol liegt JENSEITS der Schulter
        # (taucht ein), aber innerhalb des Rillenbodens (Bodenspiel vorhanden).
        ball_inner_pole = pitch_r - spec.roller_d * 0.5
        ball_outer_pole = pitch_r + spec.roller_d * 0.5
        inner_groove_bottom = pitch_r - BALL_GROOVE_CONFORMITY_INNER * spec.roller_d
        outer_groove_bottom = pitch_r + BALL_GROOVE_CONFORMITY_OUTER * spec.roller_d
        self.assertLess(ball_inner_pole, shoulder_r_in, msg=f"{code}: Kugel taucht innen nicht ein")
        self.assertGreater(ball_outer_pole, shoulder_r_out, msg=f"{code}: Kugel taucht außen nicht ein")
        self.assertGreater(ball_inner_pole, inner_groove_bottom, msg=f"{code}: kein Bodenspiel innen")
        self.assertLess(ball_outer_pole, outer_groove_bottom, msg=f"{code}: kein Bodenspiel außen")

    def test_reference_ball_bearings_nestle(self):
        for code, d, big_d, b, _ball, _n in BALL_REFERENCE:
            with self.subTest(code=code):
                self._check(d, big_d, b, code)


# --------------------------------------------------------------------------- #
# 3) Saubere Profile für ALLE Lagertypen über ALLE Presets                    #
# --------------------------------------------------------------------------- #


class TestAllTypesCleanProfiles(unittest.TestCase):
    """Jeder Lagertyp liefert über alle Presets revolvier-fähige Profile."""

    def _profiles(self, bt, d, big_d, b, spec):
        if is_ball_type(bt):
            inner = raceway.ball_inner_ring_profile(
                bore_d=d, shoulder_d=spec.inner_outer_d, width=b,
                ball_d=spec.roller_d, pitch_d=spec.pitch_d,
            )
            if bt == constants.VGROOVE:
                outer = raceway.vgroove_outer_ring_profile(
                    shoulder_d=spec.outer_inner_d, outer_d=big_d, width=b,
                    ball_d=spec.roller_d, pitch_d=spec.pitch_d,
                )
            else:
                outer = raceway.ball_outer_ring_profile(
                    shoulder_d=spec.outer_inner_d, outer_d=big_d, width=b,
                    ball_d=spec.roller_d, pitch_d=spec.pitch_d,
                )
            return [("inner", inner), ("outer", outer)]
        if bt in (constants.CYLINDRICAL, constants.NEEDLE):
            inner = raceway.cylindrical_inner_ring_profile(
                bore_d=d, shoulder_d=spec.inner_outer_d, width=b,
            )
            outer = raceway.cylindrical_outer_ring_profile(
                shoulder_d=spec.outer_inner_d, outer_d=big_d, width=b,
                roller_length=spec.roller_length, roller_d=spec.roller_d,
            )
            return [("inner", inner), ("outer", outer)]
        if bt == constants.TAPERED:
            angle = math.radians(14.0)
            inner = raceway.tapered_inner_ring_profile(
                bore_d=d, shoulder_d=spec.inner_outer_d, width=b,
                contact_angle_rad=angle, large_flange_height_mm=1.0,
            )
            outer = raceway.tapered_outer_ring_profile(
                shoulder_d=spec.outer_inner_d, outer_d=big_d, width=b,
                contact_angle_rad=angle,
            )
            return [("inner", inner), ("outer", outer)]
        if bt == constants.SPHERICAL:
            outer = raceway.spherical_outer_ring_profile(
                shoulder_d=spec.outer_inner_d, outer_d=big_d, width=b,
                pitch_d=spec.pitch_d, roller_d=spec.roller_d,
            )
            results = [("outer", outer)]
            for rows in (1, 2):
                inner = raceway.spherical_inner_ring_profile(
                    bore_d=d, shoulder_d=spec.inner_outer_d, width=b,
                    pitch_d=spec.pitch_d, roller_d=spec.roller_d,
                    roller_length=spec.roller_length,
                    contact_angle_rad=math.radians(10.0), rows=rows,
                )
                results.append((f"inner_rows{rows}", inner))
            return results
        return []

    def test_every_type_every_preset_yields_clean_profiles(self):
        any_checked = False
        for bt, presets in constants.SERIES_PRESETS.items():
            for code, (d, big_d, b) in presets.items():
                _s, spec, error = _resolve_for(bt, d, big_d, b)
                with self.subTest(type=bt, preset=code):
                    self.assertIsNone(error, msg=f"{bt}/{code}: {error}")
                    self.assertGreaterEqual(spec.element_count, 3)
                    self.assertGreater(spec.roller_d, 0.0)
                    for name, prof in self._profiles(bt, d, big_d, b, spec):
                        any_checked = True
                        ok, reason = _is_clean_revolve_profile(prof)
                        self.assertTrue(ok, msg=f"{bt}/{code} {name}: {reason}")
        self.assertTrue(any_checked, "Keine Profile geprüft – Preset-Katalog leer?")


class TestRollerTypesFitWithinRaces(unittest.TestCase):
    """Rollen (kein Rillen-Sizing) bleiben zwischen den Schultern."""

    def test_rollers_do_not_exceed_shoulders(self):
        roller_types = (constants.CYLINDRICAL, constants.NEEDLE, constants.TAPERED, constants.SPHERICAL)
        for bt in roller_types:
            presets = constants.SERIES_PRESETS.get(bt, {})
            for code, (d, big_d, b) in presets.items():
                with self.subTest(type=bt, preset=code):
                    _s, spec, error = _resolve_for(bt, d, big_d, b)
                    self.assertIsNone(error, msg=f"{bt}/{code}: {error}")
                    pitch_r = spec.pitch_d * 0.5
                    # Rollen-Querschnitt bleibt innerhalb der Laufbahn-Schultern.
                    self.assertLessEqual(
                        pitch_r + spec.roller_d * 0.5, spec.outer_inner_d * 0.5 + 1e-6,
                        msg=f"{bt}/{code}: Rolle ragt in den Außenring",
                    )
                    self.assertGreaterEqual(
                        pitch_r - spec.roller_d * 0.5, spec.inner_outer_d * 0.5 - 1e-6,
                        msg=f"{bt}/{code}: Rolle ragt in den Innenring",
                    )


if __name__ == "__main__":
    unittest.main()
