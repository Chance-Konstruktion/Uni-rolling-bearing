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
    cage_dimensions,
    compute_dims,
    max_elements_for_pitch,
    resolve_geometry,
    roller_length_for_type,
    suggest_defaults,
    tapered_apex_z,
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


class TestSuggestDefaults(unittest.TestCase):
    def test_resolves_without_auto_fit_for_all_presets(self):
        # Vorgeschlagene Defaults dürfen den Resolver auch ohne Auto-Fit nicht
        # in einen Fehler laufen lassen.
        for type_id, presets in constants.SERIES_PRESETS.items():
            for code, (d, big_d, b) in presets.items():
                suggestion = suggest_defaults(type_id, d, big_d)
                spec, error = resolve_geometry(
                    bearing_type=type_id,
                    bore_diameter=d,
                    outer_diameter=big_d,
                    width=b,
                    ring_thickness=suggestion.ring_thickness,
                    roller_diameter=suggestion.roller_diameter,
                    element_count=suggestion.element_count,
                    radial_clearance=0.02,
                    gap_factor=0.10,
                    auto_fit=False,
                )
                with self.subTest(type=type_id, preset=code):
                    self.assertIsNone(error, msg=f"{type_id}/{code}: {error}")
                    self.assertGreaterEqual(spec.element_count, 3)

    def test_min_ring_thickness(self):
        # Sehr enges Lager – Ringstärke darf nicht unter dem harten Minimum liegen.
        s = suggest_defaults(constants.NEEDLE, 10.0, 11.0)
        self.assertGreaterEqual(s.ring_thickness, 0.5)

    def test_max_ring_thickness_capped(self):
        # Sehr breites Lager – Ringstärke wird gedeckelt, statt unsinnig groß zu werden.
        s = suggest_defaults(constants.BALL, 20.0, 200.0)
        self.assertLessEqual(s.ring_thickness, 8.0)

    def test_degenerate_input_does_not_raise(self):
        s = suggest_defaults(constants.BALL, 30.0, 20.0)
        self.assertGreater(s.ring_thickness, 0.0)
        self.assertGreater(s.roller_diameter, 0.0)
        self.assertGreaterEqual(s.element_count, 3)


