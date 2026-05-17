"""Tests für die neuen Kegelrollen-Reihen und getrennte Cone-/Cup-Breite."""

from __future__ import annotations

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from uni_rolling_bearing import constants, norm_engine  # noqa: E402


class TestNewSeries(unittest.TestCase):
    def test_series_313_present(self):
        tapered = constants.SERIES_PRESETS[constants.TAPERED]
        self.assertIn("31304", tapered)
        self.assertIn("31310", tapered)
        d, D, T = tapered["31306"]
        self.assertEqual((d, D, T), (30.0, 72.0, 20.75))

    def test_series_320_322_323_present(self):
        tapered = constants.SERIES_PRESETS[constants.TAPERED]
        for code in ("32008", "32208", "32308"):
            self.assertIn(code, tapered)

    def test_total_count_increased(self):
        tapered = constants.SERIES_PRESETS[constants.TAPERED]
        # 302 (9) + 303 (9) + 313 (7) + 320 (7) + 322 (7) + 323 (7) = 46
        self.assertGreaterEqual(len(tapered), 40)


class TestRingWidths(unittest.TestCase):
    def test_widths_loaded_for_tapered(self):
        widths = norm_engine.load_ring_widths_for(constants.TAPERED)
        self.assertIn("30206", widths)
        B, C = widths["30206"]
        self.assertEqual((B, C), (16.0, 14.0))

    def test_widths_empty_for_ball(self):
        # Ball-JSON enthält keine 4-Tupel.
        self.assertEqual(norm_engine.load_ring_widths_for(constants.BALL), {})

    def test_new_series_have_widths(self):
        widths = norm_engine.load_ring_widths_for(constants.TAPERED)
        for code in ("31304", "32004", "32204", "32304"):
            self.assertIn(code, widths)
            B, C = widths[code]
            self.assertGreater(B, C)


if __name__ == "__main__":
    unittest.main()
