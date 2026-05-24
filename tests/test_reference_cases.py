"""Referenzfälle gegen ISO-15-/Katalogwerte.

Drei Ebenen:

1. **Maße** – die ausgelieferten Presets müssen exakt den veröffentlichten
   ISO 15 / DIN 616-Hauptmaßen (d, D, B) entsprechen. Das verankert die
   JSON-Datenbasis gegen Tippfehler.
2. **Wälzkörper-Anzahl** – für Kegel- und Pendelrollenlager muss die
   abgeleitete Rollenzahl im realen Katalogbereich liegen (Regression für
   die v0.24-Sizing-Korrektur).
3. **Tragzahlen** – C0r/Cr dürfen nur um einen *dokumentierten Faktor* von
   den Katalogwerten abweichen. Das Modell ist bewusst vereinfacht (siehe
   README), daher sind die Schranken weit; sie fangen grobe Formelfehler und
   Größenordnungs-Regressionen ab, nicht die normale Näherungsabweichung.
"""

from __future__ import annotations

import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from uni_rolling_bearing import constants, ratings  # noqa: E402
from uni_rolling_bearing.geometry import resolve_geometry, suggest_defaults  # noqa: E402


def _resolve(bearing_type: str, d: float, big_d: float, b: float):
    """Wie das Addon: Defaults vorschlagen und auflösen (mit Auto-Fit)."""
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
    return spec, error


# (Lagertyp, Code, d, D, B) – Sollmaße nach ISO 15 / DIN 616 / DIN 720 / DIN 635.
REFERENCE_DIMENSIONS = [
    (constants.BALL, "6204", 20.0, 47.0, 14.0),
    (constants.BALL, "6206", 30.0, 62.0, 16.0),
    (constants.BALL, "6304", 20.0, 52.0, 15.0),
    (constants.BALL, "6306", 30.0, 72.0, 19.0),
    (constants.BALL, "6008", 40.0, 68.0, 15.0),
    (constants.TAPERED, "30206", 30.0, 62.0, 17.25),
    (constants.TAPERED, "30306", 30.0, 72.0, 20.75),
    (constants.SPHERICAL, "22210", 50.0, 90.0, 23.0),
    (constants.SPHERICAL, "22310", 50.0, 110.0, 40.0),
]


class TestReferenceDimensions(unittest.TestCase):
    def test_presets_match_published_dimensions(self):
        for bearing_type, code, d, big_d, b in REFERENCE_DIMENSIONS:
            with self.subTest(code=code):
                preset = constants.SERIES_PRESETS.get(bearing_type, {}).get(code)
                self.assertIsNotNone(preset, f"{code} fehlt im Preset-Katalog")
                p_d, p_big_d, p_b = preset
                self.assertAlmostEqual(p_d, d, places=2, msg=f"{code}: d")
                self.assertAlmostEqual(p_big_d, big_d, places=2, msg=f"{code}: D")
                self.assertAlmostEqual(p_b, b, places=2, msg=f"{code}: B")


# (Lagertyp, Code, d, D, B, min_n, max_n) – Katalog-Rollenzahl (pro Reihe bei
# Pendelrollenlagern) mit Toleranzband. Das Sizing-Modell soll in diesem
# Bereich landen; die Bänder sind so gewählt, dass sie die realen Werte
# (30206≈17, 30306≈14, 22210≈14/Reihe, 22310≈14/Reihe) einschließen.
REFERENCE_COUNTS = [
    (constants.TAPERED, "30206", 30.0, 62.0, 17.25, 13, 21),
    (constants.TAPERED, "30306", 30.0, 72.0, 20.75, 11, 18),
    (constants.SPHERICAL, "22210", 50.0, 90.0, 23.0, 12, 24),
    (constants.SPHERICAL, "22310", 50.0, 110.0, 40.0, 11, 19),
]


