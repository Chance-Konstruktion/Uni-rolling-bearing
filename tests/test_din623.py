"""Tests für DIN 623 Bohrungskennzahl und Maßreihen-Generator."""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from uni_rolling_bearing import constants, din623  # noqa: E402


class TestBoreCode(unittest.TestCase):
    def test_special_codes(self):
        self.assertEqual(din623.bore_code_to_diameter("00"), 10.0)
        self.assertEqual(din623.bore_code_to_diameter("01"), 12.0)
        self.assertEqual(din623.bore_code_to_diameter("02"), 15.0)
        self.assertEqual(din623.bore_code_to_diameter("03"), 17.0)

    def test_regular_codes_multiply_by_five(self):
        self.assertEqual(din623.bore_code_to_diameter("04"), 20.0)
        self.assertEqual(din623.bore_code_to_diameter("20"), 100.0)
        self.assertEqual(din623.bore_code_to_diameter("96"), 480.0)

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            din623.bore_code_to_diameter("97")


class TestPresetGeneration(unittest.TestCase):
    def test_ball_presets_include_known_sizes(self):
        ball = constants.SERIES_PRESETS[constants.BALL]
        self.assertEqual(ball["6000"], (10.0, 26.0, 8.0))
        self.assertEqual(ball["6204"], (20.0, 47.0, 14.0))
        self.assertEqual(ball["6306"], (30.0, 72.0, 19.0))
        self.assertEqual(ball["61804"], (20.0, 37.0, 9.0))

    def test_ball_preset_count_covers_main_series(self):
        ball = constants.SERIES_PRESETS[constants.BALL]
        # 60/62/63 jeweils 21 Größen + 64 (6) + 618 (9) + 619 (7) = 79
        self.assertGreaterEqual(len(ball), 70)

    def test_d_consistent_with_bore_code(self):
        for code, (d, _D, _B) in constants.SERIES_PRESETS[constants.BALL].items():
            bore_code = code[-2:]
            self.assertAlmostEqual(d, din623.bore_code_to_diameter(bore_code))

    def test_d_less_than_D(self):
        for type_, table in constants.SERIES_PRESETS.items():
            for code, (d, D, B) in table.items():
                self.assertLess(d, D, msg=f"{type_}/{code}: d ≥ D")
                self.assertGreater(B, 0.0)


if __name__ == "__main__":
    unittest.main()
