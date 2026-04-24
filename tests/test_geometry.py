"""Tests für die reine Geometrie-Schicht (laufen ohne Blender)."""

from __future__ import annotations

import math
import pathlib
import sys
import unittest

# Repo-Wurzel auf den Pfad legen, damit ``uni_rolling_bearing`` importierbar ist.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from uni_rolling_bearing import constants  # noqa: E402
from uni_rolling_bearing.geometry import (  # noqa: E402
    compute_dims,
    max_elements_for_pitch,
    resolve_geometry,
    roller_length_for_type,
)


def _base_kwargs(**overrides):
    """Plausible Default-Eingabe für resolve_geometry, einzeln überschreibbar."""
    base = dict(
        bearing_type=constants.BALL,
        bore_diameter=20.0,
        outer_diameter=47.0,
        width=14.0,
        ring_thickness=4.0,
        roller_diameter=7.0,
        element_count=10,
        radial_clearance=0.02,
        gap_factor=0.10,
        auto_fit=True,
    )
    base.update(overrides)
    return base


class TestComputeDims(unittest.TestCase):
    def test_basic_dims(self):
        dims = compute_dims(20.0, 47.0, 4.0)
        self.assertAlmostEqual(dims.inner_outer_d, 28.0)
        self.assertAlmostEqual(dims.outer_inner_d, 39.0)
        self.assertAlmostEqual(dims.radial_space, 11.0)

    def test_zero_radial_space(self):
        # bore=4, D=20, ring=4 → inner_outer=12, outer_inner=12, kein Spalt.
        dims = compute_dims(4.0, 20.0, 4.0)
        self.assertAlmostEqual(dims.radial_space, 0.0)


class TestMaxElementsForPitch(unittest.TestCase):
    def test_no_overlap_at_max(self):
        pitch = 30.0
        roller = 5.0
        gap = 0.10
        n = max_elements_for_pitch(pitch, roller, gap)
        # n Wälzkörper mit 10% Spalt müssen auf den Umfang passen.
        self.assertGreaterEqual(math.pi * pitch, n * roller * (1.0 + gap))

    def test_at_least_three(self):
        # Sehr enger Pitch / großer Roller – Funktion muss trotzdem ≥3 liefern.
        self.assertGreaterEqual(max_elements_for_pitch(1.0, 10.0, 0.0), 3)


class TestRollerLengthForType(unittest.TestCase):
    def test_ball_uses_diameter(self):
        self.assertEqual(roller_length_for_type(constants.BALL, 20.0, 7.0), 7.0)

    def test_needle_uses_ratio(self):
        self.assertAlmostEqual(
            roller_length_for_type(constants.NEEDLE, 20.0, 3.0),
            20.0 * constants.ROLLER_LENGTH_RATIO[constants.NEEDLE],
        )

    def test_unknown_falls_back_to_diameter(self):
        self.assertEqual(roller_length_for_type("UNKNOWN", 20.0, 7.0), 7.0)


class TestResolveGeometry(unittest.TestCase):
    def test_happy_path(self):
        spec, error = resolve_geometry(**_base_kwargs())
        self.assertIsNone(error)
        self.assertIsNotNone(spec)
        self.assertGreater(spec.roller_d, 0.0)
        self.assertGreaterEqual(spec.element_count, 3)
        self.assertAlmostEqual(spec.pitch_d, spec.inner_outer_d + spec.roller_d + 2 * 0.02)

    def test_bore_not_smaller_than_outer(self):
        spec, error = resolve_geometry(**_base_kwargs(bore_diameter=50.0, outer_diameter=47.0))
        self.assertIsNone(spec)
        self.assertIn("Innendurchmesser", error)

    def test_no_radial_space(self):
        # Ringstärke verschluckt den gesamten Spalt.
        spec, error = resolve_geometry(**_base_kwargs(ring_thickness=20.0))
        self.assertIsNone(spec)
        self.assertIn("Laufbahnspalt", error)

    def test_roller_too_large_without_auto_fit(self):
        spec, error = resolve_geometry(
            **_base_kwargs(roller_diameter=50.0, auto_fit=False)
        )
        self.assertIsNone(spec)
        self.assertIn("Wälzkörper-Ø", error)

    def test_roller_too_large_is_clamped_with_auto_fit(self):
        spec, error = resolve_geometry(**_base_kwargs(roller_diameter=50.0, auto_fit=True))
        self.assertIsNone(error)
        self.assertLess(spec.roller_d, 50.0)
        # radial_space = (47 - 2*4) - (20 + 2*4) = 11, Lagerluft 2*0.02 = 0.04.
        max_allowed = (11.0 - 0.04) * 0.98
        self.assertAlmostEqual(spec.roller_d, max_allowed, places=4)

    def test_too_many_elements_without_auto_fit(self):
        spec, error = resolve_geometry(
            **_base_kwargs(element_count=200, auto_fit=False)
        )
        self.assertIsNone(spec)
        self.assertIn("Wälzkörper", error)

    def test_too_many_elements_clamped_with_auto_fit(self):
        spec, error = resolve_geometry(**_base_kwargs(element_count=200, auto_fit=True))
        self.assertIsNone(error)
        self.assertLess(spec.element_count, 200)

    def test_clearance_eats_all_space(self):
        spec, error = resolve_geometry(**_base_kwargs(radial_clearance=10.0))
        self.assertIsNone(spec)
        self.assertIn("Lagerluft", error)

    def test_needle_length_uses_width_ratio(self):
        spec, _ = resolve_geometry(**_base_kwargs(bearing_type=constants.NEEDLE))
        self.assertAlmostEqual(
            spec.roller_length,
            14.0 * constants.ROLLER_LENGTH_RATIO[constants.NEEDLE],
        )


class TestPresets(unittest.TestCase):
    def test_every_bearing_type_has_norm_hint(self):
        for type_id, *_ in constants.BEARING_TYPES:
            self.assertIn(type_id, constants.NORM_HINTS)

    def test_presets_match_known_bearing_types(self):
        for type_id in constants.SERIES_PRESETS:
            self.assertIn(type_id, dict((t[0], t) for t in constants.BEARING_TYPES))

    def test_preset_dimensions_resolve(self):
        # Jedes Preset muss sich unter Auto-Fit mit einer angemessenen Ringstärke
        # lösen lassen (höchstens ein Viertel des verfügbaren Radials, mind. 0.5 mm).
        for type_id, presets in constants.SERIES_PRESETS.items():
            for code, (d, big_d, b) in presets.items():
                # Ringstärke ≈ 1/6 des äußeren Radial-Bereichs (typische Praxis).
                ring_thickness = max(0.5, min(4.0, (big_d - d) / 6.0))
                spec, error = resolve_geometry(
                    **_base_kwargs(
                        bearing_type=type_id,
                        bore_diameter=d,
                        outer_diameter=big_d,
                        width=b,
                        ring_thickness=ring_thickness,
                    )
                )
                with self.subTest(type=type_id, preset=code):
                    self.assertIsNone(error, msg=f"{type_id}/{code}: {error}")
                    self.assertGreater(spec.roller_d, 0.0)


if __name__ == "__main__":
    unittest.main()