class TestCageDimensions(unittest.TestCase):
    def _resolve_default(self, **overrides):
        spec, error = resolve_geometry(**_base_kwargs(**overrides))
        self.assertIsNone(error)
        return spec

    def test_basic_cage_fits(self):
        spec = self._resolve_default()
        cage = cage_dimensions(
            pitch_d=spec.pitch_d,
            roller_d=spec.roller_d,
            roller_length=spec.roller_length,
            width=14.0,
            element_count=spec.element_count,
            inner_race_d=spec.inner_outer_d,
            outer_race_d=spec.outer_inner_d,
        )
        self.assertIsNotNone(cage)
        self.assertGreater(cage.plate_thickness, 0.0)
        # Endplatte muss innerhalb der Lagerstirnflächen liegen.
        self.assertLess(cage.plate_z_offset + cage.plate_thickness * 0.5, 14.0 * 0.5)
        # Plattenring überspannt die Pitch-Linie und bleibt zwischen den Laufbahnen.
        self.assertLess(cage.plate_inner_d, spec.pitch_d)
        self.assertGreater(cage.plate_outer_d, spec.pitch_d)
        self.assertGreaterEqual(cage.plate_inner_d, spec.inner_outer_d)
        self.assertLessEqual(cage.plate_outer_d, spec.outer_inner_d)
        self.assertEqual(cage.web_count, spec.element_count)

    def test_no_axial_room_returns_none(self):
        # Eine Nadel füllt fast die ganze Breite – kein Platz für Endplatten.
        spec = self._resolve_default(bearing_type=constants.NEEDLE)
        cage = cage_dimensions(
            pitch_d=spec.pitch_d,
            roller_d=spec.roller_d,
            roller_length=spec.roller_length,
            width=spec.roller_length + 0.05,
            element_count=spec.element_count,
            inner_race_d=spec.inner_outer_d,
            outer_race_d=spec.outer_inner_d,
        )
        self.assertIsNone(cage)

    def test_too_many_elements_blocks_webs(self):
        # Wälzkörper dicht an dicht ⇒ kein Tangentialspalt für Webs.
        spec = self._resolve_default()
        cage = cage_dimensions(
            pitch_d=spec.pitch_d,
            roller_d=spec.roller_d,
            roller_length=spec.roller_length,
            width=14.0,
            element_count=200,
            inner_race_d=spec.inner_outer_d,
            outer_race_d=spec.outer_inner_d,
        )
        self.assertIsNone(cage)

    def test_plate_stays_clear_of_races(self):
        spec = self._resolve_default()
        cage = cage_dimensions(
            pitch_d=spec.pitch_d,
            roller_d=spec.roller_d,
            roller_length=spec.roller_length,
            width=14.0,
            element_count=spec.element_count,
            inner_race_d=spec.inner_outer_d,
            outer_race_d=spec.outer_inner_d,
        )
        self.assertIsNotNone(cage)
        # Plattenfenster überschreitet den Wälzkörper-Querschnitt nicht in die Laufbahn.
        self.assertGreater(cage.plate_inner_d, spec.inner_outer_d)
        self.assertLess(cage.plate_outer_d, spec.outer_inner_d)

    def test_invalid_inputs_return_none(self):
        defaults = dict(roller_length=10.0, width=14.0, inner_race_d=15.0, outer_race_d=45.0)
        self.assertIsNone(
            cage_dimensions(pitch_d=0.0, roller_d=5.0, element_count=10, **defaults)
        )
        self.assertIsNone(
            cage_dimensions(pitch_d=30.0, roller_d=5.0, element_count=2, **defaults)
        )
        # Ringe in falscher Reihenfolge.
        self.assertIsNone(
            cage_dimensions(
                pitch_d=30.0, roller_d=5.0, roller_length=10.0, width=14.0,
                element_count=10, inner_race_d=45.0, outer_race_d=15.0,
            )
        )


class TestTaperedApex(unittest.TestCase):
    def test_zero_angle_returns_neg_inf(self):
        # Achsen sind dann parallel zur Lagerachse – kein endlicher Apex.
        self.assertEqual(tapered_apex_z(35.0, 12.0, 0.0), float("-inf"))

    def test_negative_angle_returns_neg_inf(self):
        self.assertEqual(tapered_apex_z(35.0, 12.0, -0.1), float("-inf"))

    def test_apex_below_origin(self):
        # Mit positivem Winkel zeigt die Konvention den Apex unter z=0
        # (kleine Stirn radial nach innen, axial nach unten).
        z = tapered_apex_z(35.0, 12.0, math.radians(14.0))
        self.assertLess(z, 0.0)

    def test_apex_distance_matches_geometry(self):
        # Apex muss exakt auf der Verlängerung der kleinen-Stirn-Achse liegen:
        # Abstand vom kleinen Stirn-Mittelpunkt (pitch_r - sin α · L/2, 0, -cos α · L/2)
        # entlang Richtung (-sin α, 0, -cos α) ist (pitch_r - sin α · L/2)/sin α.
        pitch_d, length = 35.0, 12.0
        alpha = math.radians(20.0)
        z = tapered_apex_z(pitch_d, length, alpha)
        pitch_r = pitch_d * 0.5
        sin_a, cos_a = math.sin(alpha), math.cos(alpha)
        small_x = pitch_r - sin_a * length * 0.5
        small_z = -cos_a * length * 0.5
        expected = small_z - (small_x / sin_a) * cos_a
        self.assertAlmostEqual(z, expected)

    def test_steeper_angle_brings_apex_closer(self):
        # Bei steilerem Kontaktwinkel rückt der Apex näher an z=0.
        z_small = tapered_apex_z(35.0, 12.0, math.radians(10.0))
        z_large = tapered_apex_z(35.0, 12.0, math.radians(30.0))
        self.assertLess(z_small, z_large)


if __name__ == "__main__":
    unittest.main()
