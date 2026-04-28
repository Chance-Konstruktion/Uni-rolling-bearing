# UNI Rolling Bearing Generator (Blender Addon)

Ein Blender-Addon zur Erstellung parametrischer Wälzlager (Kugel-, Zylinderrollen-, Nadel-, Kegelrollen- und Tonnenlager) über ein übersichtliches N-Panel.

## Ziele des Addons

- **Kompakte Bedienung** im N-Panel mit Lagertyp-Dropdown als Einstieg.
- **Normorientierte Eingabe** über Presets und Toleranz-/Lagerluft-Felder.
- **Funktionsfähige Geometrie** durch Plausibilitätsprüfung und Auto-Fit von Wälzkörper-Parametern.
- **Manifold-orientierte Meshes** für alle erzeugten Komponenten.

## Unterstützte Lagertypen

- Kugellager
- Zylinderrollenlager
- Nadellager
- Kegelrollenlager
- Tonnenlager (sphärische Rollen)

## Normenbezug (aktueller Stand)

> Hinweis: Das Addon enthält aktuell **praxisnahe Start-Presets** und normorientierte Felder, aber noch **keine vollständige digitale Normdatenbank**.

Aktuell berücksichtigt:

- **ISO 15 / DIN ISO 15**: Hauptabmessungslogik über Preset-Ansatz.
- **DIN 625**: Fokus bei Kugellager-Startwerten.
- **ISO 492 / DIN 620**: Toleranzklassenauswahl als Metadatum.
- **DIN 623**: Preset-/Baureihen-Logik in Richtung Bezeichnungssystem.

Geplant (siehe ROADMAP):

- Vollständige Tabellen je Baureihe.
- Erweiterte Toleranz-/Passungsberechnung.
- Tragzahl-/Lebensdauerkennwerte (ISO 281 / ISO 76).

## Installation

### Variante A – Fertige ZIP bauen (empfohlen)

```bash
python build_addon_zip.py
```

Das Skript schreibt `dist/uni_rolling_bearing.zip`. Diese ZIP enthält genau
den Addon-Ordner (ohne README, Tests, `.git` o. Ä.) – also genau das Format,
das Blender erwartet.

In Blender:

1. `Edit > Preferences > Add-ons > Install…`
2. `dist/uni_rolling_bearing.zip` auswählen.
3. Addon-Häkchen aktivieren („UNI Rolling Bearing Generator“).
4. In der 3D-View mit `N` das Sidebar öffnen.
5. Tab **UNI Bearings** auswählen.

### Variante B – Direkt aus dem Repo (Entwickler)

Den Ordner `uni_rolling_bearing/` (nicht das ganze Repo!) in das Blender-
Addon-Verzeichnis kopieren bzw. symlinken:

| OS      | Pfad |
|---------|------|
| Windows | `%APPDATA%\Blender Foundation\Blender\<version>\scripts\addons\` |
| macOS   | `~/Library/Application Support/Blender/<version>/scripts/addons/` |
| Linux   | `~/.config/blender/<version>/scripts/addons/` |

Anschließend in Blender im Add-on-Dialog aktivieren.

## Bedienung

1. **Lagertyp wählen** (Dropdown).
2. Optional **Norm-Preset** anwenden.
3. Geometrieparameter setzen (`d`, `D`, `B`, Ringstärke).
4. Wälzkörper-Parameter setzen (`Ø`, Anzahl, Umfangsspalt).
5. **Auto-Fit** aktiv lassen, damit unplausible Kombinationen automatisch korrigiert werden.
6. Unten auf **Erstellen** klicken.

## Was wurde für „funktionsfähig“ verbessert?

Frühere Versionen konnten Geometrien erzeugen, bei denen:

- Wälzkörper zu groß waren und in Ringe schnitten,
- zu viele Wälzkörper gesetzt wurden und kollidierten,
- alles zu einem einzelnen Mesh verschmolz (keine funktionale Baugruppe).

Aktueller Stand:

- Plausibilitätsrechnung löst die Geometrie zuerst auf.
- Bei aktivem Auto-Fit werden `Wälzkörper-Ø` und `Anzahl` begrenzt.
- Komponenten bleiben als **separate Teile** unter einer gemeinsamen `Bearing`-Assembly (Empty parent) erhalten.

## Technische Details

- Einheiten der Eingabe: **Millimeter**.
- Blender-Skalierung beim Erzeugen: **mm -> m** (`0.001`).
- Jeder Ring/Wälzkörper wird als eigenes manifold Mesh erzeugt.
- Pro Erzeugung wird eine eigene Collection `Bearing_<Typ>` angelegt.

## Kegelrollenlager: Kontaktwinkel

Für Kegelrollenlager ist der Kontaktwinkel α einstellbar (Default 14°). Die
Wälzkörper werden im Mesh-Frame um die lokale Y-Achse gekippt, *bevor* sie auf
den Teilkreis rotiert werden – die Achsen aller Rollen treffen sich daher
exakt auf der Lagerachse in einem gemeinsamen Apex. Der berechnete Apex-Z
wird als Metadatum (`tapered_apex_z_mm`) am Bearing-Empty hinterlegt. Die
Laufbahnen (Innen-/Außenring) bleiben in v0.5.0 noch zylindrisch.

## Käfig (optional)

Über die Checkbox **Käfig erzeugen** wird ein einfacher parametrischer
Leiter-Käfig miterzeugt: zwei axiale Endplatten zwischen Lagerrand und
Wälzkörperende, verbunden durch tangentiale Webs in den Lücken zwischen den
Wälzkörpern. Der Käfig wird als eigene `Cage`-Sub-Assembly unter dem
Bearing-Empty geparented. Ist zu wenig Bauraum vorhanden (Wälzkörper füllen
fast die ganze Breite, kein Tangentialspalt o. Ä.), meldet das Addon eine
Warnung und überspringt den Käfig.

## Einschränkungen

- Keine FEM-/Kontaktmechanik.
- Keine exakte DIN/ISO-Tabellenabdeckung aller Reihen.
- Käfig ist eine vereinfachte Leiterstruktur ohne typ-spezifische Pockets.

## Entwicklung

Modulstruktur des Addons:

```
uni_rolling_bearing/
├── __init__.py        # bl_info, register/unregister (lazy bpy-Import)
├── constants.py       # Lagertyp-IDs, Presets, Normhinweise
├── geometry.py        # Pure Geometriefunktionen (testbar ohne Blender)
├── mesh_builders.py   # BMesh-Helfer (Ringe, Kugeln, Rollen, Tonnen)
├── properties.py      # PropertyGroup für das N-Panel
├── operators.py       # Erstell-/Preset-Operatoren
└── panel.py           # N-Panel UI
```

Syntaxcheck lokal:

```bash
python -m compileall uni_rolling_bearing/
```

Unit-Tests (laufen ohne Blender, prüfen die Geometrie-Schicht):

```bash
python -m unittest discover tests
```

## Lizenz

Siehe `LICENSE`.
