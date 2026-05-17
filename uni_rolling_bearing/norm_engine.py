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
    for series_name, entries in series.items():
        if prefix:
            code_prefix = prefix + series_name
        elif series_name.startswith("6"):
            code_prefix = series_name
        else:
            code_prefix = series_name
        for bore_code, dims in entries.items():
            if len(dims) != 2:
                LOG.warning("Skipping %s/%s: erwartet [D, B], bekam %r",
                            series_name, bore_code, dims)
                continue
            try:
                d = din623.bore_code_to_diameter(bore_code)
            except ValueError as exc:
                LOG.warning("Skipping %s/%s: %s", series_name, bore_code, exc)
                continue
            D, B = float(dims[0]), float(dims[1])
            result[f"{code_prefix}{bore_code}"] = (d, D, B)
    return result


def _expand_direct(payload: dict) -> Dict[str, Tuple[float, float, float]]:
    presets = payload.get("presets", {})
    result: Dict[str, Tuple[float, float, float]] = {}
    for code, dims in presets.items():
        if len(dims) != 3:
            LOG.warning("Skipping %s: erwartet [d, D, B], bekam %r", code, dims)
            continue
        result[code] = (float(dims[0]), float(dims[1]), float(dims[2]))
    return result


def _expand(payload: dict) -> Dict[str, Tuple[float, float, float]]:
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


def norm_hint_for(bearing_type: str) -> str:
    filename = _TYPE_FILES.get(bearing_type)
    if filename is None:
        return ""
    try:
        payload = _load_json(_DATA_DIR / filename)
    except (OSError, json.JSONDecodeError):
        return ""
    return payload.get("norm", "")
