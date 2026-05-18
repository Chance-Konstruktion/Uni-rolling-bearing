"""Tests für die Tragzahlen- und Lebensdauerberechnung."""

from __future__ import annotations

import math
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from uni_rolling_bearing import constants, ratings  # noqa: E402


class TestGamma(unittest.TestCase):
    def test_gamma_uses_pitch_diameter(self):
        # γ = Dw·cos(α) / dm
        g = ratings.gamma(roller_d_mm=5.0, contact_angle_rad=0.0, pitch_d_mm=25.0)
        self.assertAlmostEqual(g, 0.2)

    def test_gamma_with_contact_angle(self):
        g = ratings.gamma(
            roller_d_mm=10.0,
            contact_angle_rad=math.radians(14.0),
            pitch_d_mm=50.0,
        )
        self.assertAlmostEqual(g, 10.0 * math.cos(math.radians(14.0)) / 50.0)

    def test_gamma_zero_pitch_returns_zero(self):
        self.assertEqual(ratings.gamma(5.0, 0.0, 0.0), 0.0)


class TestF0Fc(unittest.TestCase):
    def test_f0_ball_hits_table_value(self):
        # γ = 0.10 → f0_ball = 13.7 (ISO 76 Annex).
        self.assertAlmostEqual(ratings.f0_for(constants.BALL, 0.10), 13.7)

    def test_fc_ball_hits_table_value(self):
        # γ = 0.20 → fc_ball = 59.9 (ISO 281 Annex A).
        self.assertAlmostEqual(ratings.fc_for(constants.BALL, 0.20), 59.9)

    def test_f0_roller_hits_table_value(self):
        # γ = 0.12 → f0_roller = 45.5 (Maximum der Roller-Kurve).
        self.assertAlmostEqual(ratings.f0_for(constants.CYLINDRICAL, 0.12), 45.5)

    def test_fc_roller_hits_table_value(self):
        # γ = 0.16 → fc_roller = 84.8 (Maximum der Roller-Kurve).
        self.assertAlmostEqual(ratings.fc_for(constants.CYLINDRICAL, 0.16), 84.8)

    def test_linear_interpolation_between_entries(self):
        # γ = 0.11 liegt zwischen (0.10, 13.7) und (0.12, 13.9).
        # Linear: 13.7 + 0.5·(13.9 - 13.7) = 13.8.
        self.assertAlmostEqual(ratings.f0_for(constants.BALL, 0.11), 13.8, places=6)

    def test_clamps_below_lowest_entry(self):
        # γ << 0.05 → kleinster Tabellenwert.
        self.assertAlmostEqual(ratings.f0_for(constants.BALL, 0.0), 12.7)
        self.assertAlmostEqual(ratings.f0_for(constants.BALL, -1.0), 12.7)

    def test_clamps_above_highest_entry(self):
        # γ >> 0.34 → größter (letzter) Tabellenwert für Ball.
        self.assertAlmostEqual(ratings.f0_for(constants.BALL, 0.50), 14.4)
        # Roller-Tabelle endet bei 0.30 → letzter Eintrag 40.9.
        self.assertAlmostEqual(ratings.f0_for(constants.NEEDLE, 0.50), 40.9)

    def test_vgroove_treated_as_ball(self):
        # VGROOVE nutzt die Ball-Tabellen (rollende Kugel).
        self.assertEqual(
            ratings.f0_for(constants.VGROOVE, 0.10),
            ratings.f0_for(constants.BALL, 0.10),
        )


