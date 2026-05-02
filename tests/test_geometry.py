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
    validate_against_suggestion,
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
        # Radiale Spaltbreite (nicht Durchmesser-Differenz!).
        self.assertAlmostEqual(dims.radial_space, 5.5)

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
        # Wälzkörper sitzen mittig zwischen den Laufbahnen.
        self.assertAlmostEqual(
            spec.pitch_d, (spec.inner_outer_d + spec.outer_inner_d) * 0.5
        )

    def test_roller_does_not_clip_outer_race(self):
        # Selbst bei maximalem Wälzkörper-Ø darf der äußere Punkt der Rolle
        # nicht in den Außenring ragen.
        spec, error = resolve_geometry(
            **_base_kwargs(roller_diameter=50.0, auto_fit=True)
        )
        self.assertIsNone(error)
        outer_extent = spec.pitch_d * 0.5 + spec.roller_d * 0.5
        self.assertLessEqual(outer_extent, spec.outer_inner_d * 0.5 + 1e-6)
        inner_extent = spec.pitch_d * 0.5 - spec.roller_d * 0.5
        self.assertGreaterEqual(inner_extent, spec.inner_outer_d * 0.5 - 1e-6)

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
        # Radiale Spaltbreite = ((47 - 2·4) - (20 + 2·4)) / 2 = 5.5 mm,
        # abzgl. Lagerluft 2·0.02 = 0.04 mm.
        max_allowed = (5.5 - 0.04) * 0.98
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

    def test_type_specific_ratios_differ(self):
        # Nadellager sollen dünnere Ringe und schlankere Wälzkörper bekommen
        # als ein Kugellager bei gleichen Hauptmaßen.
        ball = suggest_defaults(constants.BALL, 30.0, 72.0)
        needle = suggest_defaults(constants.NEEDLE, 30.0, 72.0)
        self.assertLess(needle.ring_thickness, ball.ring_thickness)
        # Nadeln füllen den Spalt anteilig stärker → größerer Roller-Ø trotz
        # dünnerer Ringe ist plausibel; aber Anzahl muss in beiden Fällen ≥ 3.
        self.assertGreaterEqual(needle.element_count, 3)
        self.assertGreaterEqual(ball.element_count, 3)


class TestValidateAgainstSuggestion(unittest.TestCase):
    def _kwargs(self, **overrides):
        base = dict(
            bearing_type=constants.BALL,
            bore_diameter=20.0,
            outer_diameter=47.0,
            ring_thickness=4.5,
            roller_diameter=2.5,
            element_count=10,
            radial_clearance=0.02,
            gap_factor=0.10,
        )
        base.update(overrides)
        return base

    def test_suggestion_validates_itself(self):
        s = suggest_defaults(constants.BALL, 20.0, 47.0)
        ok, hint = validate_against_suggestion(
            **self._kwargs(
                ring_thickness=s.ring_thickness,
                roller_diameter=s.roller_diameter,
                element_count=s.element_count,
            )
        )
        self.assertTrue(ok, msg=hint)

    def test_far_off_values_flagged(self):
        ok, hint = validate_against_suggestion(
            **self._kwargs(ring_thickness=0.5, roller_diameter=0.5, element_count=3)
        )
        self.assertFalse(ok)
        self.assertIn("Vorschlag", hint)


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


def _is_simple_closed_profile(points, tol=1e-9):
    """Liefert ``True``, wenn das Profil ≥3 Punkte hat und keine zwei
    aufeinanderfolgenden Punkte identisch sind. Reicht als Sanity-Check für die
    Revolutions-Eingabe; topologische Selbstschnitte werden hier nicht geprüft."""
    if len(points) < 3:
        return False
    for (r, _), (rn, _) in zip(points, points[1:]):
        if rn < 0:
            return False
    for a, b in zip(points, points[1:] + [points[0]]):
        if abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol:
            return False
    return True


