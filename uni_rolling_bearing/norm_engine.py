"""Norm-Engine: Laden der Maßreihen-Tabellen aus externen JSON-Dateien.

Trennung zwischen Code und Normdaten. Jede JSON-Datei unter ``data/``
beschreibt einen Lagertyp mit Norm-Quelle und Maßeinträgen:

* ``coding: "din623"`` – Reihen-Tabelle, Schlüssel = Bohrungskennzahl,
  Wert = ``[D, B]``. ``d`` wird per DIN 623 aus der Kennzahl abgeleitet.
* ``coding: "direct"`` – direkte ``code → [d, D, B]`` Tabelle.

Benutzer können eigene Presets ergänzen, indem sie eine Datei mit dem
gleichen Schema im Blender-User-Verzeichnis ablegen
(``<config>/scripts/uni_bearing/<type>.json``) – sie werden über die
ausgelieferten Defaults gemerged.
"""

from __future__ import annotations

import json
import logging
import math
import pathlib
from typing import Dict, Tuple

from . import din623

LOG = logging.getLogger(__name__)

_DATA_DIR = pathlib.Path(__file__).resolve().parent / "data"
_TYPE_FILES: Dict[str, str] = {
    "BALL": "ball.json",
    "CYLINDRICAL": "cylindrical.json",
    "NEEDLE": "needle.json",
    "TAPERED": "tapered.json",
    "SPHERICAL": "spherical.json",
    "VGROOVE": "vgroove.json",
}