class TestStaticRating(unittest.TestCase):
    def test_ball_uses_diameter_squared(self):
        # γ = 7 / 25 = 0.28 → f0_ball ≈ 14.5.
        c0 = ratings.static_load_rating(
            constants.BALL, 7.0, 0.0, 10, pitch_d_mm=25.0,
        )
        f0 = ratings.f0_for(constants.BALL, 7.0 / 25.0)
        self.assertAlmostEqual(c0, f0 * 10 * 49.0, places=3)

    def test_roller_uses_length_times_diameter(self):
        # γ = 6 / 60 = 0.10 → f0_roller = 45.4.
        c0 = ratings.static_load_rating(
            constants.CYLINDRICAL, 6.0, 10.0, 12, pitch_d_mm=60.0,
        )
        f0 = ratings.f0_for(constants.CYLINDRICAL, 0.10)
        self.assertAlmostEqual(c0, f0 * 12 * 10.0 * 6.0, places=3)

    def test_spherical_has_two_rows(self):
        single = ratings.static_load_rating(
            constants.CYLINDRICAL, 6.0, 10.0, 12, pitch_d_mm=60.0,
        )
        twin = ratings.static_load_rating(
            constants.SPHERICAL, 6.0, 10.0, 12, pitch_d_mm=60.0,
        )
        # Pendel rechnet mit α=10° und i=2; γ ändert sich um cos(10°).
        cos_a = math.cos(math.radians(10.0))
        g_single = ratings.gamma(6.0, 0.0, 60.0)
        g_twin = ratings.gamma(6.0, math.radians(10.0), 60.0)
        f0_single = ratings.f0_for(constants.CYLINDRICAL, g_single)
        f0_twin = ratings.f0_for(constants.SPHERICAL, g_twin)
        expected_ratio = (f0_twin / f0_single) * 2.0 * cos_a
        self.assertAlmostEqual(twin / single, expected_ratio, places=4)

    def test_zero_inputs_return_zero(self):
        self.assertEqual(
            ratings.static_load_rating(constants.BALL, 0.0, 0.0, 10, 30.0), 0.0,
        )
        self.assertEqual(
            ratings.static_load_rating(constants.BALL, 7.0, 0.0, 0, 30.0), 0.0,
        )
        self.assertEqual(
            ratings.static_load_rating(constants.NEEDLE, 4.0, 0.0, 10, 30.0), 0.0,
        )


class TestDynamicRating(unittest.TestCase):
    def test_ball_scales_with_diameter_to_1_8(self):
        # Bei festem γ skaliert Cr ∝ Dw^1.8. Wenn wir γ konstant halten
        # (gleicher Dw/dm-Quotient), klappt die Beziehung exakt.
        small = ratings.dynamic_load_rating(
            constants.BALL, 5.0, 0.0, 10, pitch_d_mm=25.0,
        )
        large = ratings.dynamic_load_rating(
            constants.BALL, 10.0, 0.0, 10, pitch_d_mm=50.0,
        )
        self.assertAlmostEqual(large / small, 2.0 ** 1.8, places=3)

    def test_roller_scales_with_count_to_three_quarters(self):
        few = ratings.dynamic_load_rating(
            constants.CYLINDRICAL, 6.0, 10.0, 8, pitch_d_mm=60.0,
        )
        many = ratings.dynamic_load_rating(
            constants.CYLINDRICAL, 6.0, 10.0, 16, pitch_d_mm=60.0,
        )
        self.assertAlmostEqual(many / few, 2.0 ** 0.75, places=3)


class TestLife(unittest.TestCase):
    def test_no_load_returns_none(self):
        self.assertIsNone(ratings.nominal_life_hours(10000.0, 0.0, 1000.0, 3.0))
        self.assertIsNone(ratings.nominal_life_hours(10000.0, 500.0, 0.0, 3.0))

    def test_l10_uses_exponent_three_for_ball(self):
        h = ratings.nominal_life_hours(20000.0, 2000.0, 1500.0, 3.0)
        self.assertAlmostEqual(h, (10.0 ** 3) * 1.0e6 / (60.0 * 1500.0), places=3)

    def test_compute_ratings_returns_gamma_and_factors(self):
        r = ratings.compute_ratings(
            bearing_type=constants.BALL,
            roller_d_mm=7.0,
            roller_length_mm=7.0,
            element_count=10,
            pitch_d_mm=33.5,
            radial_load_Fr_N=500.0,
            speed_rpm=1500.0,
        )
        self.assertGreater(r.static_C0_N, 0.0)
        self.assertGreater(r.dynamic_C_N, 0.0)
        self.assertIsNotNone(r.L10h)
        self.assertEqual(r.life_exponent, 3.0)
        # γ und Beiwerte werden mit ausgeliefert.
        self.assertAlmostEqual(r.gamma, 7.0 / 33.5, places=6)
        self.assertGreater(r.f0, 0.0)
        self.assertGreater(r.fc, 0.0)


class TestCatalogPlausibility(unittest.TestCase):
    """Spot-Check, dass die γ-Beiwerte plausible Bereiche liefern.

    Wir vergleichen nicht gegen Hersteller-Katalogwerte (die Lager-Geometrie
    ist vom Resolver abgeleitet, nicht aus dem Katalog), aber wir können
    zeigen, dass die γ-abhängigen Beiwerte die Tragzahl gegenüber den
    Mittelwert-Konstanten reduzieren (ISO 281 Annex-Werte liegen tendenziell
    unter den im alten Modul verwendeten Mittelwerten f0=14.7, fc=70.0).
    """

    def test_ball_typical_gamma_lowers_factors_vs_old_constants(self):
        # 6204-Resolver liefert ungefähr γ ≈ 0.13 (Dw≈4.2, dm≈33.5).
        g = 0.13
        self.assertLess(ratings.f0_for(constants.BALL, g), 14.7)
        # fc-Tabelle bleibt selbst im Maximum (≈60) deutlich unter 70.
        self.assertLess(ratings.fc_for(constants.BALL, g), 70.0)


