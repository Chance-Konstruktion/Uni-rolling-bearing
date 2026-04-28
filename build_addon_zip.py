"""Erzeugt eine Blender-installierbare ZIP-Datei für das Addon.

Aufruf:

    python build_addon_zip.py            # legt dist/uni_rolling_bearing.zip an
    python build_addon_zip.py -o foo.zip # eigener Zielpfad

Die ZIP enthält ausschließlich den Addon-Ordner (kein README/Tests/.git),
so wie ihn Blender unter ``Edit > Preferences > Add-ons > Install...``
erwartet.
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import zipfile

ADDON_DIR_NAME = "uni_rolling_bearing"
DEFAULT_OUTPUT = pathlib.Path("dist") / f"{ADDON_DIR_NAME}.zip"

# Dateien/Verzeichnisse, die nicht ins Release wandern.
EXCLUDE_NAMES = {"__pycache__", ".pytest_cache", ".mypy_cache"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def _should_include(path: pathlib.Path) -> bool:
    if path.name in EXCLUDE_NAMES:
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    return True


def build(output: pathlib.Path) -> pathlib.Path:
    repo_root = pathlib.Path(__file__).resolve().parent
    addon_dir = repo_root / ADDON_DIR_NAME
    if not addon_dir.is_dir():
        raise SystemExit(f"Addon-Ordner nicht gefunden: {addon_dir}")

    output = output if output.is_absolute() else (repo_root / output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    written = 0
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(addon_dir.rglob("*")):
            if not _should_include(path):
                continue
            if path.is_dir():
                continue
            arcname = path.relative_to(addon_dir.parent)
            zf.write(path, arcname.as_posix())
            written += 1

    print(f"OK: {output} ({written} Dateien)")
    return output


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Build Blender addon ZIP.")
    parser.add_argument(
        "-o", "--output",
        type=pathlib.Path,
        default=DEFAULT_OUTPUT,
        help=f"Zielpfad (Default: {DEFAULT_OUTPUT}).",
    )
    args = parser.parse_args(argv)
    build(args.output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