class TestRacewayProfiles(unittest.TestCase):
    """Profile sind reine Geometrie – ohne Blender testbar."""

    def test_ball_inner_profile_carves_groove(self):
        from uni_rolling_bearing import raceway

        profile = raceway.ball_inner_ring_profile(
            bore_d=20.0,
            shoulder_d=29.0,
            width=14.0,
            ball_d=5.2,
            pitch_d=33.5,
        )
        self.assertTrue(_is_simple_closed_profile(profile))
        rs = [r for r, _ in profile]
        zs = [z for _, z in profile]
        self.assertAlmostEqual(min(rs), 10.0, places=6)        # Bohrungswand
        self.assertAlmostEqual(max(rs), 14.5, places=6)        # Schulterhöhe
        # Mindestens ein Punkt liegt strikt unter der Schulterhöhe → Rille ist sichtbar.
        self.assertTrue(any(r < 14.5 - 1e-3 for r, z in profile if abs(z) < 7.0 - 1e-3))
        # Achsensymmetrisch um z=0.
        self.assertAlmostEqual(min(zs), -7.0, places=6)
        self.assertAlmostEqual(max(zs), 7.0, places=6)

    def test_ball_inner_profile_falls_back_on_undersized_ball(self):
        from uni_rolling_bearing import raceway

        # Sehr kleine Kugel – Rillenbogen reicht die Schulter nicht ⇒ Hohlzylinder.
        profile = raceway.ball_inner_ring_profile(
            bore_d=20.0,
            shoulder_d=29.0,
            width=14.0,
            ball_d=1.0,
            pitch_d=33.5,
        )
        self.assertEqual(len(profile), 4)  # Rechteck-Querschnitt
        rs = sorted({round(r, 6) for r, _ in profile})
        self.assertEqual(rs, [10.0, 14.5])

    def test_ball_outer_profile_carves_groove(self):
        from uni_rolling_bearing import raceway

        profile = raceway.ball_outer_ring_profile(
            shoulder_d=38.0,
            outer_d=47.0,
            width=14.0,
            ball_d=5.2,
            pitch_d=33.5,
        )
        self.assertTrue(_is_simple_closed_profile(profile))
        rs = [r for r, _ in profile]
        self.assertAlmostEqual(min(rs), 19.0, places=6)        # Schulter-Innenhöhe
        self.assertAlmostEqual(max(rs), 23.5, places=6)        # Außen-Ø
        # Rille bauchst NACH AUSSEN (größerer r als Schulter) auf der Innenseite.
        self.assertTrue(any(19.0 + 1e-3 < r < 23.5 - 1e-3 for r, z in profile if abs(z) < 7.0 - 1e-3))

    def test_cylindrical_outer_profile_has_two_bord_steps(self):
        from uni_rolling_bearing import raceway

        profile = raceway.cylindrical_outer_ring_profile(
            shoulder_d=42.0,
            outer_d=47.0,
            width=14.0,
            roller_length=11.0,
            roller_d=5.0,
        )
        self.assertTrue(_is_simple_closed_profile(profile))
        rs = sorted({round(r, 4) for r, _ in profile})
        # Drei distinkte radiale Niveaus: Bord-Innenkante, Schulter (Laufbahn),
        # Außenmantel.
        self.assertEqual(len(rs), 3)
        bord_inner_r, shoulder_r, outer_r = rs
        self.assertLess(bord_inner_r, shoulder_r)
        self.assertLess(shoulder_r, outer_r)

    def test_cylindrical_outer_profile_fallbacks_when_no_room(self):
        from uni_rolling_bearing import raceway

        # Rolle füllt die Breite quasi voll → kein Bord möglich.
        profile = raceway.cylindrical_outer_ring_profile(
            shoulder_d=42.0,
            outer_d=47.0,
            width=10.0,
            roller_length=9.95,
            roller_d=5.0,
        )
        self.assertEqual(len(profile), 4)

    def test_tapered_profile_tapers_in_consistent_direction(self):
        from uni_rolling_bearing import raceway

        inner = raceway.tapered_inner_ring_profile(
            bore_d=20.0,
            shoulder_d=30.0,
            width=15.25,
            contact_angle_rad=math.radians(14.0),
        )
        outer = raceway.tapered_outer_ring_profile(
            shoulder_d=40.0,
            outer_d=47.0,
            width=15.25,
            contact_angle_rad=math.radians(14.0),
        )
        for prof in (inner, outer):
            self.assertTrue(_is_simple_closed_profile(prof))

        # Innenring: Außenfläche-r am +z-Ende größer als am -z-Ende.
        r_at_minus = max(r for r, z in inner if abs(z + 15.25 / 2) < 1e-6)
        r_at_plus = max(r for r, z in inner if abs(z - 15.25 / 2) < 1e-6)
        self.assertGreater(r_at_plus, r_at_minus)
        # Außenring: Innenfläche-r am +z-Ende größer als am -z-Ende.
        r_at_minus_o = min(r for r, z in outer if abs(z + 15.25 / 2) < 1e-6)
        r_at_plus_o = min(r for r, z in outer if abs(z - 15.25 / 2) < 1e-6)
        self.assertGreater(r_at_plus_o, r_at_minus_o)

    def test_spherical_outer_profile_is_curved(self):
        from uni_rolling_bearing import raceway

        profile = raceway.spherical_outer_ring_profile(
            shoulder_d=51.33,
            outer_d=62.0,
            width=20.0,
            pitch_d=46.0,
            roller_d=3.71,
        )
        self.assertTrue(_is_simple_closed_profile(profile))
        # Innenfläche am Mittelpunkt steht weiter aus der Achse als an den Rändern
        # (sphärisch nach außen gewölbt).
        r_mid = max(r for r, z in profile if abs(z) < 1e-6)
        r_edges = min(r for r, z in profile if abs(abs(z) - 10.0) < 1e-6)
        self.assertGreater(r_mid, r_edges + 0.1)


if __name__ == "__main__":
    unittest.main()
