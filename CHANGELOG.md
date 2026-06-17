# Changelog

Alle nennenswerten Änderungen am **UNI Rolling Bearing Generator**.

Das Format orientiert sich an [Keep a Changelog](https://keepachangelog.com/de/1.1.0/),
die Versionierung an [Semantic Versioning](https://semver.org/lang/de/).
Für ältere Releases (vor Einführung dieses Changelogs) sind keine
Veröffentlichungsdaten erfasst; sie sind chronologisch absteigend gelistet.

Geplante, noch offene Arbeiten stehen in [`ROADMAP.md`](ROADMAP.md).

## [0.28.0] – 2026-06-17

Wie zuvor bei Kugeln und Kegelrollen saßen auch Zylinder-, Nadel- und
Tonnenrollen zu klein und schwebten im Laufbahnspalt – damit sitzen jetzt
**alle** Wälzkörpertypen satt und katalognah in ihren Laufbahnen.

### Changed
- **Zylinderrollen:** Ringwand `1/7 → 1/8` und Füllgrad `0.78 → 0.94`. Die Rolle
  füllt den Laufbahnspalt nun satt (NU206 → ø≈7.5 mm / 13 Rollen statt ~5.3 mm /
  24), statt mit großem Spiel zwischen den Schultern zu schweben (~33 % → ~47 %
  des Radialbands).
- **Nadeln:** Füllgrad `0.88 → 0.94` (satter Sitz).
- **Tonnenrollen:** Füllgrad `0.86 → 0.90` (etwas größer, satterer Sitz in der Mulde).

### Added
- `constants.TYPE_SUGGEST_PITCH_GAP`: typgerechter Umfangsspalt für die
  *vorgeschlagene* Wälzkörperzahl (berücksichtigt Käfigstege) → katalognahe
  Default-Bestückung statt dichtest gepacktem Umfang. Vereinheitlicht und ersetzt
  den ball-spezifischen `BALL_SUGGEST_PITCH_GAP` für alle Typen.
- Tests `TestRollerSnugFit`: Rolle füllt ≥ 82 % des Radialspalts, ohne über die
  Schultern zu ragen; Zylinderrolle ≥ 40 % des Radialbands und Stückzahl
  katalognah (Regression gegen „zu klein"/Überfüllung). Gesamt 173 Tests.

## [0.27.0] – 2026-06-17

### Fixed
- **Kegelrollen waren zu klein** und schwebten zwischen den Laufbahnen: der
  Rollen-Ø füllte nur den *radialen* Spalt, obwohl die Rolle geneigt sitzt. Neue
  `geometry.tapered_roller_diameter` legt den mittleren Rollen-Ø über
  `d_we = radial_space · cos α − Lagerluft` aus, sodass die geneigte Rolle
  senkrecht zu ihrer Achse an der (steileren) Cup-Laufbahn anliegt, ohne sie zu
  durchschneiden.

### Changed
- `TYPE_RING_THICKNESS_RATIO[TAPERED]` `1/9 → 1/10`: die Kegelrolle füllt nun
  ~57 % statt ~53 % des Radialbands, bei katalognaher Rollenzahl
  (30206 → 14, 30306 → 12).
- `contact_angle_deg` löst jetzt Live-Auto-Berechnen aus; der Kontaktwinkel wird
  in Resolver (`resolve_geometry`) und Vorschlag (`suggest_defaults`)
  durchgereicht, sodass der Rollen-Ø mit α skaliert.

### Added
- Tests für die Kegelrollen-Formel, das Anliegen an der Cup-Laufbahn (ohne
  Clipping), Bandfüllung ≥ 55 % und Rollenzahl im Katalogbereich.

## [0.26.0] – 2026-06-17

### Fixed
- **Kugeln waren zu klein** und schwebten zwischen den Schultern (flache Rillen).
  Neue `geometry.ball_diameter_from_groove` setzt die DIN-625-Rillenformel um:
  `d_w = Schulterspalt + Rillentiefe_innen + Rillentiefe_außen − Lagerluft`. Die
  Kugel ist damit *größer* als der Schulterspalt und taucht über beide Schultern
  hinaus in die Rillen ein; nach oben begrenzt nur die Restwand zwischen
  Rillenboden und Bohrung/Außenmantel (`max_ball_diameter_for_walls`).
- **Maintainer** (`bl_info` author) von „Codex" auf „Chance-Konstruktion"
  korrigiert.

### Changed
- `TYPE_RING_THICKNESS_RATIO[BALL,VGROOVE]` `1/12 → 2/15`: realistische
  Schulterlage, sodass Kugel-Ø und -zahl katalognah ausfallen (6204 → ø7.82 mm /
  8 Kugeln, 6304 → 9.28 / 7, 6306 → 12.2 / 8). Als Nebeneffekt fallen die
  Tragzahlen C0r/Cr von ~1.3–1.6× auf ~1.0× des Katalogs.
- Vorgeschlagene Kugelzahl über katalognahen Umfangsfüllgrad (≈ 60 %).

### Added
- Test-Suite `tests/test_bearing_quality.py`: Rillenformel, katalognahe
  Kugel-Ø/-Zahl, Kugel *nestelt* in der Laufbahn-Rille (Rille schneidet sichtbar
  unter die Schulter, Bodenspiel vorhanden) und – für **alle** Lagertypen über
  **alle** Presets – revolvier-fähige (manifold-taugliche) Querschnittsprofile.

## [0.25.0] – Sichtbare Kugelrille, korrekte Kegelrollen-Geometrie, Tonnenlager-Reihen, Solo-Panel

- **Kugellager – Rille sichtbar, Kugeln größer:** Die v0.23-Rillenformel
  `max_kugel = radial_space/(2·f)` machte die Kugel so klein, dass sie mittig
  schwebte und der Rillenbogen die Schulter nicht erreichte (z_arc = 0 → keine
  Rille im Mesh). Die Kugel füllt jetzt – wie eine Rolle – den nutzbaren Spalt
  (`usable · ROLLER_SAFETY_FRACTION`) und reicht bis an beide Schultern, sodass
  der Rillenbogen sichtbar einschneidet. 6204-Default ≈ 8.5 mm (statt 6.95 mm);
  weiter innerhalb 10 % der realen Kugel. `_ball_max_roller_d` und der
  `groove_conformity`-Sizing-Parameter entfielen (Sizing für alle Typen
  einheitlich; die Konformität steuert weiterhin nur die Rillen-Profilform).
- **Kegelrollenlager – gemeinsamer Apex:** Neue Geometriefunktion
  `geometry.tapered_cone_half_angle` leitet den halben Rollen-Kegelwinkel β
  aus den Laufbahnradien ab, sodass Cup-(α), Kegel-(α − 2β) Laufbahn und Rolle
  (gekippt um α − β) einen gemeinsamen Apex haben. Vorher kippten beide
  Laufbahnen um α (konstanter Spalt) und ein fehlerhafter Clamp schrumpfte die
  Rollen zu winzigen Spitzkegeln. Rollenlänge auf 0.78·B reduziert und Füllgrad
  auf 0.94 erhöht – die Rolle bleibt nach dem Kippen innerhalb beider Laufbahnen
  und der Lagerbreite. Katalog-Rollenzahlen (30206 → 15, 30306 → 13) bleiben im
  geprüften Band.
- **Tonnenlager ein-/zweireihig:** Neue Property `spherical_rows` (1/2,
  Default 1). Einreihig (DIN 635-1): eine Tonne mittig, eine zentrale konkave
  Innenlaufbahn. Zweireihig (DIN 635-2): bisherige zwei Reihen, aber mit
  längeren (tonnenförmigen statt stummeligen) Rollen. `raceway.spherical_inner_ring_profile`
  bekam einen `rows`-Schalter; `ratings` rechnet die Reihenzahl korrekt
  (`rows`-Parameter statt fest i = 2).
- **Solo-Panel:** Optionale Sektionen (Normen, Mesh-Qualität, Tragzahlen,
  Passungen) starten eingeklappt (`DEFAULT_CLOSED`); pro Lagertyp werden nur
  die tatsächlich relevanten Wälzkörper-Optionen gezeigt (Kontaktwinkel nur bei
  Kegelrollen bzw. zweireihigem Pendellager, Rillen-Konformität nur bei
  Kugellagern, V-Rille nur bei SG). Typspezifische Felder sind in eigene Boxen
  gruppiert.
- Neue Tests für `tapered_cone_half_angle` (gemeinsamer Apex) und das einreihige
  Pendel-Innenprofil. Gesamt 154 Tests.

## [0.24.0] – Katalognahe Rollenzahlen, U-Profil-Rille, Referenz-Testsuite

- **Rollen-Sizing (Kegel-/Pendelrollenlager):**
  `TYPE_RING_THICKNESS_RATIO[TAPERED,SPHERICAL]` von 1/6 auf 1/9 reduziert
  und `TYPE_ROLLER_FILL[TAPERED,SPHERICAL]` auf 0.86 angehoben. Die Rollen
  werden dadurch größer und die Anzahl fällt in den realen Katalogbereich
  (30206 → 17 statt ~40, 30306 → 14, 22310 → 15/Reihe).
- **U-Profil-Variante (SG-Reihe):** neue Property `vgroove_shape` (`V`/`U`).
  `raceway.vgroove_outer_ring_profile` erzeugt bei `"U"` eine halbrunde
  Außenrille (Kosinus-Bogen gleicher Tiefe und Breite) statt der geraden
  V-Flanken – passend für Rundriemen/-seile.
- **Referenz-Testsuite `tests/test_reference_cases.py`:** prüft (1) Preset-Maße
  gegen veröffentlichte ISO 15-Werte, (2) abgeleitete Rollenzahlen gegen
  Katalog-Bänder, (3) C0r/Cr gegen Katalog-Richtwerte innerhalb dokumentierter
  Faktoren. Gesamt 149 Tests.
- SG-Zwischengrößen (SG30/40/55) bleiben bewusst offen, bis belastbare
  Maßquellen vorliegen.

## [0.23.2] – Toter Code entfernt

- `din623.py` auf die tatsächlich genutzte `bore_code_to_diameter`-Logik
  reduziert (189 → 32 Zeilen): die hartkodierten Maßreihen-Tabellen samt
  Buildern waren seit v0.16 durch die JSON-Norm-Engine ersetzt.
- Ungenutzte Konstanten entfernt: `constants.TYPE_GAP_FACTOR` und
  `raceway.SPHERICAL_OUTER_RACE_FACTOR`.
- Ungenutzte Test-Imports in `tests/test_norm_engine.py` entfernt.
- Verifiziert mit pyflakes/vulture; verbliebene Treffer sind ausschließlich
  Blender-Framework-Hooks (`bl_idname`/`draw`/`execute`/`register`).

## [0.23.1] – Projekt-Qualität: CI, reproduzierbare Distribution, aktuelle In-App-Hilfe

- GitHub-Actions-Workflow `.github/workflows/tests.yml`: führt bei jedem Push und
  Pull-Request `compileall` und die komplette `unittest`-Suite auf Python
  3.10/3.11/3.12 aus und verifiziert über `build_addon_zip.py --check`, dass
  `dist/uni_rolling_bearing.zip` Datei-für-Datei mit dem Quellbaum übereinstimmt.
- `build_addon_zip.py` um einen `--check`-Modus erweitert (nur Vergleich).
- In-App-Hilfetexte aktualisiert (Tragzahlen, X-/Y-Faktoren, Passungen,
  JSON-Norm-Engine, vier Käfig-Bauarten, typabhängige Ringwand).
- `.gitignore` macht die ausgelieferte ZIP explizit (`dist/*` +
  `!dist/uni_rolling_bearing.zip`).
- README mit CI-Status-Badge.

## [0.23.0] – Rillen-Geometrie und realistische Kugelgrößen

- `geometry.resolve_geometry` / `suggest_defaults` rechnen für Rillenkugellager
  (BALL/VGROOVE) mit der Rillen-Formel `max_kugel = radial_space / (2·f)`. Die
  Konformität `f` kommt aus `groove_conformity_inner/_outer`; ohne Wert gilt
  `DEFAULT_BALL_GROOVE_CONFORMITY = 0.52`.
- `TYPE_RING_THICKNESS_RATIO[BALL,VGROOVE]` von 1/6 auf 1/12 reduziert;
  `ring_thickness` als Mindestwand zwischen Bohrung und Rillenboden interpretiert.
- Default-Vorschläge treffen reale ISO 15-Reihen (6204 → ø7.94 mm vs. vorher
  ø4.27 mm). Operatoren reichen die Konformität durch (`_groove_conformity_for`).

## [0.22.0] – Sub-Panel-UX und Pendelrollen-Fixes

- N-Panel auf einklappbare Sub-Panels (`bl_parent_id`) umgestellt; neue
  `Ergebnisse`-Box bündelt berechnete Werte (Check, Tragzahlen, Passungen).
- `auto_recompute` (Live-Auto-Berechnen) standardmäßig aktiv.
- **Fix:** `ROLLER_LENGTH_RATIO[SPHERICAL]` `0.85 → 0.38` – die Tonnenrolle ist
  *ein* Wälzkörper einer zweireihigen Anordnung; die alte Ratio ließ die Rollen
  über die Lagerstirnflächen hinausragen.
- `raceway.spherical_inner_row_z` neu formuliert: Reihen überlappen am Mittelband
  nicht und bleiben innerhalb der Lagerbreite; Profil- und Wälzkörper-Position
  sind synchron.
- Zwei neue Asserts für die 22210-Geometrie.

## [0.21.0] – Massivkäfig mit Schmiertaschen

- Neue Käfig-Bauart `MASSIVE`: Pocket-Sleeve plus radiale Schmiertaschen-
  Bohrungen im tangentialen Steg zwischen zwei Pockets (gefräster Messing-Stil).
- Neue Property `oil_pocket_diameter_mm` (0 = automatisch ≈ 50 % des kleineren
  Bauraums); Clamping auf verfügbaren Bauraum, unter `MIN_OIL_POCKET_DIAMETER_MM`
  (0.3 mm) entfällt die Tasche.
- Fallback auf reinen Pocket-Sleeve bzw. die Leiter-Kette bei zu wenig Bauraum.
- Reine Geometriefunktion `geometry.oil_pocket_diameter` (testbar ohne Blender).
- Metadaten `oil_pocket_diameter_mm`, `oil_pocket_count`.

## [0.20.0] – X-/Y-Faktoren für äquivalente Last

- Eingaben `radial_load_fr_n` (Fr) und `axial_load_fa_n` (Fa) statt einer
  einzigen P-Property. `P = X·Fr + Y·Fa` nach ISO 281 Tabelle 4 lagertypabhängig:
  - **Rillenkugellager (BALL/VGROOVE):** e, Y aus Fa/C0r interpoliert; X = 1 für
    Fa/Fr ≤ e, sonst 0.56.
  - **Kegelrollenlager (TAPERED):** e = 1.5·tan(α), Y = 0.4/tan(α); X = 1 bzw. 0.4.
  - **Pendelrollenlager (SPHERICAL):** e = 1.5·tan(α); X/Y1 bzw. X/Y2.
  - **Zylinderrollen-/Nadellager:** rein radial, Fa wird ignoriert (Panel-Warnung).
- Neue Helfer `ratings.equivalent_load`, `ratings.LoadFactors`; `Ratings` enthält
  X, Y, e, P_N. Metadaten am Bearing-Empty (nur wenn eine Last > 0).
- Neue Tests für alle Lagertypen, Tabellen-Stützstellen, Clamping.

## [0.19.0] – f0/fc als γ-abhängige ISO-Tabellen

- `ratings.py` ersetzt die Mittelwert-Konstanten `f0`/`fc` durch interpolierte
  Werte aus den ISO 76- bzw. ISO 281-Annex-Tabellen (Kugel-/Rollenlager getrennt,
  Randwert-Clamping).
- Neue Helfer `ratings.gamma`, `ratings.f0_for`, `ratings.fc_for`;
  `compute_ratings` & Co. bekommen `pitch_d_mm` als Pflichtparameter
  (γ = Dw·cos(α)/dm).
- `Ratings` liefert `gamma`, `f0`, `fc`; Live-Vorschau + Metadaten
  (`rating_gamma`, `rating_f0`, `rating_fc`).
- Zusätzliche Tests für Tabellenwerte, Interpolation, Clamping, γ.

## [0.18.0] – UI-Workflow „Reihe → Bohrungskennzahl"

- Für DIN-623-Lagertypen (BALL, CYLINDRICAL, TAPERED, SPHERICAL) zwei
  aufeinander aufbauende Dropdowns (`Massreihe` → `Bohrungskennzahl`) mit
  abgeleitetem Bohrungs-Ø im Label und kombinierter Bezeichnung als Live-Vorschau.
- Neuer Operator `uni_bearing.apply_bore_code_preset` (setzt d/D/B, übernimmt
  Cone-/Cup-Breiten; hält `series_code` synchron).
- `direct`-Coding-Typen (NEEDLE, VGROOVE) behalten die freie Code-Auswahl; UI
  schaltet je Lagertyp automatisch um.
- Neue Helfer `norm_engine.coding_for`, `load_series_for`, `load_bore_codes_for`;
  abgedeckt durch `tests/test_norm_engine.py`.

## [0.17.1] – Bugfix: Wälzkörper-Position und EnumProperty-Memory

- **Position-Bug:** Bei Zylinder-, Nadel-, Kegel- und Pendelrollenlagern wurden
  die Wälzkörper-Vertices im Mesh-Frame translatiert und zusätzlich per
  `rotation_euler[2]` um die Welt-Z gedreht – die Rollen landeten bei `2a` statt
  `a` und überlappten paarweise. Fix in `add_uv_sphere`, `add_cylinder`,
  `add_tapered_roller`, `add_barrel_roller`: Vertices bleiben mesh-zentriert, die
  Position kommt über `obj.location`.
- **EnumProperty-Memory:** `_series_items` erzeugte bei jedem Aufruf frische
  Strings (bekannter Blender-Pitfall → Crash/Korruption); Items werden nun pro
  Lagertyp gecacht.

## [0.17.0] – Kegelrollen-Reihen 313/320/322/323 + Cone/Cup-Breiten

- Vier zusätzliche DIN 720-Reihen (313, 320, 322, 323) in `data/tapered.json`;
  insgesamt 46 Kegelrollen-Größen.
- JSON-Eintragsformat erweitert: `[D, T]` oder `[D, T, B, C]` mit getrennter
  Cone- (`B`) und Cup-Breite (`C`).
- `norm_engine.load_ring_widths_for` + `apply_series_preset` übertragen die
  Breiten in `tapered_cone_width_mm` / `tapered_cup_width_mm`; Profile nutzen die
  separaten Breiten. Werte als Metadaten hinterlegt.

## [0.16.0] – Norm-Engine als JSON-Datenquelle

- Neues Modul `norm_engine.py` lädt die Maßreihen aus JSON-Dateien unter
  `uni_rolling_bearing/data/` (Codings `din623` und `direct`).
- `constants.SERIES_PRESETS` / `NORM_HINTS` werden beim Import aus JSON gebaut –
  keine Hardcoded-Tabellen mehr.
- Benutzer können eigene Presets als gleichnamige JSON unter
  `<Blender-Scripts>/uni_bearing/` ablegen (Merge über die Defaults).

## [0.15.0] – Käfig-Bauart Ribbon

- Neue Käfig-Bauart `RIBBON`: zwei genietete Halbringe (Pressblech-Stil),
  Halb-Pockets per Boolean, Niete in den Lücken.
- Neue Property `cage_style` (`AUTO`/`POCKET`/`RIBBON`/`LADDER`); `AUTO` behält
  das bisherige Verhalten, Fallback auf Leiter-Käfig.
- Metadatum `cage_style` (`pocket`/`ribbon`/`ladder`).

## [0.14.0] – Welle-/Gehäuse-Passungen DIN 5418

- Neues Modul `fits.py` mit DIN-5418-Empfehlung der ISO-286-Toleranzklasse für
  Welle und Gehäusebohrung; Stufung nach Belastungsfall und Durchmesser.
- Abmaße für g6/h6/j6/k5/k6/m5/m6/n6/p6 sowie G7/H6/H7/J7/K7/M7/N7/P7 in
  10 Bereichen 1..250 mm tabelliert.
- UI-Sektion „Passungen (DIN 5418)"; Metadaten `load_case`, `shaft_fit_class`,
  `housing_fit_class` (+ Abmaße in µm, soweit tabelliert).

## [0.13.0] – Tragzahlen ISO 76 / ISO 281

- Neues Modul `ratings.py`: `static_load_rating` (C0r, ISO 76),
  `dynamic_load_rating` (Cr, ISO 281), `nominal_life_hours` (L10h).
- UI-Sektion „Tragzahlen & Lebensdauer" mit Live-Vorschau; Metadaten
  `static_load_rating_N`, `dynamic_load_rating_N`, `L10h_hours`.
- Lebensdauer-Exponent p = 3 (Kugel/SG), 10/3 (Rollen); Pendelrollenlager mit
  i = 2 Reihen, α = 10°.

## [0.12.0] – DIN 623 / ISO 15 Maßreihen

- Neues Modul `din623.py` mit Bohrungskennzahl-Logik (`bore_code_to_diameter`)
  und ISO-15-Maßtabellen (60/62/63/64/618/619, NU2/NU3, 302/303, 222/223).
- `SERIES_PRESETS` für BALL/CYLINDRICAL/TAPERED/SPHERICAL aus den Tabellen
  generiert (~80 Rillenkugellager-Größen statt 3); Nadel-Presets HK0808–HK3020.
- Tests `tests/test_din623.py`.

## [0.10.1] – Kantenfasen am Kugellager

- Neue Property `bearing_chamfer_mm` (Default 0.3 mm): 45°-Fase nach
  DIN 620 / ISO 582 an Bohrung und Außenmantel (bei VGROOVE links/rechts der
  V-Rille), direkt ins Querschnittsprofil eingebaut (kein Bevel-Modifier, Ring
  bleibt manifold). Auto-Clamp auf 45 % des Bauraums; `0` = scharfe Kante.
- Metadatum `bearing_chamfer_mm`.
- `build_addon_zip.py` wiederhergestellt.

## [0.10.0] – Käfig-Ausbau & Kegelrollen-Bord

- Käfig-Werkstoff (`Stahlblech`/`Messing`/`Polymer`) als UI-Auswahl (Metadatum
  `cage_material`).
- Pocket-Spiel als UI-Parameter `pocket_clearance_mm` (Default 0.20 mm).
- Kegelrollenlager: optionaler Bord am Innenring (`tapered_flange_height_mm`,
  Default 1.0 mm), Höhe auf den Bauraum bis zur Außenlaufbahn begrenzt.

## [0.9.1] – Konformitätsfaktor als UI-Parameter

- Neue Properties `groove_conformity_inner` (0.58) und `groove_conformity_outer`
  (0.60) für BALL/VGROOVE, durchgereicht an die Rillen-Profile und als Metadaten
  hinterlegt. UI nur bei BALL/VGROOVE; Bereich 0.51–0.70.

## [0.9.0] – Detailliertes Fehlerfeedback

- Geometrie-Resolver liefert konkrete Korrekturvorschläge mit Zahlen (max.
  Ringstärke, max. Lagerluft, max. Wälzkörper-Ø/-anzahl).
- Operator-Reports geben konkrete nächste Schritte an.

## [0.8.0] – U-Rillen-Kugellager / SG-Reihe

- Neuer Lagertyp `VGROOVE` (Führungsrollen-Kugellager) mit Presets SG10/15/20/
  25/35/66.
- Neue `raceway.vgroove_outer_ring_profile`: Kugelrille innen + V-Rille im
  Außenmantel (Default 90° V, Tiefe ≈ 35 % der Außenwand), Fallback auf
  Standard-Profil bei zu wenig Bauraum.
- UI-Parameter `vgroove_depth_mm`, `vgroove_half_angle_deg` (Metadaten).

## [0.7.0] – Pocket-Käfig

- Standard-Käfig als einteiliger Sleeve mit typabhängigen Pockets (Boolean-
  Difference aus oversized Wälzkörper-Stempeln); Form folgt dem Lagertyp.
- Fallback auf Leiter-Käfig; Metadatum `cage_style` (`pocket`/`ladder`).
- Neuer Helfer `mesh_builders.apply_boolean_difference`.

## [0.6.0] – Echte Laufbahnen

- Neues Modul `raceway.py` mit typspezifischen Querschnittsprofilen, per
  Z-Achsen-Revolution zu manifold Ringen vermesht.
- Kugellager: Konformitätsbogen (groove) innen/außen, Fallback auf Hohlzylinder.
- Zylinder-/Nadellager: Außenring mit zwei Borden (NU-Bauart).
- Kegelrollenlager: konische Laufbahnen passend zum Kontaktwinkel.
- Tonnenlager: sphärische Innenlaufbahn am Außenring.
- Mesh-Builder `make_revolved_ring`; Kugel-Füllgrad auf 0.95 angehoben.

## [0.5.0] – Kegelrollen-Kontaktwinkel

- Property `contact_angle_deg` (Default 14°, nur TAPERED). Wälzkörper im
  Mesh-Frame um die lokale Y-Achse gekippt, gemeinsamer Apex auf der Lagerachse;
  `tapered_apex_z_mm` als Metadatum.

## [0.4.0] – Käfig

- Optionaler parametrischer Leiter-Käfig (zwei Endplatten + tangentiale Webs),
  gegen die Laufbahnen geclippt. UI-Toggle `Käfig erzeugen`; bei zu wenig Platz
  Überspringen mit Warnung.

## Grundlagen (vor der Versionierung)

- **Basis-Addon & UI:** Addon-Struktur mit `bl_info`, Registrierung, N-Panel;
  Lagertyp-Dropdown; Erstellen-Button. Typen: Kugel-, Zylinderrollen-, Nadel-,
  Kegelrollen- und Tonnenlager.
- **Normorientierung:** Start-Presets, Toleranzklasse (ISO 492), radiale
  Lagerluft, Normhinweise als Metadaten.
- **Funktionsfähigkeit:** Geometrie-Resolver (Laufbahnspalt/Wälzkörperraum),
  Auto-Fit (Ø- und Anzahl-Begrenzung), funktionale Baugruppe mit getrennten
  Komponenten unter gemeinsamem Empty-Parent.
- **Mesh-Qualität:** manifold-orientierte BMesh-Erzeugung je Ring/Wälzkörper,
  Non-manifold-Kantenprüfung pro Komponente.