def _load_json(path: pathlib.Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _user_data_path(filename: str) -> pathlib.Path | None:
    try:
        import bpy  # type: ignore
    except ImportError:
        return None
    user_dir = pathlib.Path(bpy.utils.user_resource("SCRIPTS")) / "uni_bearing"
    candidate = user_dir / filename
    return candidate if candidate.exists() else None


def _expand_din623(payload: dict) -> Dict[str, Tuple[float, float, float]]:
    series = payload.get("series", {})
    prefix = payload.get("prefix", "")
    result: Dict[str, Tuple[float, float, float]] = {}
    if not isinstance(prefix, str):
        LOG.warning("Skipping DIN 623 payload: 'prefix' muss Text sein")
        return result
    if not isinstance(series, dict):
        LOG.warning("Skipping DIN 623 payload: 'series' muss ein Objekt sein")
        return result
    for series_name, entries in series.items():
        code_prefix = (prefix + series_name) if prefix else series_name
        if not isinstance(entries, dict):
            LOG.warning("Skipping series %s: muss ein Objekt sein", series_name)
            continue
        for bore_code, dims in entries.items():
            if not isinstance(dims, (list, tuple)) or len(dims) not in (2, 4):
                LOG.warning("Skipping %s/%s: erwartet [D, B] oder [D, T, B, C], bekam %r",
                            series_name, bore_code, dims)
                continue
            try:
                numeric_dims = tuple(float(value) for value in dims)
                d = din623.bore_code_to_diameter(str(bore_code))
            except (TypeError, ValueError, OverflowError) as exc:
                LOG.warning("Skipping %s/%s: ungültige Maßangabe (%s)", series_name, bore_code, exc)
                continue
            D, total_width = numeric_dims[0], numeric_dims[1]
            if (
                not all(math.isfinite(value) and value > 0.0 for value in numeric_dims)
                or not math.isfinite(d)
                or d <= 0.0
                or D <= d
            ):
                LOG.warning("Skipping %s/%s: ungültige Lagermaße %r", series_name, bore_code, dims)
                continue
            result[f"{code_prefix}{bore_code}"] = (d, D, total_width)
    return result


def _extract_ring_widths(payload: dict) -> Dict[str, Tuple[float, float]]:
    """Liefert ``{code: (inner_width_B, outer_width_C)}`` für 4-stellige Einträge."""
    if not isinstance(payload, dict):
        LOG.warning("Skipping ring-width payload: Wurzel muss ein JSON-Objekt sein")
        return {}
    series = payload.get("series", {})
    prefix = payload.get("prefix", "")
    result: Dict[str, Tuple[float, float]] = {}
    if not isinstance(prefix, str):
        LOG.warning("Skipping ring-width payload: 'prefix' muss Text sein")
        return result
    if not isinstance(series, dict):
        return result
    for series_name, entries in series.items():
        code_prefix = (prefix + series_name) if prefix else series_name
        if not isinstance(entries, dict):
            continue
        for bore_code, dims in entries.items():
            if not isinstance(dims, (list, tuple)) or len(dims) != 4:
                continue
            try:
                numeric_dims = tuple(float(value) for value in dims)
                d = din623.bore_code_to_diameter(str(bore_code))
            except (TypeError, ValueError, OverflowError):
                continue
            if (
                not all(math.isfinite(value) and value > 0.0 for value in numeric_dims)
                or not math.isfinite(d)
                or d <= 0.0
                or numeric_dims[0] <= d
            ):
                continue
            B, C = numeric_dims[2], numeric_dims[3]
            result[f"{code_prefix}{bore_code}"] = (B, C)
    return result


def _expand_direct(payload: dict) -> Dict[str, Tuple[float, float, float]]:
    presets = payload.get("presets", {})
    result: Dict[str, Tuple[float, float, float]] = {}
    if not isinstance(presets, dict):
        LOG.warning("Skipping direct preset payload: 'presets' muss ein Objekt sein")
        return result
    for code, dims in presets.items():
        if not isinstance(dims, (list, tuple)) or len(dims) != 3:
            LOG.warning("Skipping %s: erwartet [d, D, B], bekam %r", code, dims)
            continue
        try:
            d, D, B = (float(value) for value in dims)
        except (TypeError, ValueError, OverflowError):
            LOG.warning("Skipping %s: Maße sind keine Zahlen: %r", code, dims)
            continue
        if not all(math.isfinite(value) for value in (d, D, B)) or d <= 0.0 or D <= d or B <= 0.0:
            LOG.warning("Skipping %s: ungültige Lagermaße [d, D, B]=%r", code, dims)
            continue
        result[str(code)] = (d, D, B)
    return result


def _expand(payload: dict) -> Dict[str, Tuple[float, float, float]]:
    if not isinstance(payload, dict):
        LOG.warning("Skipping norm payload: Wurzel muss ein JSON-Objekt sein")
        return {}
    coding = payload.get("coding", "direct")
    if coding == "din623":
        return _expand_din623(payload)
    if coding == "direct":
        return _expand_direct(payload)
    LOG.warning("Unbekanntes coding %r – ignoriere Datei", coding)
    return {}


def load_presets_for(bearing_type: str) -> Dict[str, Tuple[float, float, float]]:
    """Lädt Default-Presets und merged optionale User-Datei darüber."""
    filename = _TYPE_FILES.get(bearing_type)
    if filename is None:
        return {}
    default_path = _DATA_DIR / filename
    try:
        payload = _load_json(default_path)
    except (OSError, json.JSONDecodeError) as exc:
        LOG.error("Konnte %s nicht laden: %s", default_path, exc)
        return {}
    presets = _expand(payload)

    user_path = _user_data_path(filename)
    if user_path is not None:
        try:
            user_payload = _load_json(user_path)
            presets.update(_expand(user_payload))
            LOG.info("User-Presets aus %s zusammengeführt", user_path)
        except (OSError, json.JSONDecodeError) as exc:
            LOG.warning("User-Datei %s ignoriert: %s", user_path, exc)
    return presets


def load_all_presets() -> Dict[str, Dict[str, Tuple[float, float, float]]]:
    return {bt: load_presets_for(bt) for bt in _TYPE_FILES}


def load_ring_widths_for(bearing_type: str) -> Dict[str, Tuple[float, float]]:
    """Liefert getrennte Innen-/Außenring-Breiten (B, C) für den Typ, soweit
    in den Maßreihen-Daten hinterlegt (4-elementige Einträge)."""
    filename = _TYPE_FILES.get(bearing_type)
    if filename is None:
        return {}
    try:
        payload = _load_json(_DATA_DIR / filename)
    except (OSError, json.JSONDecodeError):
        return {}
    widths = _extract_ring_widths(payload)
    user_path = _user_data_path(filename)
    if user_path is not None:
        try:
            widths.update(_extract_ring_widths(_load_json(user_path)))
        except (OSError, json.JSONDecodeError):
            pass
    return widths


def norm_hint_for(bearing_type: str) -> str:
    filename = _TYPE_FILES.get(bearing_type)
    if filename is None:
        return ""
    try:
        payload = _load_json(_DATA_DIR / filename)
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        LOG.warning("Katalog %s hat keine Objekt-Wurzel; Normhinweis ausgelassen", filename)
        return ""
    value = payload.get("norm", "")
    return value if isinstance(value, str) else ""


def _load_default_payload(bearing_type: str) -> dict:
    filename = _TYPE_FILES.get(bearing_type)
    if filename is None:
        return {}
    try:
        payload = _load_json(_DATA_DIR / filename)
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        LOG.error("Katalog %s hat keine JSON-Objekt-Wurzel", filename)
        return {}
    return payload


def coding_for(bearing_type: str) -> str:
    """Liefert das Coding-Schema (``'din623'``, ``'direct'`` oder ``''``).

    Über das Coding entscheidet die UI, ob der Workflow ``Reihe →
    Bohrungskennzahl`` (din623) oder eine direkte Code-Auswahl (direct,
    z. B. HK0808, SG10) zum Einsatz kommt.
    """
    return _load_default_payload(bearing_type).get("coding", "")


def load_series_for(bearing_type: str) -> list:
    """Liefert die Massreihen-Codes (inkl. Prefix) eines DIN 623-Lagertyps.

    Für Lagertypen mit anderem Coding (``direct``) wird eine leere Liste
    zurückgegeben. Eine optionale User-Datei wird über die Defaults gemerged.
    """
    payload = _load_default_payload(bearing_type)
    if payload.get("coding") != "din623":
        return []
    prefix = payload.get("prefix", "")
    names = set(payload.get("series", {}).keys())
    user_path = _user_data_path(_TYPE_FILES[bearing_type])
    if user_path is not None:
        try:
            user_payload = _load_json(user_path)
            if isinstance(user_payload, dict) and user_payload.get("coding") == "din623":
                user_series = user_payload.get("series", {})
                if isinstance(user_series, dict):
                    names.update(user_series.keys())
        except (OSError, json.JSONDecodeError):
            pass
    return sorted(f"{prefix}{name}" for name in names)


def load_bore_codes_for(bearing_type: str, series_code: str) -> list:
    """Liefert die Bohrungskennzahlen einer Massreihe, sortiert nach Bohrungs-Ø.

    Ungültige Kennzahlen (außerhalb DIN 623 04..96) werden übersprungen.
    Eine optionale User-Datei wird über die Defaults gemerged.
    """
    payload = _load_default_payload(bearing_type)
    if payload.get("coding") != "din623":
        return []
    prefix = payload.get("prefix", "")
    if prefix and series_code.startswith(prefix):
        key = series_code[len(prefix):]
    else:
        key = series_code
    entries: dict = dict(payload.get("series", {}).get(key, {}))
    user_path = _user_data_path(_TYPE_FILES[bearing_type])
    if user_path is not None:
        try:
            user_payload = _load_json(user_path)
            if isinstance(user_payload, dict) and user_payload.get("coding") == "din623":
                user_series = user_payload.get("series", {})
                user_entries = user_series.get(key, {}) if isinstance(user_series, dict) else {}
                if isinstance(user_entries, dict):
                    entries.update(user_entries)
        except (OSError, json.JSONDecodeError):
            pass
    sortable = []
    for code in entries:
        try:
            d = din623.bore_code_to_diameter(code)
        except ValueError:
            continue
        sortable.append((d, code))
    sortable.sort()
    return [code for _, code in sortable]
