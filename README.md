# UNI Rolling Bearing Generator (Blender Addon)

[![Tests](https://github.com/Chance-Konstruktion/Uni-rolling-bearing/actions/workflows/tests.yml/badge.svg)](https://github.com/Chance-Konstruktion/Uni-rolling-bearing/actions/workflows/tests.yml)

Ein Blender-Addon zur Erstellung parametrischer Wälzlager (Kugel-, Zylinderrollen-, Nadel-, Kegelrollen- und Tonnenlager) über ein übersichtliches N-Panel.

## Ziele des Addons

- **Kompakte Bedienung** im N-Panel mit Lagertyp-Dropdown als Einstieg.
- **Normorientierte Eingabe** über Presets und Toleranz-/Lagerluft-Felder.
- **Funktionsfähige Geometrie** durch Plausibilitätsprüfung und Auto-Fit von Wälzkörper-Parametern.
- **Manifold-orientierte Meshes** für alle erzeugten Komponenten.

## Unterstützte Lagertypen

- Kugellager (Rillenkugellager, DIN 625)
- Zylinderrollenlager
- Nadellager
- Kegelrollenlager
- Tonnenlager (sphärische Rollen)
- **U-Rillen-Kugellager / Führungsrolle (SG-Reihe)** – Kugellager mit
  V-/U-Rille im Außenmantel, Presets `SG10`, `SG15`, `SG20`, `SG25`,
  `SG35`, `SG66`

## Normenbezug (aktueller Stand)

> Hinweis: Das Addon enthält aktuell **praxisnahe Start-Presets** und normorientierte Felder, aber noch **keine vollständige digitale Normdatenbank**.

Aktuell berücksichtigt:

- **ISO 15 / DIN ISO 15**: Maßreihen für Rillenkugel-, Zylinderrollen-,
  Kegelrollen- und Pendelrollenlager als JSON-Datenquelle (`norm_engine.py`).
- **DIN 623**: Bohrungskennzahl-Logik (`din623.py`); ~80 Rillenkugellager-
  Größen aus den Tabellen generiert.
- **DIN 625**: Rillenkugellager-Reihen 60/62/63/64/618/619.
- **DIN 720**: Kegelrollen-Reihen 302/303/313/320/322/323 inkl. getrennter
  Cone/Cup-Breiten.
- **ISO 492 / DIN 620**: Toleranzklassen NORMAL/P6/P5/P4 werden in µm-
  Abweichungen für d/D/B umgerechnet und als Metadaten hinterlegt.
- **DIN 5418**: Empfohlene Welle-/Gehäuse-Passungen (g6…p6, G7…P7) je
  Belastungsfall mit ISO 286-Abmaßen.
- **ISO 76 / ISO 281**: Statische/dynamische Tragzahl und L10h-Lebensdauer
  als Live-Vorschau im Panel. Die Beiwerte `f0`/`fc` werden über das
  Hüllkurvenverhältnis γ = Dw·cos(α)/dm aus den ISO-Annex-Tabellen
  interpoliert; γ, `f0`, `fc` werden zusätzlich als Metadaten am
  Bearing-Empty abgelegt. Eingaben für radiale Last `Fr` und axiale Last
  `Fa` werden über X-/Y-Faktoren (ISO 281 Tabelle 4) zur äquivalenten
  Last `P = X·Fr + Y·Fa` kombiniert. Kugellager-Tabelle ist
  Fa/C0r-interpoliert; Kegelrollen/Pendelrollen rechnen über den
  Kontaktwinkel α; Zylinderrollen-/Nadellager ignorieren `Fa`.

Geplant (siehe ROADMAP):

- SG-Zwischengrößen (SG30/40/55) – ausstehend, bis belastbare Maßquellen
  vorliegen. Die U-Profil-Variante der SG-Außenrille ist seit v0.24 verfügbar
  (`vgroove_shape` = U).

## Installation

### Variante A – Fertige ZIP direkt herunterladen

Im Repo liegt unter [`dist/uni_rolling_bearing.zip`](dist/uni_rolling_bearing.zip)
eine vorgebaute, Blender-installierbare ZIP. Auf GitHub einfach diese Datei
über „Download raw file“ herunterladen und in Blender importieren – kein
lokaler Build nötig.

### Variante B – Fertige ZIP selbst bauen

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

### Variante C – Direkt aus dem Repo (Entwickler)

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
2. Optional **Norm-Preset** anwenden:
   - Für Lagertypen mit DIN 623-Coding (Kugel-, Zylinderrollen-, Kegelrollen-,
     Pendelrollenlager) zuerst die **Massreihe** wählen (z. B. `60`, `62`,
     `NU3`), dann die **Bohrungskennzahl** (`00`..`96`). Die kombinierte
     Bezeichnung (z. B. `6204`, `NU306`, `30212`) und der abgeleitete
     Bohrungs-Ø werden live angezeigt.
   - Für Lagertypen mit direkter Code-Auswahl (Nadel-, SG-Reihe) bleibt der
     freie Reihen-Code-Dropdown (z. B. `HK1010`, `SG20`).
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

## Laufbahnen (ab v0.6)

Die Innen- und Außenringe werden seit v0.6 nicht mehr als reine Hohlzylinder
erzeugt, sondern aus einem typabhängigen Querschnittsprofil zu einem manifold
Volumen revolviert (Modul `raceway.py`). Folgende Laufbahnen werden modelliert:

- **Kugellager** – Rillen-Bogen (groove) mit Konformitätsfaktor f = r_groove/d_ball
  in Innen- und Außenring. Reicht der Bogen geometrisch nicht bis zur Schulter
  (z. B. weil der Wälzkörper-Ø sehr klein gewählt wurde), fällt das Profil
  automatisch auf einen Hohlzylinder zurück. Zusätzlich kann eine 45°-Fase
  (DIN 620 / ISO 582 r_s) an der Bohrungs- bzw. Außenring-Kante eingestellt
  werden (`bearing_chamfer_mm`, Default 0.3 mm). Die Fase wird bei zu wenig
  Bauraum automatisch heruntergeclampt.
- **Zylinderrollen-/Nadellager** – NU-Bauart: Außenring mit zwei radial nach
  innen vorstehenden Borden, die die Rollen axial halten; Innenring zylindrisch.
  Bei zu engem Bauraum (Rolle füllt nahezu die ganze Lagerbreite) wird der
  Bord automatisch weggelassen.
- **Kegelrollenlager** – Beide Ringe haben tatsächlich konische Laufbahnen,
  geneigt mit dem Kontaktwinkel α (siehe nächster Abschnitt).
- **Tonnenlager / Pendelrollenlager** – Außenring mit sphärischer
  Innenlaufbahn, deren Sphärenradius automatisch aus Pitch-Ø und
  Wälzkörperabmaßen abgeleitet wird.
- **U-Rillen-Kugellager (SG)** – Innen identisch zum Rillenkugellager,
  zusätzlich V-Rille im Außenmantel des Außenrings. Tiefe und Halbwinkel
  der V-Rille sind im Panel einstellbar (`vgroove_depth_mm`,
  `vgroove_half_angle_deg`); 0 mm Tiefe wählt automatisch ≈35 % der
  Außenwand. Bei zu wenig Bauraum (sehr dünne Außenwand) fällt das Profil
  auf das Standard-Kugellager-Außenringprofil zurück.

## Kegelrollenlager: Kontaktwinkel

Für Kegelrollenlager ist der Kontaktwinkel α einstellbar (Default 14°). Die
Wälzkörper werden im Mesh-Frame um die lokale Y-Achse gekippt, *bevor* sie auf
den Teilkreis rotiert werden – die Achsen aller Rollen treffen sich daher
exakt auf der Lagerachse in einem gemeinsamen Apex. Der berechnete Apex-Z
wird als Metadatum (`tapered_apex_z_mm`) am Bearing-Empty hinterlegt. Seit
v0.6 sind die Laufbahnen passend zu α geneigt (vorher zylindrisch).

## Käfig (optional)

Über die Checkbox **Käfig erzeugen** wird ein parametrischer Käfig miterzeugt
und als eigene `Cage`-Sub-Assembly unter dem Bearing-Empty geparented.

Seit v0.7 ist der Default ein **einteiliger Sleeve-Käfig mit typabhängigen
Pockets**: Aus einem Hohlzylinder werden per Boolean-Difference oversized
Wälzkörper-Stempel herausgeschnitten, sodass die Pockets typgerecht
sphärisch (Kugel), zylindrisch (Zylinder/Nadel), kegelig (Kegelrolle) oder
tonnenförmig (Tonnenlager) entstehen. Der erzeugte Pocket-Käfig wird als
`cage_style = "pocket"` am Bearing-Empty markiert.

Seit v0.21 gibt es zusätzlich die Bauart **Massiv** (`cage_style = "massive"`):
ein Pocket-Sleeve mit radialen Schmiertaschen-Bohrungen im tangentialen
Steg zwischen je zwei Wälzkörper-Pockets, wie sie für gefräste Messing-
Massivkäfige typisch sind. Der Durchmesser kann manuell vorgegeben oder
automatisch gewählt werden (`oil_pocket_diameter_mm`, 0 = automatisch);
reicht der Bauraum nicht, fällt der Käfig auf einen reinen Pocket-Sleeve
zurück.

Schlägt der Boolean fehl (z. B. wegen degenerierter Cutter bei sehr grober
Auflösung), fällt das Addon automatisch auf den historischen
**Leiter-Käfig** zurück (`cage_style = "ladder"`): zwei axiale Endplatten
zwischen Lagerrand und Wälzkörperende, verbunden durch tangentiale Webs in
den Lücken zwischen den Wälzkörpern.

Ist zu wenig Bauraum vorhanden (Wälzkörper füllen fast die ganze Breite,
kein Tangentialspalt o. Ä.), meldet das Addon eine Warnung und überspringt
den Käfig komplett.

## Einschränkungen

- Keine FEM-/Kontaktmechanik.
- Keine vollständige DIN/ISO-Tabellenabdeckung aller Reihen.
- Tragzahlen und Lebensdauer sind vereinfachte Näherungen, keine
  zertifizierten Auslegungswerte.

## Entwicklung

Modulstruktur des Addons:

```
uni_rolling_bearing/
├── __init__.py        # bl_info, register/unregister (lazy bpy-Import)
├── constants.py       # Lagertyp-IDs, Presets, Normhinweise
├── geometry.py        # Pure Geometriefunktionen (testbar ohne Blender)
├── raceway.py         # Laufbahn-Querschnittsprofile (testbar ohne Blender)
├── mesh_builders.py   # BMesh-Helfer (Ringe, Revolution, Kugeln, Rollen, Tonnen)
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
