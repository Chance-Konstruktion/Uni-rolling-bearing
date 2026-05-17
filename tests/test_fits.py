"""Tests für die Passungs-Empfehlung nach DIN 5418."""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from uni_rolling_bearing import fits  # noqa: E402


class TestShaftSelection(unittest.TestCase):
    def test_stationary_uses_slip_fit(self):
        r = fits.recommend_fits("STATIONARY", 20.0, 47.0)
        self.assertEqual(r.shaft_class, "h6")

    def test_outer_rotating_uses_loose_shaft(self):
        r = fits.recommend_fits("OUTER_ROT", 30.0, 62.0)
        self.assertEqual(r.shaft_class, "g6")
        self.assertEqual(r.housing_class, "N7")

    def test_normal_load_steps_up_with_diameter(self):
        small = fits.recommend_fits("INNER_ROT_NORMAL", 15.0, 35.0).shaft_class
        mid = fits.recommend_fits("INNER_ROT_NORMAL", 25.0, 52.0).shaft_class
        large = fits.recommend_fits("INNER_ROT_NORMAL", 80.0, 140.0).shaft_class
        bigger = fits.recommend_fits("INNER_ROT_NORMAL", 150.0, 270.0).shaft_class
        self.assertEqual(small, "j6")
        self.assertEqual(mid, "k5")
        self.assertEqual(large, "k6")
        self.assertEqual(bigger, "m6")

    def test_heavy_load_tightens(self):
        normal = fits.recommend_fits("INNER_ROT_NORMAL", 30.0, 62.0).shaft_class
        heavy = fits.recommend_fits("INNER_ROT_HEAVY", 30.0, 62.0).shaft_class
        self.assertEqual(normal, "k5")
        self.assertEqual(heavy, "k6")


class TestDeviations(unittest.TestCase):
    def test_k5_deviations_for_20mm_match_iso286(self):
        # 18..30 mm, k5 → +11/+2 µm
        r = fits.recommend_fits("INNER_ROT_NORMAL", 20.0, 47.0)
        self.assertEqual((r.shaft_upper_um, r.shaft_lower_um), (11, 2))

    def test_housing_j7_deviations_for_47mm(self):
        # 30..50 mm, J7 → +14/-11 µm
        r = fits.recommend_fits("INNER_ROT_NORMAL", 20.0, 47.0)
        self.assertEqual(r.housing_class, "J7")
        self.assertEqual((r.housing_upper_um, r.housing_lower_um), (14, -11))

    def test_out_of_range_returns_none(self):
        r = fits.recommend_fits("INNER_ROT_NORMAL", 500.0, 800.0)
        self.assertIsNone(r.shaft_upper_um)
        self.assertIsNone(r.housing_upper_um)
        # Klasse wird dennoch zugeordnet.
        self.assertTrue(r.shaft_class)
        self.assertTrue(r.housing_class)


if __name__ == "__main__":
    unittest.main()