class TestEquivalentLoad(unittest.TestCase):
    """ISO 281 Tabelle 4 – X-/Y-Faktoren und äquivalente Last P."""

    def test_ball_pure_radial_below_threshold(self):
        # Fa = 0 < e·Fr ⇒ X = 1, Y = 0, P = Fr.
        load = ratings.equivalent_load(
            constants.BALL, radial_load_Fr_N=1000.0, axial_load_Fa_N=0.0,
            static_C0_N=10000.0,
        )
        self.assertEqual(load.X, 1.0)
        self.assertEqual(load.Y, 0.0)
        self.assertEqual(load.P_N, 1000.0)

    def test_ball_pure_axial_uses_y(self):
        # Fr = 0, Fa = 1000 ⇒ alleinige Axiallast wird über Y berücksichtigt.
        load = ratings.equivalent_load(
            constants.BALL, radial_load_Fr_N=0.0, axial_load_Fa_N=1000.0,
            static_C0_N=10000.0,
        )
        self.assertGreater(load.Y, 0.0)
        # P = X·0 + Y·Fa = Y·Fa.
        self.assertAlmostEqual(load.P_N, load.X * 0.0 + load.Y * 1000.0, places=3)

    def test_ball_axial_above_threshold_switches_to_xy(self):
        # Fa/Fr > e ⇒ X = 0.56, Y > 0, P = 0.56·Fr + Y·Fa.
        load = ratings.equivalent_load(
            constants.BALL, radial_load_Fr_N=100.0, axial_load_Fa_N=1000.0,
            static_C0_N=10000.0,
        )
        self.assertAlmostEqual(load.X, 0.56)
        self.assertGreater(load.Y, 0.0)
        self.assertAlmostEqual(load.P_N, 0.56 * 100.0 + load.Y * 1000.0, places=3)

    def test_ball_e_y_interpolates(self):
        # Fa/C0 = 0.025 ⇒ e = 0.22, Y = 2.0 (erster Tabelleneintrag).
        load = ratings.equivalent_load(
            constants.BALL, radial_load_Fr_N=1.0, axial_load_Fa_N=250.0,
            static_C0_N=10000.0,
        )
        self.assertAlmostEqual(load.e, 0.22, places=3)
        self.assertAlmostEqual(load.Y, 2.0, places=3)

    def test_ball_e_y_clamps_above_table(self):
        # Fa/C0 = 1.0 weit über letztem Eintrag ⇒ e = 0.44, Y = 1.0.
        load = ratings.equivalent_load(
            constants.BALL, radial_load_Fr_N=100.0, axial_load_Fa_N=10000.0,
            static_C0_N=10000.0,
        )
        self.assertAlmostEqual(load.e, 0.44, places=3)
        self.assertAlmostEqual(load.Y, 1.0, places=3)

    def test_tapered_uses_contact_angle(self):
        # α = 14° ⇒ e = 1.5·tan(14°) ≈ 0.374, Y = 0.4/tan(14°) ≈ 1.605.
        alpha_deg = 14.0
        load = ratings.equivalent_load(
            constants.TAPERED, radial_load_Fr_N=100.0, axial_load_Fa_N=1000.0,
            static_C0_N=0.0, contact_angle_deg=alpha_deg,
        )
        tan_a = math.tan(math.radians(alpha_deg))
        self.assertAlmostEqual(load.e, 1.5 * tan_a, places=4)
        self.assertAlmostEqual(load.Y, 0.4 / tan_a, places=4)
        # Fa/Fr = 10 > e ⇒ X = 0.4.
        self.assertAlmostEqual(load.X, 0.4, places=4)

    def test_tapered_below_threshold(self):
        # Fa/Fr unter e ⇒ X = 1, Y = 0.
        load = ratings.equivalent_load(
            constants.TAPERED, radial_load_Fr_N=1000.0, axial_load_Fa_N=100.0,
            static_C0_N=0.0, contact_angle_deg=14.0,
        )
        self.assertEqual(load.X, 1.0)
        self.assertEqual(load.Y, 0.0)
        self.assertEqual(load.P_N, 1000.0)

    def test_tapered_zero_angle_falls_back_to_radial(self):
        # α = 0 ⇒ kein Axiallast-Anteil (degenerate Kegelrolle = Zylinder).
        load = ratings.equivalent_load(
            constants.TAPERED, radial_load_Fr_N=100.0, axial_load_Fa_N=1000.0,
            static_C0_N=0.0, contact_angle_deg=0.0,
        )
        self.assertEqual(load.X, 1.0)
        self.assertEqual(load.Y, 0.0)
        self.assertEqual(load.P_N, 100.0)

    def test_spherical_uses_y_low_below_threshold(self):
        # Pendel-Default α = 10° (siehe _contact_angle_rad). Fa/Fr unter e ⇒
        # Y1 ≈ 0.45/tan(10°) und Last = Fr + Y1·Fa.
        load = ratings.equivalent_load(
            constants.SPHERICAL, radial_load_Fr_N=1000.0, axial_load_Fa_N=50.0,
            static_C0_N=0.0,
        )
        tan_a = math.tan(math.radians(10.0))
        self.assertAlmostEqual(load.e, 1.5 * tan_a, places=4)
        self.assertAlmostEqual(load.Y, 0.45 / tan_a, places=4)
        self.assertAlmostEqual(load.P_N, 1000.0 + load.Y * 50.0, places=3)

    def test_cylindrical_ignores_axial(self):
        # Reines Radiallager: Fa wird ignoriert, P = Fr.
        load = ratings.equivalent_load(
            constants.CYLINDRICAL, radial_load_Fr_N=500.0, axial_load_Fa_N=999.0,
            static_C0_N=0.0,
        )
        self.assertEqual(load.X, 1.0)
        self.assertEqual(load.Y, 0.0)
        self.assertEqual(load.P_N, 500.0)

    def test_needle_ignores_axial(self):
        load = ratings.equivalent_load(
            constants.NEEDLE, radial_load_Fr_N=500.0, axial_load_Fa_N=999.0,
            static_C0_N=0.0,
        )
        self.assertEqual(load.P_N, 500.0)

    def test_vgroove_treated_as_ball(self):
        # VGROOVE soll dieselben Tabellen wie BALL nutzen.
        ball = ratings.equivalent_load(
            constants.BALL, radial_load_Fr_N=100.0, axial_load_Fa_N=200.0,
            static_C0_N=5000.0,
        )
        vg = ratings.equivalent_load(
            constants.VGROOVE, radial_load_Fr_N=100.0, axial_load_Fa_N=200.0,
            static_C0_N=5000.0,
        )
        self.assertEqual((ball.X, ball.Y, ball.e), (vg.X, vg.Y, vg.e))
        self.assertAlmostEqual(ball.P_N, vg.P_N, places=6)

    def test_negative_loads_clamped_to_zero(self):
        load = ratings.equivalent_load(
            constants.BALL, radial_load_Fr_N=-100.0, axial_load_Fa_N=-50.0,
            static_C0_N=10000.0,
        )
        self.assertEqual(load.P_N, 0.0)


