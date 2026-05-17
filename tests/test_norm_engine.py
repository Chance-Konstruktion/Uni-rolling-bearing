"""Tests für die JSON-basierte Norm-Engine."""

from __future__ import annotations

import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from uni_rolling_bearing import norm_engine  # noqa: E402


class TestExpand(unittest.TestCase):
    def test_din623_expansion_uses_bore_code(self):
        payload = {
            "coding": "din623",
            "series": {"62": {"04": [47.0, 14.0]}},
        }
        result = norm_engine._expand(payload)
        self.assertEqual(result, {"6204": (20.0, 47.0, 14.0)})

    def test_din623_with_prefix(self):
        payload = {
            "coding": "din623",
            "prefix": "NU",
            "series": {"3": {"06": [72.0, 19.0]}},
        }
        result = norm_engine._expand(payload)
        self.assertEqual(result, {"NU306": (30.0, 72.0, 19.0)})

    def test_direct_passes_three_tuple(self):
        payload = {
            "coding": "direct",
            "presets": {"HK1010": [10.0, 14.0, 10.0]},
        }
        result = norm_engine._expand(payload)
        self.assertEqual(result, {"HK1010": (10.0, 14.0, 10.0)})

    def test_unknown_coding_returns_empty(self):
        self.assertEqual(norm_engine._expand({"coding": "ufo"}), {})

    def test_malformed_entries_are_skipped(self):
        payload = {
            "coding": "din623",
            "series": {"60": {"04": [42.0]}},  # zu kurz
        }
        self.assertEqual(norm_engine._expand(payload), {})


class TestLoaderIntegration(unittest.TestCase):
    def test_load_all_presets_covers_six_types(self):
        all_presets = norm_engine.load_all_presets()
        self.assertEqual(
            set(all_presets),
            {"BALL", "CYLINDRICAL", "NEEDLE", "TAPERED", "SPHERICAL", "VGROOVE"},
        )
        for bt, table in all_presets.items():
            self.assertGreater(len(table), 0, msg=f"{bt} ist leer")

    def test_missing_file_returns_empty(self):
        self.assertEqual(norm_engine.load_presets_for("DOES_NOT_EXIST"), {})

    def test_norm_hint_for_ball(self):
        self.assertIn("DIN 625", norm_engine.norm_hint_for("BALL"))


if __name__ == "__main__":
    unittest.main()