class TestRollerCountRealism(unittest.TestCase):
    def test_roller_count_in_catalog_range(self):
        for bearing_type, code, d, big_d, b, lo, hi in REFERENCE_COUNTS:
            with self.subTest(code=code):
                spec, error = _resolve(bearing_type, d, big_d, b)
                self.assertIsNone(error, msg=f"{code}: {error}")
                self.assertGreaterEqual(spec.element_count, lo, msg=f"{code} n zu klein")
                self.assertLessEqual(spec.element_count, hi, msg=f"{code} n zu groß")


# (Lagertyp, Code, d, D, B, C0r_kN, Cr_kN) – Katalog-Richtwerte (SKF/FAG).
REFERENCE_RATINGS = [
    (constants.BALL, "6204", 20.0, 47.0, 14.0, 6.55, 12.7),
    (constants.BALL, "6206", 30.0, 62.0, 16.0, 11.2, 19.5),
]
# Erlaubter Faktor model/Katalog. Das vereinfachte Modell überschätzt aktuell
# um ~1.3–1.6×; die Schranken lassen Luft, fangen aber Größenordnungsfehler.
C0_FACTOR_BOUNDS = (0.5, 2.5)
CR_FACTOR_BOUNDS = (0.5, 2.5)


class TestRatingsAgainstCatalog(unittest.TestCase):
    def test_ratings_within_documented_factor(self):
        for bearing_type, code, d, big_d, b, c0_kn, cr_kn in REFERENCE_RATINGS:
            with self.subTest(code=code):
                spec, error = _resolve(bearing_type, d, big_d, b)
                self.assertIsNone(error, msg=f"{code}: {error}")
                r = ratings.compute_ratings(
                    bearing_type=bearing_type,
                    roller_d_mm=spec.roller_d,
                    roller_length_mm=spec.roller_length,
                    element_count=spec.element_count,
                    pitch_d_mm=spec.pitch_d,
                )
                c0_ratio = (r.static_C0_N / 1000.0) / c0_kn
                cr_ratio = (r.dynamic_C_N / 1000.0) / cr_kn
                self.assertGreaterEqual(c0_ratio, C0_FACTOR_BOUNDS[0], msg=f"{code} C0r zu klein")
                self.assertLessEqual(c0_ratio, C0_FACTOR_BOUNDS[1], msg=f"{code} C0r zu groß")
                self.assertGreaterEqual(cr_ratio, CR_FACTOR_BOUNDS[0], msg=f"{code} Cr zu klein")
                self.assertLessEqual(cr_ratio, CR_FACTOR_BOUNDS[1], msg=f"{code} Cr zu groß")


class TestVGrooveShapeVariant(unittest.TestCase):
    """U-Profil-Variante der SG-Außenrille (v0.24)."""

    def _profile(self, shape: str):
        from uni_rolling_bearing import raceway

        return raceway.vgroove_outer_ring_profile(
            shoulder_d=30.0,
            outer_d=40.0,
            width=11.0,
            ball_d=5.0,
            pitch_d=27.0,
            groove_shape=shape,
        )

    def test_both_shapes_yield_valid_revolve_profiles(self):
        for shape in ("V", "U"):
            prof = self._profile(shape)
            with self.subTest(shape=shape):
                self.assertGreaterEqual(len(prof), 3)
                self.assertTrue(all(r > 0.0 for r, _ in prof), "r>0 für Revolve nötig")
                self.assertTrue(all(math.isfinite(r) and math.isfinite(z) for r, z in prof))

    def test_u_shape_is_rounded_with_more_points(self):
        v = self._profile("V")
        u = self._profile("U")
        # Der Kosinus-Bogen der U-Rille bringt mehr Stützpunkte als die
        # 3-Punkt-V-Kerbe.
        self.assertGreater(len(u), len(v))
        # Beide Rillen haben dieselbe Tiefe → gleicher minimaler OD-Rillengrund.
        outer_r = 20.0
        u_groove_min = min(r for r, z in u if abs(z) < 5.0 and r < outer_r - 1e-6)
        v_groove_min = min(r for r, z in v if abs(z) < 5.0 and r < outer_r - 1e-6)
        self.assertAlmostEqual(u_groove_min, v_groove_min, delta=0.25)


if __name__ == "__main__":
    unittest.main()