class TestComputeRatingsWithLoads(unittest.TestCase):
    """Fr + Fa fließen über compute_ratings in P und L10h ein."""

    def test_axial_load_shortens_life_for_ball(self):
        # Gleiche Lager-Geometrie, einmal nur Fr, einmal Fr + großes Fa.
        kwargs = dict(
            bearing_type=constants.BALL,
            roller_d_mm=7.0,
            roller_length_mm=7.0,
            element_count=10,
            pitch_d_mm=33.5,
            speed_rpm=1500.0,
        )
        only_radial = ratings.compute_ratings(
            **kwargs, radial_load_Fr_N=500.0, axial_load_Fa_N=0.0,
        )
        with_axial = ratings.compute_ratings(
            **kwargs, radial_load_Fr_N=500.0, axial_load_Fa_N=2000.0,
        )
        # Mehr Axiallast ⇒ größeres P ⇒ kürzere L10h.
        self.assertGreater(with_axial.P_N, only_radial.P_N)
        self.assertLess(with_axial.L10h, only_radial.L10h)

    def test_xy_factors_propagate_to_dataclass(self):
        r = ratings.compute_ratings(
            bearing_type=constants.TAPERED,
            roller_d_mm=6.0,
            roller_length_mm=10.0,
            element_count=12,
            pitch_d_mm=40.0,
            contact_angle_deg=14.0,
            radial_load_Fr_N=100.0,
            axial_load_Fa_N=1000.0,
            speed_rpm=1500.0,
        )
        # X, Y, e und P sind aus equivalent_load übernommen.
        self.assertAlmostEqual(r.X, 0.4)
        self.assertGreater(r.Y, 1.0)
        self.assertGreater(r.P_N, 100.0)


if __name__ == "__main__":
    unittest.main()
