"""Baut ``dist/uni_rolling_bearing.zip`` für die Blender-Installation.

Das Skript bündelt ausschließlich den Addon-Ordner ``uni_rolling_bearing/``
(ohne ``__pycache__``, Tests, Repo-Metadaten o. Ä.) – genau das Format, das
Blender im Dialog ``Edit > Preferences > Add-ons > Install...`` erwartet.

Aufruf::

    python build_addon_zip.py          # ZIP (neu) bauen
    python build_addon_zip.py --check  # nur prüfen, ob die ZIP synchron ist

Der ``--check``-Modus schreibt nichts und liefert Exitcode 1, wenn die
committete ZIP nicht Datei-für-Datei zum Quellbaum passt – ideal für die CI.
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


def check() -> int:
    """Prüft, ob ``ZIP_PATH`` inhaltlich dem aktuellen Quellbaum entspricht.

    Vergleicht Dateiliste und -inhalte (Byte-für-Byte), unabhängig von
    Kompressions- oder Zeitstempel-Unterschieden. Gibt 0 bei Übereinstimmung,
    sonst 1 zurück und listet die Abweichungen auf.
    """
    if not ZIP_PATH.is_file():
        print(f"FEHLT: {ZIP_PATH.relative_to(REPO_ROOT)} – bitte 'python build_addon_zip.py' ausführen.")
        return 1

    expected = {
        src.relative_to(REPO_ROOT).as_posix(): src.read_bytes()
        for src in _iter_addon_files()
    }
    problems: list[str] = []
    with zipfile.ZipFile(ZIP_PATH) as zf:
        zip_names = {n for n in zf.namelist() if not n.endswith("/")}
        expected_names = set(expected)
        for missing in sorted(expected_names - zip_names):
            problems.append(f"fehlt in ZIP: {missing}")
        for extra in sorted(zip_names - expected_names):
            problems.append(f"überzählig in ZIP: {extra}")
        for name in sorted(expected_names & zip_names):
            if zf.read(name) != expected[name]:
                problems.append(f"Inhalt weicht ab: {name}")

    if problems:
        print("dist-ZIP ist NICHT synchron mit dem Quellbaum:")
        for problem in problems:
            print(f"  - {problem}")
        print("Bitte 'python build_addon_zip.py' ausführen und das ZIP committen.")
        return 1

    print(f"dist-ZIP ist synchron ({len(expected)} Dateien).")
    return 0


if __name__ == "__main__":
    if "--check" in sys.argv[1:]:
        sys.exit(check())
    out = build()
    print(f"ZIP geschrieben: {out.relative_to(REPO_ROOT)} ({out.stat().st_size} bytes)")
    sys.exit(0)
