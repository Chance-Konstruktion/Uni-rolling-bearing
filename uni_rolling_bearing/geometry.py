"""Reine Geometrieberechnungen – ohne Blender-Abhängigkeit, daher testbar."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

from . import constants

# Mindesthöhe [mm] für den nutzbaren Ringspalt, damit ein Wälzkörper sinnvoll passt.
MIN_USABLE_SPACE_MM = 0.2

# Sicherheitsabschlag am maximal erlaubten Wälzkörper-Ø – verhindert 0-Spalt
# zwischen Wälzkörper und Laufbahn.
ROLLER_SAFETY_FRACTION = 0.98

# Verhältnis Ringstärke zu Radial-Bereich (D-d) für Preset-Vorschläge:
# entspricht etwa der Praxis bei Standard-Wälzlagern.
SUGGESTED_RING_THICKNESS_FRACTION = 1.0 / 6.0
MIN_SUGGESTED_RING_THICKNESS_MM = 0.5
MAX_SUGGESTED_RING_THICKNESS_MM = 8.0

# Wie viel des nutzbaren Spalts (nach Abzug der Lagerluft) der vorgeschlagene
# Wälzkörper-Ø einnimmt. Lässt etwas Spielraum gegenüber dem harten Maximum.
SUGGESTED_ROLLER_FILL = 0.90

# Typischer Konformitätsfaktor f = r_groove / d_ball für Rillenkugellager,
# wenn der Aufrufer keinen eigenen Wert übergibt. Reale Werte liegen bei
# 0.515–0.535; 0.52 ist ein guter Mittelwert für die Geometrie-Berechnung.
DEFAULT_BALL_GROOVE_CONFORMITY = 0.52


@dataclass(frozen=True)
class BearingDims:
    """Abgeleitete Hauptmaße in mm.

    ``radial_space`` ist die *radiale Spaltbreite* zwischen Innen- und Außen-
    laufbahn (= ``(outer_inner_d - inner_outer_d) / 2``). Der nutzbare
    Wälzkörper-Ø darf maximal so groß werden wie diese Spaltbreite (abzüglich
    Lagerluft).
    """

    inner_outer_d: float  # Außen-Ø des Innenrings = Innenlaufbahn
    outer_inner_d: float  # Innen-Ø des Außenrings = Außenlaufbahn
    radial_space: float   # Radiale Spaltbreite (Innenlaufbahn → Außenlaufbahn)


@dataclass(frozen=True)
class ResolvedBearing:
    """Ergebnis des Geometrie-Resolvers – alle Werte in mm bzw. Stückzahl."""

    inner_outer_d: float
    outer_inner_d: float
    roller_d: float
    roller_length: float
    pitch_d: float
    element_count: int


def compute_dims(
    bore_diameter: float,
    outer_diameter: float,
    ring_thickness: float,
) -> BearingDims:
    """Leitet Laufbahn-Durchmesser und radialen Rohspalt aus den Hauptmaßen ab."""
    inner_outer_d = bore_diameter + 2.0 * ring_thickness
    outer_inner_d = outer_diameter - 2.0 * ring_thickness
    radial_space = (outer_inner_d - inner_outer_d) * 0.5
    return BearingDims(inner_outer_d, outer_inner_d, radial_space)


def max_elements_for_pitch(
    pitch_diameter: float,
    element_diameter: float,
    gap_factor: float,
) -> int:
    """Maximale Wälzkörperanzahl, bei der sie sich auf dem Teilkreis nicht überlappen.

    ``gap_factor`` ist der relative Zusatzabstand (z. B. 0.1 = 10 % Spalt).
    """
    circumference = math.pi * pitch_diameter
    element_pitch = max(0.1, element_diameter * (1.0 + gap_factor))
    return max(3, int(circumference // element_pitch))


def roller_length_for_type(bearing_type: str, width: float, roller_d: float) -> float:
    """Liefert die Rollenlänge in Abhängigkeit vom Lagertyp.

    Für Kugellager wird die Länge gleich dem Ø gesetzt (Kugel).
    """
    if bearing_type == constants.BALL:
        return roller_d
    ratio = constants.ROLLER_LENGTH_RATIO.get(bearing_type)
    if ratio is None:
        return roller_d
    return width * ratio


def _ball_max_roller_d(usable_space: float, conformity: float) -> float:
    """Maximaler Kugel-Ø, wenn ``ring_thickness`` als Mindestwand über der
    Rille interpretiert wird.

    Herleitung: die Rille reicht radial bis zu ``pitch_r - r_groove =
    pitch_r - f·d_ball``. Damit unter ihr noch die Wand ``ring_thickness``
    übrig bleibt, muss ``f·d_ball ≤ (D−d)/4 − ring_thickness =
    usable_space / 2``. Aufgelöst nach ``d_ball``: ``d_ball ≤ usable_space /
    (2·f)``. Symmetrisch für die Außenring-Rille. ``ROLLER_SAFETY_FRACTION``
    bleibt als 2 %-Sicherheitspuffer erhalten.
    """
    f = max(0.5 + 1.0e-6, conformity)
    return (usable_space / (2.0 * f)) * ROLLER_SAFETY_FRACTION


def _tapered_max_roller_d(
    *,
    radial_space: float,
    width: float,
    contact_angle_rad: float,
    clearance: float,
) -> float:
    """Maximaler Kegelrollen-Ø, bei dem die α-gekippte Großend-Stirn die
    Außenlaufbahn nicht durchstößt.

    Spiegelt die Clamp-Bedingung aus ``operators._tapered_roller_radii``:
    ohne diesen Cap würde der Operator die gezeichneten Radien nachträglich
    runterskalieren, sodass das im Panel angezeigte ``roller_d`` deutlich
    größer sein kann als die tatsächlich gerenderte Rolle. Mit diesem Cap
    stimmen Resolver-Wert und gezeichnetes Mesh überein.

    Bei ``contact_angle_rad ≤ 0`` (typisch CYLINDRICAL/NEEDLE) liefert die
    Funktion ``+inf`` – der Tilt-Cap ist dann nicht bindend.
    """
    if contact_angle_rad <= 0.0:
        return float("inf")
    length = width * constants.ROLLER_LENGTH_RATIO[constants.TAPERED]
    sin_a = math.sin(contact_angle_rad)
    cos_a = max(math.cos(contact_angle_rad), 1e-6)
    # Abstand pitch_r → Außenrace = radial_space / 2.
    # Nach dem Kipp wandert das Großend-Stirnzentrum um sin(α)·L/2 nach außen,
    # dort darf ``radius_large · cos(α)`` plus ``clearance`` nicht über die
    # Außenlaufbahn hinaus reichen.
    max_face_r = (radial_space * 0.5 - sin_a * length * 0.5 - clearance) / cos_a
    # ``radius_large = mean_r + delta`` mit ``delta = sin(α/2)·L/2`` (Kegelform).
    delta = math.sin(contact_angle_rad * 0.5) * length * 0.5
    return max(0.0, 2.0 * (max_face_r - delta))


def resolve_geometry(
    *,
    bearing_type: str,
    bore_diameter: float,
    outer_diameter: float,
    width: float,
    ring_thickness: float,
    roller_diameter: float,
    element_count: int,
    radial_clearance: float,
    gap_factor: float,
    auto_fit: bool,
    groove_conformity: Optional[float] = None,
    contact_angle_deg: float = 0.0,
) -> Tuple[Optional[ResolvedBearing], Optional[str]]:
    """Löst alle Parameter zu einer funktionsfähigen Geometrie auf.

    Gibt ``(spec, None)`` bei Erfolg oder ``(None, error_message)`` zurück.
    Mit ``auto_fit=True`` werden unplausible Werte stillschweigend korrigiert.

    ``groove_conformity`` wird bei Rillenkugellagern (BALL/VGROOVE) verwendet,
    um die maximale Kugelgröße zu berechnen: weil die Kugel teilweise in die
    Rille eintaucht, darf sie größer sein als der reine Schulter-zu-Schulter-
    Abstand. Bei anderen Lagertypen ohne Bedeutung.
    """
    if bore_diameter >= outer_diameter:
        return None, (
            f"Innendurchmesser ({bore_diameter:.2f} mm) muss kleiner als "
            f"Außendurchmesser ({outer_diameter:.2f} mm) sein. "
            f"Vorschlag: d auf < {outer_diameter:.2f} mm setzen oder D erhöhen."
        )

    dims = compute_dims(bore_diameter, outer_diameter, ring_thickness)
    if dims.radial_space <= 0.0:
        max_thickness = (outer_diameter - bore_diameter) * 0.45
        return None, (
            f"Ringstärke ({ring_thickness:.2f} mm) lässt keinen Laufbahnspalt. "
            f"Vorschlag: Ringstärke auf ≤ {max_thickness:.2f} mm reduzieren."
        )

    usable_space = dims.radial_space - 2.0 * radial_clearance
    if usable_space <= MIN_USABLE_SPACE_MM:
        max_clearance = max(0.0, (dims.radial_space - MIN_USABLE_SPACE_MM) * 0.5)
        return None, (
            f"Nach Abzug der Lagerluft ({radial_clearance:.3f} mm) bleibt nur "
            f"{usable_space:.3f} mm Wälzkörperraum. "
            f"Vorschlag: Lagerluft auf ≤ {max_clearance:.3f} mm reduzieren "
            f"oder Ringstärke verkleinern."
        )

    if bearing_type in (constants.BALL, constants.VGROOVE):
        f = groove_conformity if groove_conformity is not None else DEFAULT_BALL_GROOVE_CONFORMITY
        max_roller_d = _ball_max_roller_d(usable_space, f)
    else:
        max_roller_d = usable_space * ROLLER_SAFETY_FRACTION
        if bearing_type == constants.TAPERED and contact_angle_deg > 0.0:
            tilt_max = _tapered_max_roller_d(
                radial_space=dims.radial_space,
                width=width,
                contact_angle_rad=math.radians(contact_angle_deg),
                clearance=radial_clearance,
            )
            max_roller_d = min(max_roller_d, tilt_max)

    if roller_diameter > max_roller_d:
        if not auto_fit:
            return None, (
                f"Wälzkörper-Ø ({roller_diameter:.2f} mm) ist zu groß. "
                f"Vorschlag: Wälzkörper-Ø auf ≤ {max_roller_d:.2f} mm setzen "
                f"oder Auto-Fit aktivieren."
            )
        roller_d = max_roller_d
    else:
        roller_d = roller_diameter

    # Wälzkörper sitzen mittig zwischen Innen- und Außenlaufbahn (Teilkreis-Ø
    # ist der Mittelwert der Laufbahn-Durchmesser). So bleibt zwischen Roller
    # und beiden Laufbahnen jeweils der gleiche Restspalt – frühere Versionen
    # rechneten ``inner_outer_d + roller_d + 2*clearance`` und drückten den
    # Wälzkörper an die Innenlaufbahn, wodurch er bei großem Ø in den Außenring
    # ragte.
    pitch_d = (dims.inner_outer_d + dims.outer_inner_d) * 0.5
    max_count = max_elements_for_pitch(pitch_d, roller_d, gap_factor)
    if element_count > max_count:
        if not auto_fit:
            return None, (
                f"Zu viele Wälzkörper ({element_count}) für Teilkreis "
                f"Ø{pitch_d:.2f} mm und Wälzkörper-Ø {roller_d:.2f} mm. "
                f"Vorschlag: Anzahl auf ≤ {max_count} reduzieren, "
                f"Wälzkörper-Ø verkleinern oder Auto-Fit aktivieren."
            )
        resolved_count = max_count
    else:
        resolved_count = element_count

    roller_length = roller_length_for_type(bearing_type, width, roller_d)

    spec = ResolvedBearing(
        inner_outer_d=dims.inner_outer_d,
        outer_inner_d=dims.outer_inner_d,
        roller_d=roller_d,
        roller_length=roller_length,
        pitch_d=pitch_d,
        element_count=max(3, resolved_count),
    )
    return spec, None


@dataclass(frozen=True)
class SuggestedDefaults:
    """Geometrisch plausible Defaults zu einer Hauptmaß-Vorgabe."""

    ring_thickness: float
    roller_diameter: float
    element_count: int


def suggest_defaults(
    bearing_type: str,
    bore_diameter: float,
    outer_diameter: float,
    *,
    radial_clearance: float = 0.02,
    gap_factor: float = 0.10,
    groove_conformity: Optional[float] = None,
    width: float = 0.0,
    contact_angle_deg: float = 0.0,
) -> SuggestedDefaults:
    """Liefert ring_thickness/roller_d/Anzahl, mit denen ein Lager sofort funktioniert.

    Pro Lagertyp wird ein eigener Ringstärke-Anteil und Wälzkörper-Füllgrad
    verwendet (siehe ``constants.TYPE_RING_THICKNESS_RATIO`` und
    ``TYPE_ROLLER_FILL``). Damit erhält man typische Industriewerte für
    Wandstärke und Wälzkörper-Ø ohne manuelle Berechnung.

    Für Rillenkugellager (BALL/VGROOVE) wird zusätzlich die Konformität
    berücksichtigt, weil die Kugel teilweise in die Rille eintaucht; der
    vorgeschlagene Roller-Ø nutzt denselben Maximalwert wie
    ``resolve_geometry``.
    """
    if bore_diameter >= outer_diameter:
        # Degenerate Eingabe – minimaler Default damit nichts crasht.
        return SuggestedDefaults(MIN_SUGGESTED_RING_THICKNESS_MM, 0.5, 3)

    radial_band = outer_diameter - bore_diameter
    thickness_ratio = constants.TYPE_RING_THICKNESS_RATIO.get(
        bearing_type, SUGGESTED_RING_THICKNESS_FRACTION
    )
    ring_thickness = max(
        MIN_SUGGESTED_RING_THICKNESS_MM,
        min(MAX_SUGGESTED_RING_THICKNESS_MM, radial_band * thickness_ratio),
    )

    dims = compute_dims(bore_diameter, outer_diameter, ring_thickness)
    usable = max(MIN_USABLE_SPACE_MM, dims.radial_space - 2.0 * radial_clearance)
    fill = constants.TYPE_ROLLER_FILL.get(bearing_type, SUGGESTED_ROLLER_FILL)
    if bearing_type in (constants.BALL, constants.VGROOVE):
        f = groove_conformity if groove_conformity is not None else DEFAULT_BALL_GROOVE_CONFORMITY
        max_ball_d = _ball_max_roller_d(usable, f)
        roller_d = max(0.5, max_ball_d * fill)
    else:
        roller_d = max(0.5, usable * fill)
        if bearing_type == constants.TAPERED and contact_angle_deg > 0.0 and width > 0.0:
            tilt_max = _tapered_max_roller_d(
                radial_space=dims.radial_space,
                width=width,
                contact_angle_rad=math.radians(contact_angle_deg),
                clearance=radial_clearance,
            )
            roller_d = max(0.5, min(roller_d, tilt_max))
    pitch_d = (dims.inner_outer_d + dims.outer_inner_d) * 0.5
    count = max_elements_for_pitch(pitch_d, roller_d, gap_factor)

    return SuggestedDefaults(
        ring_thickness=ring_thickness,
        roller_diameter=roller_d,
        element_count=count,
    )


def validate_against_suggestion(
    *,
    bearing_type: str,
    bore_diameter: float,
    outer_diameter: float,
    ring_thickness: float,
    roller_diameter: float,
    element_count: int,
    radial_clearance: float,
    gap_factor: float,
    tolerance: float = 0.10,
) -> Tuple[bool, str]:
    """Prüft, ob die aktuellen Werte nahe am typabhängigen Vorschlag liegen.

    ``tolerance`` ist die zulässige relative Abweichung (0.10 = ±10 %).
    Liefert ``(ok, hint)``. Bei ``ok == True`` ist die Konfiguration nahe an
    der Empfehlung; ansonsten enthält ``hint`` einen Korrekturhinweis.
    """
    s = suggest_defaults(
        bearing_type,
        bore_diameter,
        outer_diameter,
        radial_clearance=radial_clearance,
        gap_factor=gap_factor,
    )
    deltas = []
    if abs(ring_thickness - s.ring_thickness) > max(0.1, s.ring_thickness * tolerance):
        deltas.append(f"Ringstärke {ring_thickness:.2f} ↔ Vorschlag {s.ring_thickness:.2f} mm")
    if abs(roller_diameter - s.roller_diameter) > max(0.1, s.roller_diameter * tolerance):
        deltas.append(f"Wälzkörper-Ø {roller_diameter:.2f} ↔ Vorschlag {s.roller_diameter:.2f} mm")
    if abs(element_count - s.element_count) > max(1, int(round(s.element_count * tolerance))):
        deltas.append(f"Anzahl {element_count} ↔ Vorschlag {s.element_count}")
    if not deltas:
        return True, "Werte entsprechen der Empfehlung."
    return False, "; ".join(deltas)


# ---------------------------------------------------------------------------
# Kegelrollenlager (Tapered)
# ---------------------------------------------------------------------------


def tapered_apex_z(pitch_d: float, roller_length: float, contact_angle_rad: float) -> float:
    """Z-Position des Apex (gemeinsamer Treffpunkt aller Kegelrollen-Achsen).

    Annahmen: Roller-Mittelpunkt liegt auf dem Teilkreis-Radius bei z=0 und ist um
    ``contact_angle_rad`` um die lokale Y-Achse gekippt (kleine Stirnseite zur
    Lagerachse hin, große von ihr weg). Der Apex liegt auf der Lagerachse (x=y=0)
    auf der Seite der kleinen Stirn.

    Für ``contact_angle_rad <= 0`` ist die Roller-Achse parallel zur Lagerachse;
    in dem Fall liefert die Funktion ``-inf``.
    """
    if contact_angle_rad <= 0.0:
        return float("-inf")
    pitch_r = pitch_d * 0.5
    sin_a = math.sin(contact_angle_rad)
    cos_a = math.cos(contact_angle_rad)
    # Kleine Stirn nach dem Tilt liegt bei (pitch_r - sin α · L/2, 0, -cos α · L/2).
    # Apex erreicht man durch Verlängern der Achse bis x=0:
    small_x = pitch_r - sin_a * roller_length * 0.5
    small_z = -cos_a * roller_length * 0.5
    if sin_a == 0.0:
        return float("-inf")
    t = small_x / sin_a  # Schritte entlang der negativen Achsenrichtung
    return small_z - t * cos_a


# ---------------------------------------------------------------------------
# Käfig (Cage)
# ---------------------------------------------------------------------------

# Mindestmaße in mm, damit die Käfig-Geometrie nicht in degenerate Zustände kippt.
MIN_CAGE_PLATE_THICKNESS_MM = 0.2
MIN_CAGE_WEB_RADIAL_MM = 0.4
MIN_CAGE_WEB_TANGENTIAL_MM = 0.3
# Axiales Spiel zwischen Wälzkörperende und innerer Plattenfläche.
CAGE_AXIAL_CLEARANCE_MM = 0.1
# Radialer Sicherheitsabstand zwischen Käfig und Laufbahn (an Innen-/Außenring).
CAGE_RACE_CLEARANCE_MM = 0.2
# Radialer Überstand der Endplatten gegenüber dem Wälzkörper-Querschnitt – wird
# notfalls durch die Laufbahn-Clearance gedeckelt.
CAGE_PLATE_RADIAL_OVERHANG_FACTOR = 0.15
# Anteil des tangentialen Spalts zwischen Wälzkörpern, den ein Web ausnutzt.
CAGE_WEB_TANGENTIAL_FILL = 0.6

# Mindestdurchmesser einer Schmiertasche im Massivkäfig. Wird die geometrisch
# zulässige Größe kleiner, werden Schmiertaschen weggelassen.
MIN_OIL_POCKET_DIAMETER_MM = 0.3
# Auto-Füllgrad: wie groß wird die Schmiertasche im Verhältnis zum verfüg-
# baren Material (kleinere von axialer Sleeve-Breite und tangentialem Web)?
OIL_POCKET_AUTO_FILL = 0.5


@dataclass(frozen=True)
class CageDims:
    """Geometrie eines simplen 'Leiter'-Käfigs (zwei Endplatten + Webs)."""

    plate_inner_d: float        # Innen-Ø der Endplatten (an beiden Lagerenden)
    plate_outer_d: float        # Außen-Ø der Endplatten
    plate_thickness: float      # Axiale Stärke je Platte
    plate_z_offset: float       # |z| Mittenposition jeder Platte
    web_pitch_r: float          # Radius, auf dem die Webs sitzen
    web_radial_size: float      # Radialdicke je Web
    web_tangential_size: float  # Tangentialbreite je Web
    web_axial_length: float     # Gesamt-Z-Länge eines Webs (Plattenmitte zu Plattenmitte)
    web_count: int              # Anzahl Webs (= Anzahl Wälzkörper)


def cage_dimensions(
    *,
    pitch_d: float,
    roller_d: float,
    roller_length: float,
    width: float,
    element_count: int,
    inner_race_d: float,
    outer_race_d: float,
) -> Optional[CageDims]:
    """Berechnet die Käfigmaße. Liefert ``None``, wenn kein Platz vorhanden ist.

    ``inner_race_d`` ist der Außen-Ø des Innenrings (Innenlaufbahn-Ø),
    ``outer_race_d`` ist der Innen-Ø des Außenrings (Außenlaufbahn-Ø).
    Die Endplatten werden so dimensioniert, dass sie den Wälzkörper-Querschnitt
    radial abdecken, ohne die Laufbahnen zu berühren.
    """
    if element_count < 3 or pitch_d <= 0.0 or roller_d <= 0.0 or width <= 0.0:
        return None
    if inner_race_d <= 0.0 or outer_race_d <= inner_race_d:
        return None

    pitch_r = pitch_d * 0.5
    roller_r = roller_d * 0.5

    # Wunschmaße: Plattenrand reicht knapp über den Wälzkörper-Querschnitt hinaus,
    # bleibt aber mit ``CAGE_RACE_CLEARANCE_MM`` Abstand zur Laufbahn.
    overhang = roller_d * CAGE_PLATE_RADIAL_OVERHANG_FACTOR
    plate_inner_d_target = pitch_d - roller_d - overhang
    plate_outer_d_target = pitch_d + roller_d + overhang

    plate_inner_d = max(plate_inner_d_target, inner_race_d + 2.0 * CAGE_RACE_CLEARANCE_MM)
    plate_outer_d = min(plate_outer_d_target, outer_race_d - 2.0 * CAGE_RACE_CLEARANCE_MM)
    if plate_outer_d - plate_inner_d <= 2.0 * MIN_CAGE_WEB_RADIAL_MM:
        return None

    # Axialer Restraum zwischen Wälzkörperende und Lagerstirn.
    half_elem = max(roller_r, roller_length * 0.5)
    bearing_half_w = width * 0.5
    free_axial = bearing_half_w - half_elem - CAGE_AXIAL_CLEARANCE_MM
    if free_axial <= MIN_CAGE_PLATE_THICKNESS_MM:
        return None

    plate_thickness = max(MIN_CAGE_PLATE_THICKNESS_MM, min(2.0, free_axial * 0.8))
    plate_z_offset = half_elem + CAGE_AXIAL_CLEARANCE_MM + plate_thickness * 0.5

    # Tangentiale Lücke zwischen Wälzkörpern auf dem Teilkreis.
    angular_pitch = 2.0 * math.pi / element_count
    tangential_gap = pitch_r * angular_pitch - roller_d
    if tangential_gap <= MIN_CAGE_WEB_TANGENTIAL_MM:
        return None

    web_radial_size = max(MIN_CAGE_WEB_RADIAL_MM, min(2.0, roller_r * 0.4))
    web_tangential_size = max(
        MIN_CAGE_WEB_TANGENTIAL_MM,
        tangential_gap * CAGE_WEB_TANGENTIAL_FILL,
    )
    # Web reicht zwischen die Plattenmittel (mit leichter Überlappung).
    web_axial_length = 2.0 * plate_z_offset

    return CageDims(
        plate_inner_d=plate_inner_d,
        plate_outer_d=plate_outer_d,
        plate_thickness=plate_thickness,
        plate_z_offset=plate_z_offset,
        web_pitch_r=pitch_r,
        web_radial_size=web_radial_size,
        web_tangential_size=web_tangential_size,
        web_axial_length=web_axial_length,
        web_count=element_count,
    )


def oil_pocket_diameter(
    *,
    requested_mm: float,
    sleeve_axial_extent_mm: float,
    web_tangential_size_mm: float,
    edge_clearance_mm: float = 0.0,
) -> float:
    """Liefert den effektiven Schmiertaschen-Ø für einen Massivkäfig.

    Die radiale Schmiertaschen-Bohrung sitzt mittig zwischen zwei Wälzkörper-
    Pockets; ihr Querschnitt steht damit in der axial-tangentialen Ebene des
    Käfigs. Der Durchmesser darf weder die axiale Käfigbreite noch den
    tangentialen Steg zwischen zwei Pockets überschreiten.

    ``requested_mm == 0`` aktiviert die automatische Größe (50 % des kleineren
    Bauraums). Werte kleiner als ``MIN_OIL_POCKET_DIAMETER_MM`` werden als
    "keine Schmiertasche" interpretiert und das Ergebnis ist ``0``.
    ``edge_clearance_mm`` reserviert Material am Rand der Bohrung.
    """
    max_dia = min(sleeve_axial_extent_mm, web_tangential_size_mm) - 2.0 * edge_clearance_mm
    if max_dia <= 0.0:
        return 0.0
    if requested_mm > 0.0:
        dia = min(requested_mm, max_dia)
    else:
        dia = max_dia * OIL_POCKET_AUTO_FILL
    if dia < MIN_OIL_POCKET_DIAMETER_MM:
        return 0.0
    return dia
