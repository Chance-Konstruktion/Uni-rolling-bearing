<div align="center">

<img src="assets/banner.svg" alt="UNI Rolling Bearing Generator" width="100%">

# ⚙️ UNI Rolling Bearing Generator

**Parametrische, normgerechte Wälzlager — ein Geometrie-Kern, zwei Hosts.**
<br>
<sub>Parametric standard rolling bearings for <b>Blender</b> &amp; <b>FreeCAD</b> from a single shared core.</sub>

<br>

[![Tests](https://github.com/Chance-Konstruktion/Uni-rolling-bearing/actions/workflows/tests.yml/badge.svg)](https://github.com/Chance-Konstruktion/Uni-rolling-bearing/actions/workflows/tests.yml)
![Version](https://img.shields.io/badge/version-0.30.0-f5c518)
![Tests](https://img.shields.io/badge/tests-202%20passing-3fb950)
![Blender](https://img.shields.io/badge/Blender-3.6%2B-ea7600)
![FreeCAD](https://img.shields.io/badge/FreeCAD-0.21%2B-1f80c0)
![License](https://img.shields.io/badge/license-GPLv3-9aa3ad)

**🇩🇪 Deutsch** · [🇬🇧 English](README.md)

[**Quick Start**](#quick-start) · [**Architektur**](#architektur) · [**Lagertypen**](#lagertypen) · [**FreeCAD**](#freecad) · [Changelog](CHANGELOG.md) · [Roadmap](ROADMAP.md)

</div>

---

## Was ist das? 🎯

Ein Generator für **funktionsfähige Wälzlager** (Kugel-, Zylinder-, Nadel-, Kegel-,
Tonnen-/Pendel- und U-Rillen-Lager) — bedienbar über ein **Blender-N-Panel** *und* eine
**FreeCAD-Workbench**. Beide Hosts teilen sich denselben `bpy`-/`FreeCAD`-freien
Geometrie-Kern, also rechnen sie *identisch* — Blender liefert ein Mesh, FreeCAD ein
exportierbares BREP-Solid.

> 💡 **Kurz gesagt:** Du gibst `d · D · B` ein, wählst den Lagertyp — und bekommst ein
> normorientiertes, kollisionsfreies Lager mit echten Laufbahnen, Wälzkörpern und
> optionalem Käfig.

<table>
<tr>
<td width="33%" valign="top">

### 📐 Normgerecht
ISO 15 Maßreihen, DIN 623/625/720/635, ISO 492-Toleranzen und DIN-5418-Passungen — als Presets *und* Live-Berechnung.

</td>
<td width="33%" valign="top">

### 🧩 Funktionsfähig
Auto-Fit begrenzt Wälzkörper-Ø &amp; Anzahl auf Plausibles. Keine clippenden Kugeln, keine kollidierenden Rollen, manifold-taugliche Geometrie.

</td>
<td width="33%" valign="top">

### 🔗 Zwei Hosts
Ein host-freier Kern → Blender-Mesh **und** FreeCAD-Solid. STEP/IGES-Export nativ über FreeCAD, ganz ohne Bridge.

</td>
</tr>
</table>

---

## Highlights ✨

<table>
<tr>
<td width="50%">

🧱 **6 Lagertypen** — Rillenkugel, Zylinder, Nadel, Kegel, Tonne/Pendel, U-Rillen (SG)

</td>
<td width="50%">

📐 **Normbezug** — ISO 15 · DIN 623/625/720 · ISO 492/76/281 · DIN 5418

</td>
</tr>
<tr>
<td>

🔩 **Echte Laufbahnen** — Rillenbögen, konische Apex-Geometrie, Sphären

</td>
<td>

⚖️ **Tragzahlen live** — `C0r`, `Cr`, `P`, `L10h` direkt im Panel

</td>
</tr>
<tr>
<td>

🛟 **Käfig** — Pocket · Massiv · Ribbon · Leiter (Boolean-Pockets)

</td>
<td>

🧮 **Auto-Fit** — korrigiert unplausible Kombinationen still

</td>
</tr>
<tr>
<td>

📦 **STEP / IGES** — nativ über FreeCAD-BREP-Solids

</td>
<td>

🧪 **202 Tests** — host-frei, laufen ohne Blender/FreeCAD

</td>
</tr>
</table>

---

## Architektur 🧩

Ein **geteilter Geometrie-Kern** ohne `bpy`/`FreeCAD`, zwei dünne Frontends:

<pre>
                 ┌───────────────────────────────────────────┐
                 │   uni_rolling_bearing/  ·  KERN (host-frei)│
                 │   geometry · raceway · ratings · fits      │
                 │   tolerances · norm_engine · din623        │
                 └───────────────┬───────────────┬────────────┘
                                 │               │
              resolve_geometry() │               │ build_plan()
                                 ▼               ▼
                 ┌───────────────────┐   ┌────────────────────────┐
                 │  Blender-Frontend │   │  FreeCAD-Frontend       │
                 │  mesh_builders    │   │  freecad_backend/       │
                 │  operators·panel  │   │  plan · backend · ui    │
                 │  → BMesh-Objekte  │   │  → Part-BREP-Solids     │
                 └───────────────────┘   └────────────────────────┘
                          │                         │
                       🟧 Mesh                  🟦 Solid → STEP/IGES
</pre>

<details>
<summary><b>Vollständige Modulstruktur</b></summary>

```
uni_rolling_bearing/      # Geteilter Kern + Blender-Frontend
├── constants.py       # Lagertyp-IDs, Presets, Normhinweise            [Kern]
├── geometry.py        # Pure Geometriefunktionen (testbar ohne Host)   [Kern]
├── raceway.py         # Laufbahn-Querschnittsprofile (ohne Host)       [Kern]
├── ratings.py · fits.py · tolerances.py · norm_engine.py · din623.py   [Kern]
├── mesh_builders.py   # BMesh-Helfer (Ringe, Revolution, Kugeln, …)  [Blender]
├── properties.py      # PropertyGroup für das N-Panel                [Blender]
├── operators.py       # Erstell-/Preset-Operatoren                   [Blender]
└── panel.py           # N-Panel UI                                   [Blender]

freecad_backend/          # FreeCAD-Frontend (nutzt denselben Kern)
├── params.py          # host-freie BearingParams (spiegelt die UI)
├── plan.py            # host-freier BearingPlan (Profile + Platzierungen)
├── backend_freecad.py # baut Part-Solids aus dem Plan (Polygon-Revolve)
├── uischema.py        # host-freies Property-Schema + Sichtbarkeitsregeln
└── workbench/
    ├── wb_bearing.py  # Part::FeaturePython-Proxy (Live-Rebuild, Editor)
    ├── wb_commands.py # GUI-Command „Lager erzeugen"
    └── icons/         # Workbench-Icon
InitGui.py · package.xml  # FreeCAD-Workbench-Discovery (Repo-Root)
```

Der Kern importiert **weder** `bpy` **noch** `FreeCAD` — beide Frontends rufen dieselbe
Geometrie. Deshalb laufen alle Tests ganz ohne installierten Host.
</details>

---

## Quick Start 🚀

### ▶ Blender

1. **ZIP holen** — vorgebaut unter [`dist/uni_rolling_bearing.zip`](dist/uni_rolling_bearing.zip) (oder selbst bauen, s. u.).
2. **Installieren** — `Edit > Preferences > Add-ons > Install…`, ZIP wählen, Häkchen aktivieren.
3. **Öffnen** — in der 3D-View `N` drücken, Tab **UNI Bearings** → Lagertyp wählen → **Erstellen**.

```bash
python build_addon_zip.py        # schreibt dist/uni_rolling_bearing.zip
```

### ⬡ FreeCAD

1. **Mod ablegen** — Repo als Mod-Ordner unter `Mod/` (oder via Addon-Manager); `InitGui.py` + `package.xml` liegen dafür im Root.
2. **Neustart** — Workbench **„UNI Bearings"** erscheint im Dropdown.
3. **Bauen** — Button **„Lager erzeugen"**; alle Parameter stehen im Eigenschaften-Editor und bauen das Lager **live** neu.

```python
# Geometrie auch rein programmatisch nutzbar (benötigt FreeCAD):
from freecad_backend.params import BearingParams
from freecad_backend.backend_freecad import build_bearing

p = BearingParams(bearing_type="BALL", bore_diameter=20, outer_diameter=47, width=14)
p.apply_suggested_defaults()
result = build_bearing(p)        # result.inner_ring / .outer_ring / .elements …
```

> 💡 **Kein CAD-Profi?** Lass **Auto-Fit** an und nimm ein Preset (z. B. `6204`). Damit
> kommt immer ein sauberes, funktionsfähiges Lager raus — auch ohne Detailwissen.

---

## Lagertypen 🧱

| Typ | Norm | Besonderheit |
| :-- | :-- | :-- |
| **Rillenkugellager** | DIN 625 / ISO 15 | Kugel nach DIN-625-Rillenformel, taucht in beide Rillen ein |
| **Zylinderrollenlager** | DIN 5412 / ISO 15 | NU-Bauart mit Borden am Außenring, ~94 % Spaltfüllung |
| **Nadellager** | DIN 617 / ISO 15 | schlanke Rollen, hoher Füllgrad |
| **Kegelrollenlager** | DIN 720 / ISO 355 | konische Laufbahnen mit gemeinsamem Apex, einstellbares α |
| **Tonnen-/Pendelrollenlager** | DIN 635-1/-2 | ein- oder zweireihig, sphärische Außenlaufbahn |
| **U-Rillen-Kugellager (SG)** | SG/W-Reihe | Führungsrolle mit V-/U-Rille im Außenmantel |

<details>
<summary><b>Laufbahnen im Detail</b> — wie die Wälzkörper sitzen</summary>

<br>

- **Kugellager** — Rillen-Bogen mit Konformität `f = r_groove/d_ball` in beiden Ringen.
  Kugel-Ø nach **DIN-625-Rillenformel**: `d_w = Schulterspalt + innere + äußere
  Rillentiefe − Lagerluft` (`geometry.ball_diameter_from_groove`). Die Kugel ist damit
  *größer* als der reine Schulterspalt und taucht über beide Schultern in die Rillen ein,
  statt dazwischen zu schweben. Optionale 45°-Fase (DIN 620 / ISO 582 `r_s`,
  `bearing_chamfer_mm`).
- **Zylinder-/Nadellager** — NU-Außenring mit zwei nach innen vorstehenden Borden;
  Innenring zylindrisch. Rolle füllt den Spalt satt (~94 %, Ringwand `1/8·(D−d)`).
  NU206 → ø≈7.5 mm / 13 Rollen statt zuvor ~5.3 mm / 24.
- **Kegelrollenlager** — Cup-Laufbahn unter α, Kegel-Laufbahn flacher unter `α − 2β`,
  Rolle als echter Kegelstumpf (Halbwinkel β), um `α − β` gekippt. Mittlerer Rollen-Ø
  über `geometry.tapered_roller_diameter` (`d_we ≈ radial_space · cos α`), damit die
  geneigte Rolle senkrecht zu ihrer Achse anliegt.
- **Tonnen-/Pendelrollenlager** — einreihig (DIN 635-1): eine Tonne pro Position auf
  konkaver Innenlaufbahn; zweireihig (DIN 635-2): zwei um ±α geneigte Reihen mit
  Mittelbord. Sphärenradius des Außenrings automatisch aus Pitch-Ø + Wälzkörpermaßen.
- **U-Rillen (SG)** — innen wie Rillenkugellager, zusätzlich V-/U-Rille im Außenmantel
  (`vgroove_depth_mm`, `vgroove_half_angle_deg`, `vgroove_shape`).

</details>

<details>
<summary><b>Kegelrollenlager: Kontaktwinkel</b> — gemeinsamer Apex</summary>

<br>

α (Default 14°) ist die Neigung der Cup-Laufbahn zur Lagerachse. Für reine Rollbewegung
treffen sich Rolle und beide Laufbahnen in einem **gemeinsamen Apex**; daraus leitet das
Tool den halben Kegelwinkel der Rolle ab:

```
β = ½ · (α − arctan( R_i / R_o · tan α ))
```

→ Kegel-(Innen-)Laufbahn unter `α − 2β`, Rollenachse unter `α − β`. Die Rollen werden als
echte Kegelstümpfe um die lokale Y-Achse gekippt, *bevor* sie auf den Teilkreis rotieren.
Der Apex-Z wird als Metadatum (`tapered_apex_z_mm`) hinterlegt.

</details>

<details>
<summary><b>Käfig</b> — Pocket · Massiv · Ribbon · Leiter</summary>

<br>

Checkbox **Käfig erzeugen** → eigene `Cage`-Sub-Assembly. Bauarten:

- **Pocket** (Default) — einteiliger Sleeve, aus dem typgerechte Wälzkörper-Stempel per
  Boolean-Difference herausgeschnitten werden (sphärisch/zylindrisch/kegelig/tonnenförmig).
- **Massiv** — Pocket-Sleeve mit radialen Schmiertaschen-Bohrungen (`oil_pocket_diameter_mm`,
  0 = automatisch), wie bei gefrästen Messing-Massivkäfigen.
- **Ribbon** — zwei genietete Halbringe (Pressblech-Stil).
- **Leiter** — Fallback bei misslungenem Boolean: zwei Endplatten + tangentiale Webs.

Reicht der Bauraum nicht (Wälzkörper füllen fast die ganze Breite), wird der Käfig
übersprungen und gewarnt.

</details>

<details>
<summary><b>Normbezug &amp; Tragzahlen</b> — was abgedeckt ist</summary>

<br>

> **Hinweis:** praxisnahe Start-Presets + normorientierte Felder, noch **keine**
> vollständige digitale Normdatenbank.

- **ISO 15 / DIN ISO 15** — Maßreihen als JSON-Datenquelle (`norm_engine.py`).
- **DIN 623** — Bohrungskennzahl-Logik (`din623.py`), ~80 Rillenkugellager-Größen.
- **DIN 625** — Reihen 60/62/63/64/618/619. **DIN 720** — 302/303/313/320/322/323 mit
  getrennten Cone/Cup-Breiten.
- **ISO 492 / DIN 620** — Klassen NORMAL/P6/P5/P4 → µm-Abweichungen für d/D/B.
- **DIN 5418** — Welle-/Gehäuse-Passungen je Belastungsfall (ISO-286-Abmaße).
- **ISO 76 / ISO 281** — statische/dynamische Tragzahl + L10h live im Panel; `f0`/`fc`
  über γ = `Dw·cos α / dm` interpoliert, äquivalente Last `P = X·Fr + Y·Fa`.

</details>

---

## FreeCAD 🛠️

Das Projekt ist als **FreeCAD-Workbench** verfügbar — derselbe Kern wie in Blender, aber
echte **BREP-Solids** statt Mesh. Rotationskörper entstehen aus **geraden
Polygon-Meridianen** (kein BSpline), damit der FreeCAD-Körper *exakt* dieselben Nennmaße
trifft wie der Blender-Mesh: gerade Schultern bleiben gerade, kein Naht-/Verrundungs-Defekt.

Die Workbench bietet einen `Part::FeaturePython`-Proxy mit **Live-Rebuild** und einem
**kontextabhängigen Eigenschaften-Editor** (nur Felder, die der gewählte Lagertyp wirklich
nutzt). Daraus lässt sich nativ **STEP/IGES** exportieren.

> **Stand v0.30:** Kern, Bauplan, `Part`-Backend und die komplette Workbench-GUI sind
> umgesetzt und host-frei getestet. Einzig der manuelle Gegencheck in echtem FreeCAD ist
> naturgemäß nur am Host prüfbar — Details in der [Roadmap](ROADMAP.md).

---

## Troubleshooting 🔧

<details>
<summary><b>„Wälzkörper schneidet in den Ring" / Lager sieht falsch aus</b></summary>

<br>

**Auto-Fit** aktiviert lassen — es begrenzt `Wälzkörper-Ø` und `Anzahl` auf plausible Werte
und löst die Geometrie vor dem Bau auf. Die Ergebnis-Sektion zeigt, ob Werte angepasst
wurden.
</details>

<details>
<summary><b>Käfig fehlt im Ergebnis</b></summary>

<br>

Bei sehr grober Auflösung oder zu wenig Bauraum kann der Boolean-Schnitt fehlschlagen →
Fallback auf den **Leiter-Käfig**, oder der Käfig wird mit Warnung übersprungen.
`Auflösung Segmente` erhöhen oder etwas mehr Breite/Pocket-Spiel geben.
</details>

<details>
<summary><b>FreeCAD: Workbench erscheint nicht im Dropdown</b></summary>

<br>

`InitGui.py` und `package.xml` müssen im **Wurzelverzeichnis** des Mod-Ordners liegen.
Veraltete `*.backup`-Ordner im Mod-Verzeichnis ausschließen und FreeCAD neu starten.
</details>

---

## Entwicklung 🧪

```bash
# Syntaxcheck (beide Frontends)
python -m compileall uni_rolling_bearing/ freecad_backend/ InitGui.py

# Unit-Tests — laufen ohne Blender/FreeCAD
python -m unittest discover tests
```

**Einschränkungen:** keine FEM-/Kontaktmechanik · keine vollständige DIN/ISO-Abdeckung
aller Reihen · Tragzahlen/Lebensdauer sind vereinfachte Näherungen, keine zertifizierten
Auslegungswerte.

---

## Lizenz 📄

GNU General Public License v3.0 — siehe [`LICENSE`](LICENSE).

<div align="center">
<br>
<sub><b>UNI Rolling Bearing Generator</b> · ein Kern, zwei Hosts · Blender 🟧 + FreeCAD 🟦<br>
Made for Maschinenbau — <i>d · D · B → ready-to-use bearing</i></sub>
</div>
