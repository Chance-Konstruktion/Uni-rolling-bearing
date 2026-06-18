"""Host-freie Ergebnis-Auswertung für das FreeCAD-Task-Panel.

Spiegelt den Abschnitt **„Ergebnisse"** des Blender-N-Panels (``panel.py``):
Plausibilität (effektiver Wälzkörper-Ø / Anzahl / Teilkreis), Tragzahlen &
Lebensdauer (ISO 76 / ISO 281) und Passungs-Empfehlung (DIN 5418) – als fertig
formatierte Textzeilen, damit das Qt-Panel sie nur noch anzeigen muss.

Komplett ohne ``FreeCAD``/``FreeCADGui``/``bpy`` und damit eigenständig testbar;
die Rechen-Logik liegt im geteilten Kern (``geometry``/``ratings``/``fits``).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from uni_rolling_bearing import constants, fits as fits_mod, ratings as ratings_mod
from uni_rolling_bearing.geometry import resolve_geometry

from .params import BearingParams


@dataclass
class AnalysisResult:
    """Auswertung eines Lagers als anzeigefertige Textblöcke."""

    error: Optional[str] = None
    plausibility: List[str] = field(default_factory=list)
    ratings: List[str] = field(default_factory=list)
    fits: List[str] = field(default_factory=list)


def _dev_label(prefix: str, cls: str, upper, lower) -> str:
    if upper is None or lower is None:
        return f"{prefix} {cls} (außerhalb Tabelle)"
    return f"{prefix} {cls}  {upper:+d}/{lower:+d} µm"


def analyze(params: BearingParams) -> AnalysisResult:
    """Wertet ``params`` zu Plausibilität, Tragzahlen und Passungen aus.

    Bei unzulässiger Geometrie wird ``error`` gesetzt und nur die Passungs-
    Empfehlung (die rein von d/D/Lastfall abhängt) gefüllt – analog zum
    Blender-Ergebnis-Panel.
    """
    result = AnalysisResult()

    spec, error = resolve_geometry(
        bearing_type=params.bearing_type,
        bore_diameter=params.bore_diameter,
        outer_diameter=params.outer_diameter,
        width=params.width,
        ring_thickness=params.ring_thickness,
        roller_diameter=params.roller_diameter,
        element_count=params.element_count,
        radial_clearance=params.radial_clearance,
        gap_factor=params.gap_factor,
        auto_fit=params.auto_fit,
        conformity_inner=params.groove_conformity_inner,
        conformity_outer=params.groove_conformity_outer,
        contact_angle_deg=params.contact_angle_deg,
    )

    if error or spec is None:
        result.error = error or "Geometrie unzulässig."
    else:
        roller_clamped = spec.roller_d + 1e-4 < params.roller_diameter
        count_clamped = spec.element_count < params.element_count
        roller_label = f"Effektiver Wälzkörper-Ø: {spec.roller_d:.3f} mm"
        if roller_clamped:
            roller_label += f"  (angefragt: {params.roller_diameter:.3f})"
        count_label = f"Effektive Anzahl: {spec.element_count}"
        if count_clamped:
            count_label += f"  (angefragt: {params.element_count})"
        result.plausibility.append(roller_label)
        result.plausibility.append(count_label)
        result.plausibility.append(f"Teilkreis-Ø: {spec.pitch_d:.3f} mm")
        if roller_clamped or count_clamped:
            result.plausibility.append("Auto-Fit hat Werte angepasst.")

        angle = (
            params.contact_angle_deg
            if params.bearing_type == constants.TAPERED
            else 0.0
        )
        r = ratings_mod.compute_ratings(
            bearing_type=params.bearing_type,
            roller_d_mm=spec.roller_d,
            roller_length_mm=spec.roller_length,
            element_count=spec.element_count,
            pitch_d_mm=spec.pitch_d,
            contact_angle_deg=angle,
            radial_load_Fr_N=params.radial_load_fr_n,
            axial_load_Fa_N=params.axial_load_fa_n,
            speed_rpm=params.speed_rpm,
            rows=(
                params.spherical_row_count()
                if params.bearing_type == constants.SPHERICAL
                else None
            ),
        )
        result.ratings.append(f"γ={r.gamma:.3f}  f0={r.f0:.1f}  fc={r.fc:.1f}")
        result.ratings.append(f"C0r ≈ {r.static_C0_N:,.0f} N")
        result.ratings.append(f"Cr  ≈ {r.dynamic_C_N:,.0f} N")
        if params.radial_load_fr_n > 0.0 or params.axial_load_fa_n > 0.0:
            result.ratings.append(f"X={r.X:.2f}  Y={r.Y:.2f}  e={r.e:.2f}")
            result.ratings.append(f"P ≈ {r.P_N:,.0f} N")
            if (
                params.bearing_type in (constants.CYLINDRICAL, constants.NEEDLE)
                and params.axial_load_fa_n > 0.0
            ):
                result.ratings.append("Axiallast wird bei diesem Lagertyp ignoriert.")
        if r.L10h is not None:
            result.ratings.append(f"L10h ≈ {r.L10h:,.0f} h")

    fit = fits_mod.recommend_fits(
        load_case=params.load_case,
        bore_diameter_mm=params.bore_diameter,
        outer_diameter_mm=params.outer_diameter,
    )
    result.fits.append(
        _dev_label("Welle:", fit.shaft_class, fit.shaft_upper_um, fit.shaft_lower_um)
    )
    result.fits.append(
        _dev_label("Gehäuse:", fit.housing_class, fit.housing_upper_um, fit.housing_lower_um)
    )
    return result


__all__ = ["AnalysisResult", "analyze"]
