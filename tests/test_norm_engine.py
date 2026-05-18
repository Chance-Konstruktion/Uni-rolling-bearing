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


class TestSeriesAndBoreCodes(unittest.TestCase):
    """Tests für den Workflow 'Reihe → Bohrungskennzahl'."""

    def test_coding_for_known_types(self):
        self.assertEqual(norm_engine.coding_for("BALL"), "din623")
        self.assertEqual(norm_engine.coding_for("CYLINDRICAL"), "din623")
        self.assertEqual(norm_engine.coding_for("TAPERED"), "din623")
        self.assertEqual(norm_engine.coding_for("SPHERICAL"), "din623")
        self.assertEqual(norm_engine.coding_for("NEEDLE"), "direct")
        self.assertEqual(norm_engine.coding_for("VGROOVE"), "direct")
        self.assertEqual(norm_engine.coding_for("DOES_NOT_EXIST"), "")

    def test_load_series_for_ball_returns_six_series(self):
        series = norm_engine.load_series_for("BALL")
        self.assertEqual(set(series), {"60", "62", "63", "64", "618", "619"})

    def test_load_series_for_cylindrical_includes_prefix(self):
        # CYLINDRICAL nutzt prefix='NU', sodass die Reihen NU2/NU3 lauten.
        series = norm_engine.load_series_for("CYLINDRICAL")
        self.assertEqual(set(series), {"NU2", "NU3"})

    def test_load_series_for_direct_coding_returns_empty(self):
        # Direct-Coding (z. B. NEEDLE) hat keine DIN 623-Reihen.
        self.assertEqual(norm_engine.load_series_for("NEEDLE"), [])
        self.assertEqual(norm_engine.load_series_for("VGROOVE"), [])

    def test_load_bore_codes_sorted_by_diameter(self):
        codes = norm_engine.load_bore_codes_for("BALL", "60")
        self.assertGreater(len(codes), 0)
        # Erste Einträge sind die Sonderkennzahlen 00..03 → d=10/12/15/17 mm,
        # danach 04 → 20 mm aufsteigend. Sortierung ist nach Bohrungs-Ø.
        self.assertEqual(codes[0], "00")
        self.assertEqual(codes[1], "01")
        self.assertEqual(codes[2], "02")
        self.assertEqual(codes[3], "03")
        self.assertEqual(codes[4], "04")

    def test_load_bore_codes_with_prefix(self):
        # series_code "NU2" muss das prefix korrekt strippen.
        codes = norm_engine.load_bore_codes_for("CYLINDRICAL", "NU2")
        self.assertIn("04", codes)
        self.assertIn("12", codes)

    def test_load_bore_codes_unknown_series_returns_empty(self):
        self.assertEqual(norm_engine.load_bore_codes_for("BALL", "99"), [])

    def test_load_bore_codes_for_direct_coding_returns_empty(self):
        self.assertEqual(norm_engine.load_bore_codes_for("NEEDLE", "62"), [])

    def test_combined_code_matches_preset(self):
        # Für jeden DIN 623-Typ muss jede Reihe+Kennzahl-Kombination in den
        # geladenen SERIES_PRESETS auflösbar sein.
        for bt in ("BALL", "CYLINDRICAL", "TAPERED", "SPHERICAL"):
            presets = norm_engine.load_presets_for(bt)
            for series in norm_engine.load_series_for(bt):
                for bore_code in norm_engine.load_bore_codes_for(bt, series):
                    full = f"{series}{bore_code}"
                    with self.subTest(type=bt, code=full):
                        self.assertIn(full, presets)


if __name__ == "__main__":
    unittest.main()
