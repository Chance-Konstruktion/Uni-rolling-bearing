"""Tests für die Tragzahlen- und Lebensdauerberechnung."""

from __future__ import annotations

import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from uni_rolling_bearing import constants, ratings  # noqa: E402


class TestStaticRating(unittest.TestCase):
    def test_ball_uses_diameter_squared(self):
        c0 = ratings.static_load_rating(constants.BALL, 7.0, 0.0, 10, 0.0)
        self.assertAlmostEqual(c0, 14.7 * 10 * 49.0, places=3)

    def test_roller_uses_length_times_diameter(self):
        c0 = ratings.static_load_rating(constants.CYLINDRICAL, 6.0, 10.0, 12, 0.0)
        self.assertAlmostEqual(c0, 44.0 * 12 * 10.0 * 6.0, places=3)

    def test_spherical_has_two_rows(self):
        single = ratings.static_load_rating(constants.CYLINDRICAL, 6.0, 10.0, 12)
        twin = ratings.static_load_rating(constants.SPHERICAL, 6.0, 10.0, 12)
        expected = single * 2.0 * math.cos(math.radians(10.0))
        self.assertAlmostEqual(twin, expected, places=3)

    def test_zero_inputs_return_zero(self):
        self.assertEqual(ratings.static_load_rating(constants.BALL, 0.0, 0.0, 10), 0.0)
        self.assertEqual(ratings.static_load_rating(constants.BALL, 7.0, 0.0, 0), 0.0)
        self.assertEqual(ratings.static_load_rating(constants.NEEDLE, 4.0, 0.0, 10), 0.0)


class TestDynamicRating(unittest.TestCase):
    def test_ball_scales_with_diameter_to_1_8(self):
        small = ratings.dynamic_load_rating(constants.BALL, 5.0, 0.0, 10)
        large = ratings.dynamic_load_rating(constants.BALL, 10.0, 0.0, 10)
        self.assertAlmostEqual(large / small, 2.0 ** 1.8, places=3)

    def test_roller_scales_with_count_to_three_quarters(self):
        few = ratings.dynamic_load_rating(constants.CYLINDRICAL, 6.0, 10.0, 8)
        many = ratings.dynamic_load_rating(constants.CYLINDRICAL, 6.0, 10.0, 16)
        self.assertAlmostEqual(many / few, 2.0 ** 0.75, places=3)


class TestLife(unittest.TestCase):
    def test_no_load_returns_none(self):
        self.assertIsNone(ratings.nominal_life_hours(10000.0, 0.0, 1000.0, 3.0))
        self.assertIsNone(ratings.nominal_life_hours(10000.0, 500.0, 0.0, 3.0))

    def test_l10_uses_exponent_three_for_ball(self):
        h = ratings.nominal_life_hours(20000.0, 2000.0, 1500.0, 3.0)
        self.assertAlmostEqual(h, (10.0 ** 3) * 1.0e6 / (60.0 * 1500.0), places=3)

    def test_compute_ratings_sets_l10(self):
        r = ratings.compute_ratings(
            bearing_type=constants.BALL,
            roller_d_mm=7.0,
            roller_length_mm=7.0,
            element_count=10,
            equivalent_load_P_N=500.0,
            speed_rpm=1500.0,
        )
        self.assertGreater(r.static_C0_N, 0.0)
        self.assertGreater(r.dynamic_C_N, 0.0)
        self.assertIsNotNone(r.L10h)
        self.assertEqual(r.life_exponent, 3.0)


if __name__ == "__main__":
    unittest.main()
