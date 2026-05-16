"""Baut ``dist/uni_rolling_bearing.zip`` für die Blender-Installation.

Das Skript bündelt ausschließlich den Addon-Ordner ``uni_rolling_bearing/``
(ohne ``__pycache__``, Tests, Repo-Metadaten o. Ä.) – genau das Format, das
Blender im Dialog ``Edit > Preferences > Add-ons > Install...`` erwartet.

Aufruf::

    python build_addon_zip.py
"""

from __future__ import annotations

import pathlib
import sys
import zipfile

REPO_ROOT = pathlib.Path(__file__).resolve().parent
ADDON_DIR = REPO_ROOT / "uni_rolling_bearing"
DIST_DIR = REPO_ROOT / "dist"
ZIP_PATH = DIST_DIR / "uni_rolling_bearing.zip"

# Dateien/Verzeichnisse, die nicht in die Distribution wandern.
SKIP_DIRS = {"__pycache__", ".pytest_cache"}
SKIP_SUFFIXES = {".pyc", ".pyo"}


def _iter_addon_files() -> list[pathlib.Path]:
    files: list[pathlib.Path] = []
    for path in ADDON_DIR.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(ADDON_DIR).parts):
            continue
        if path.suffix in SKIP_SUFFIXES:
            continue
        files.append(path)
    return sorted(files)


def build() -> pathlib.Path:
    if not ADDON_DIR.is_dir():
        raise SystemExit(f"Addon-Ordner nicht gefunden: {ADDON_DIR}")
    DIST_DIR.mkdir(parents=True, exist_ok=True)

    files = _iter_addon_files()
    if not files:
        raise SystemExit(f"Keine Quelldateien unter {ADDON_DIR} gefunden.")

    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for src in files:
            arcname = src.relative_to(REPO_ROOT).as_posix()
            zf.write(src, arcname)

    return ZIP_PATH


if __name__ == "__main__":
    out = build()
    print(f"ZIP geschrieben: {out.relative_to(REPO_ROOT)} ({out.stat().st_size} bytes)")
    sys.exit(0)
