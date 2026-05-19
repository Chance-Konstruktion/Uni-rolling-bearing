# ROADMAP – UNI Rolling Bearing Generator

## Erledigt ✅

### Grundlagen (pre-Versioning)

#### Basis-Addon & UI
- Addon-Struktur mit `bl_info`, Registrierung und N-Panel erstellt.
- Lagertyp-Dropdown als Einstieg umgesetzt.
- Unterstützte Typen: Kugel-, Zylinderrollen-, Nadel-, Kegelrollen- und Tonnenlager.
- Erstellen-Button am Panel-Ende integriert.

#### Normorientierung
- Start-Presets für mehrere Lagerreihen eingebaut.
- Toleranzklasse (ISO 492-Orientierung) und radiale Lagerluft als Parameter aufgenommen.
- Normhinweise als Objekt-Metadaten hinterlegt.

#### Funktionsfähigkeit (Fix)
- Geometrie-Resolver ergänzt, der Laufbahnspalt und nutzbaren Wälzkörperraum prüft.
- Auto-Fit ergänzt:
  - begrenzt Wälzkörperdurchmesser auf geometrisch zulässigen Wert,
  - begrenzt Anzahl nach Umfangsabstand.
- Ergebnis als funktionale Baugruppe geändert:
  - Komponenten bleiben getrennt,
  - gemeinsame Assembly über Empty-Parent.

#### Mesh-Qualität
- Manifold-orientierte Erzeugung je Ring/Wälzkörper via BMesh.
- Non-manifold-Kantenprüfung pro erzeugter Komponente.

---

### v0.4.0 – Käfig
- Optionaler parametrischer Käfig im Stil „Leitercage": zwei axiale Endplatten
  zwischen Lagerrand und Wälzkörperende, dazwischen tangentiale Webs in den
  Lücken zwischen den Wälzkörpern.
- Endplatten werden gegen die Laufbahnen geclippt (Sicherheitsabstand), Webs
  nutzen den verbleibenden Tangentialspalt.
- UI-Toggle ``Käfig erzeugen``; bei zu wenig Platz wird der Käfig
  übersprungen und eine Warnung gemeldet.

### v0.5.0 – Kegelrollen-Kontaktwinkel
- Eigenschaft ``contact_angle_deg`` (Default 14°), nur für TAPERED sichtbar.
- Wälzkörper werden im Mesh-Frame um die lokale Y-Achse gekippt; alle Achsen
  treffen sich auf der Lagerachse in einem gemeinsamen Apex.
- Apex-Z wird als ``tapered_apex_z_mm`` am Assembly hinterlegt.

### v0.6.0 – Echte Laufbahnen
- Neues Modul ``raceway.py`` mit typspezifischen Querschnittsprofilen, das
  per Z-Achsen-Revolution zu manifold Ringen vermesht wird.
- Kugellager: Konformitätsbogen (groove) in Innen- und Außenring; bei zu
  kleinem Wälzkörper-Ø Fallback auf Hohlzylinder.
- Zylinder-/Nadellager: Außenring mit zwei Borden (NU-Bauart), automatischer
  Verzicht bei zu engem Bauraum.
- Kegelrollenlager: konische Laufbahnen passend zum Kontaktwinkel.
- Tonnenlager: sphärische Innenlaufbahn am Außenring.
- Mesh-Builder ``make_revolved_ring`` für beliebige geschlossene Profile.
- Default-Wälzkörper-Füllgrad für Kugellager auf 0.95 angehoben (real-näher,
  Voraussetzung für sichtbare Rille bei Auto-Berechnung).

### v0.7.0 – Pocket-Käfig
- Standard-Käfig ist jetzt ein einteiliger Sleeve mit typabhängigen Pockets,
  erzeugt per Boolean-Difference aus oversized Wälzkörper-Stempeln.
- Pocket-Form folgt dem Lagertyp: sphärisch (Kugel), zylindrisch (Zylinder/
  Nadel), kegelig (Kegelrolle), tonnenförmig (Tonnenlager).
- Fallback auf den bisherigen Leiter-Käfig, wenn der Boolean nicht
  durchgreift; ``cage_style`` (``"pocket"``/``"ladder"``) wird als Meta-
  daten am Assembly hinterlegt.
- Neue Helfer ``mesh_builders.apply_boolean_difference`` als zentrale
  Schnittstelle für Boolean-basierte Mesh-Operationen.

### v0.8.0 – U-Rillen-Kugellager / SG-Reihe
- Neuer Lagertyp ``VGROOVE`` (Führungsrollen-Kugellager).
- Norm-Presets ``SG10``, ``SG15``, ``SG20``, ``SG25``, ``SG35``, ``SG66``
  mit handelsüblichen Hauptmaßen (Bishop-Wisecarver / Misumi „SG/W"-Reihe).
- Neue Außenring-Profilfunktion ``raceway.vgroove_outer_ring_profile``:
  Standard-Kugelrille innen, V-Rille im Außenmantel (Default 90° V, Tiefe
  ≈35 % der Außenwand). Fällt automatisch auf das Standard-Profil zurück,
  wenn der Bauraum für die Rille nicht reicht.
- UI-Parameter ``vgroove_depth_mm`` (0 = automatisch) und
  ``vgroove_half_angle_deg`` exklusiv für den SG-Typ; Werte werden als
  Metadaten am Bearing-Empty hinterlegt.
- Wälzkörper, Käfig-Pockets und Innenring-Profil identisch zum Standard-
  Rillenkugellager – die Reihe ist mechanisch ein Rillenkugellager mit
  zusätzlicher Außenrille.

### v0.9.0 – Detailliertes Fehlerfeedback
- Geometrie-Resolver liefert nun konkrete Korrekturvorschläge mit Zahlen
  (max. zulässige Ringstärke, max. Lagerluft, max. Wälzkörper-Ø/-anzahl)
  statt rein generischer Meldungen.
- Operator-Reports (Auto-Berechnen, Preset-Übernahme, Erstellen) geben
  Hinweise auf konkrete nächste Schritte (z. B. „Auto-Fit aktivieren",
  „Reihen-Code wechseln").

### v0.9.1 – Konformitätsfaktor als UI-Parameter
- Neue Properties ``groove_conformity_inner`` (Default 0.58) und
  ``groove_conformity_outer`` (Default 0.60) für Rillenkugellager und
  SG-Reihe (VGROOVE).
- Werden an ``raceway.ball_inner_ring_profile``,
  ``raceway.ball_outer_ring_profile`` und
  ``raceway.vgroove_outer_ring_profile`` durchgereicht und als Metadaten
  ``groove_conformity_inner/_outer`` am Bearing-Empty hinterlegt.
- UI: Im Wälzkörper-Abschnitt nur sichtbar bei BALL/VGROOVE. Bereich
  0.51–0.70 deckt reale Lager (0.515–0.535) und visualisierungsfreundliche
  Werte ab.

### v0.10.0 – Käfig-Ausbau & Kegelrollen-Bord
- Käfig-Werkstoff (``Stahlblech``/``Messing``/``Polymer``) als UI-Auswahl,
  wird als Metadatum ``cage_material`` am Bearing-Empty hinterlegt.
- Pocket-Spiel als UI-Parameter ``pocket_clearance_mm`` (Default 0.20 mm,
  Bereich 0–1 mm) – ersetzt die bisherige Konstante in den Boolean-Cuttern.
- Kegelrollenlager: optionaler Bord am Innenring (große Stirnseite,
  ``tapered_flange_height_mm``, Default 1.0 mm). Höhe wird auf den verbleibenden
  Bauraum bis zur Außenlaufbahn (abzgl. Lagerluft) begrenzt.

### v0.10.1 – Kantenfasen am Kugellager
- Neue Property ``bearing_chamfer_mm`` (Default 0.3 mm) für Standard- und
  SG-Kugellager: 45°-Fase nach DIN 620 / ISO 582 an Bohrung (Innenring) und
  Außenmantel (Außenring), bei VGROOVE links/rechts der V-Rille.
- Fase wird in ``raceway.ball_inner_ring_profile``,
  ``raceway.ball_outer_ring_profile`` und
  ``raceway.vgroove_outer_ring_profile`` direkt ins Querschnittsprofil
  eingebaut – kein nachträglicher Bevel-Modifier nötig, der Ring bleibt
  manifold.
- Bei zu wenig Bauraum (sehr dünne Wand, sehr schmales Lager, V-Rille frisst
  den Flachstirn auf) wird die Fase automatisch auf 45 % des verfügbaren
  Bauraums geclampt; ``0`` lässt die Kante scharf.
- Wert wird als Metadatum ``bearing_chamfer_mm`` am Bearing-Empty hinterlegt.
- Build-Skript ``build_addon_zip.py`` wiederhergestellt (war versehentlich
  gelöscht, README verwies aber weiter darauf).

### v0.12.0 – DIN 623 / ISO 15 Maßreihen
- Neues Modul ``din623.py`` mit DIN 623-Bohrungskennzahl-Logik
  (``bore_code_to_diameter``) sowie ISO 15-Maßtabellen für Rillenkugellager
  (Reihen 60/62/63/64/618/619), Zylinderrollenlager NU2/NU3, Kegelrollen
  302/303 und Pendelrollen 222/223.
- ``SERIES_PRESETS`` für BALL/CYLINDRICAL/TAPERED/SPHERICAL werden komplett
  aus den Tabellen generiert (~80 Rillenkugellager-Größen statt bisher 3).
- Nadellager-Presets manuell erweitert (HK0808–HK3020).
- Tests in ``tests/test_din623.py`` decken Bohrungskennzahl-Mapping und
  Konsistenz der generierten Presets ab.

### v0.13.0 – Tragzahlen ISO 76 / ISO 281
- Neues Modul ``ratings.py`` mit vereinfachten Berechnungen:
  ``static_load_rating`` (C0r nach ISO 76), ``dynamic_load_rating``
  (Cr nach ISO 281) und ``nominal_life_hours`` (L10h).
- UI-Sektion „Tragzahlen & Lebensdauer" mit Eingaben für äquivalente Last
  ``P`` und Drehzahl ``n``; zeigt C0r, Cr und – wenn P und n > 0 – L10h
  als Live-Vorschau.
- Werte werden als Metadaten ``static_load_rating_N``,
  ``dynamic_load_rating_N`` und ``L10h_hours`` am Bearing-Empty hinterlegt.
- Lebensdauer-Exponent p = 3 für Kugel-/SG-Lager, 10/3 für Rollenlager;
  Pendelrollenlager werden mit i = 2 Reihen und α = 10° gerechnet.

### v0.14.0 – Welle-/Gehäuse-Passungen DIN 5418
- Neues Modul ``fits.py`` mit DIN 5418-orientierter Empfehlung für die
  ISO 286-Toleranzklasse von Welle und Gehäusebohrung; Stufung nach
  Belastungsfall (Innenring rotiert leicht/normal/schwer, Außenring
  rotiert, stillstehend) und Bohrungs-/Außendurchmesser.
- Abmaße für die empfohlenen Klassen (g6/h6/j6/k5/k6/m5/m6/n6/p6 sowie
  G7/H6/H7/J7/K7/M7/N7/P7) in 10 ISO 286-Bereichen 1..250 mm tabelliert.
- UI-Sektion „Passungen (DIN 5418)" mit Belastungsfall-Dropdown und
  Live-Anzeige der Klasse + Abmaße in µm.
- Werte werden als Metadaten ``load_case``, ``shaft_fit_class``,
  ``housing_fit_class`` und – soweit tabelliert – ``shaft_fit_upper_um``,
  ``shaft_fit_lower_um``, ``housing_fit_upper_um``, ``housing_fit_lower_um``
  am Bearing-Empty hinterlegt.

### v0.15.0 – Käfig-Bauart Ribbon
- Neue Käfig-Bauart ``RIBBON``: zwei genietete Halbringe oberhalb und
  unterhalb der Wälzkörpermitte, klassischer Pressblech-Stil. Halb-
  Pockets entstehen per Boolean-Subtraktion aus den vorhandenen Wälz-
  körper-Cuttern; zusätzliche Niete als kleine Zylinder in den Lücken
  zwischen den Pockets.
- Neue Property ``cage_style`` mit den Werten ``AUTO`` (Default),
  ``POCKET``, ``RIBBON``, ``LADDER``. ``AUTO`` behält das bisherige
  Verhalten (Sleeve → Fallback Leiter). Bei misslungenem Boolean fällt
  ``RIBBON`` ebenfalls auf den Leiter-Käfig zurück.
- UI: Auswahl im Käfig-Abschnitt; Style wird als Metadatum
  ``cage_style`` am Bearing-Empty hinterlegt (Werte: ``pocket``,
  ``ribbon``, ``ladder``).

### v0.16.0 – Norm-Engine als JSON-Datenquelle
- Neues Modul ``norm_engine.py`` lädt die Maßreihen aus JSON-Dateien
  unter ``uni_rolling_bearing/data/`` (ball/cylindrical/needle/tapered/
  spherical/vgroove). Dateien sind in zwei Codings beschreibbar:
  ``din623`` (Reihe → Bohrungskennzahl → ``[D, B]``) und ``direct``
  (Code → ``[d, D, B]``).
- ``constants.SERIES_PRESETS`` und ``constants.NORM_HINTS`` werden
  beim Import aus den JSON-Dateien gebaut – keine Hardcoded-Tabellen
  mehr im Code.
- Benutzer können eigene Presets als gleichnamige JSON unter
  ``<Blender-Scripts>/uni_bearing/`` ablegen; sie werden über die
  ausgelieferten Defaults gemerged.

### v0.23.0 – Rillen-Geometrie und realistische Kugelgrößen
- ``geometry.resolve_geometry`` / ``suggest_defaults`` rechnen für
  Rillenkugellager (BALL/VGROOVE) jetzt mit der Rillen-Formel
  ``max_kugel = radial_space / (2·f)``. Die Konformität ``f`` kommt aus
  den UI-Properties ``groove_conformity_inner/_outer`` (binding ist die
  größere); ohne Wert wird ``DEFAULT_BALL_GROOVE_CONFORMITY = 0.52``
  angenommen.
- ``TYPE_RING_THICKNESS_RATIO[BALL,VGROOVE]`` von 1/6 auf 1/12 reduziert.
  ``ring_thickness`` wird damit als Mindestwand zwischen Bohrung und
  Rillenboden interpretiert (vorher als Schulterhöhe). Die Kugel kann
  jetzt teilweise in beide Rillen eintauchen, statt rein zwischen den
  Schultern eingesperrt zu bleiben.
- Default-Vorschläge treffen damit reale ISO 15-Reihen (6204 → ø7.94 mm
  vs. vorher ø4.27 mm; 6304/6306 mit ±5 % Abweichung). Tests in
  ``tests/test_geometry.py`` verankern den 6204-Wert.
- Operatoren reichen die Konformität durch (``_groove_conformity_for``);
  bei nicht-BALL-Lagern bleibt die Berechnung unverändert.

### v0.22.0 – Sub-Panel-UX und Pendelrollen-Fixes
- N-Panel auf einklappbare Sub-Panels (``bl_parent_id``) umgestellt: jede
  Sektion (Lagertyp, Normen, Geometrie, Wälzkörper, Mesh, Tragzahlen,
  Passungen) ist jetzt eigenständig und individuell kollabierbar.
- Neue ``Ergebnisse``-Sub-Panel-Box bündelt die berechneten Werte aus
  Plausibilitäts-Check, Tragzahlen und Passungen (vorher in drei
  getrennten Sektionen vermischt mit den Eingaben).
- ``auto_recompute`` (Live-Auto-Berechnen in der Geometrie-Sektion) ist
  jetzt standardmäßig aktiv – Ringstärke, Wälzkörper-Ø und Anzahl werden
  bei jeder Änderung von d/D/Lagertyp automatisch passend gesetzt.
- **Pendelrollenlager (Tonnenlager) Fix:**
  ``ROLLER_LENGTH_RATIO[SPHERICAL]`` von ``0.85`` auf ``0.38`` korrigiert.
  Die Tonnenrolle ist ein *einzelner* Wälzkörper einer zweireihigen
  Anordnung – die alte Ratio hat die Länge wie bei einreihigen Lagern
  berechnet, sodass jede Rolle länger als eine Reihenhälfte war und
  sichtbar über die Lagerstirnflächen hinausragte.
- ``raceway.spherical_inner_row_z`` neu formuliert: row_z wird so gewählt,
  dass die beiden Reihen am Mittelband nicht überlappen und gleichzeitig
  innerhalb der Lagerbreite bleiben (vorher 0.55·half_proj erlaubte
  Überlappung; 0.55·half_w erlaubte Überstand). ``spherical_inner_ring_profile``
  ruft die Funktion auf, damit Profil- und Wälzkörper-Position synchron sind.
- Tests in ``tests/test_geometry.py``: zwei neue Asserts prüfen, dass die
  Rollen für eine typische 22210-Geometrie innerhalb des Lagers bleiben
  und sich am Mittelband nicht überlappen.

### v0.21.0 – Massivkäfig mit Schmiertaschen
- Neue Käfig-Bauart ``MASSIVE`` (Auswahl ``Massiv (Schmiertaschen)``):
  Pocket-Sleeve wie bei ``POCKET``, zusätzlich werden im tangentialen Steg
  zwischen je zwei Wälzkörper-Pockets radiale Bohrungen als Schmiertaschen
  ausgeschnitten – Stil eines gefrästen Messing-Massivkäfigs.
- Neue Property ``oil_pocket_diameter_mm`` (Default 0 = automatisch ≈ 50 %
  des kleineren Bauraums aus axialer Sleeve-Breite und tangentialem Steg).
  Werte werden auf den verfügbaren Bauraum geclampt; unter
  ``MIN_OIL_POCKET_DIAMETER_MM`` (0.3 mm) wird die Tasche weggelassen.
- Reicht der Bauraum für die Schmiertaschen nicht, fällt der Massivkäfig
  auf einen reinen Pocket-Sleeve zurück; bei misslungenem Pocket-Boolean
  greift die bestehende Leiter-Fallback-Kette.
- Reine Geometriefunktion ``geometry.oil_pocket_diameter`` für das Clamping
  (testbar ohne Blender), abgedeckt durch ``tests/test_geometry.py``.
- Werte werden als Metadaten ``oil_pocket_diameter_mm`` und
  ``oil_pocket_count`` am Bearing-Empty hinterlegt.

### v0.20.0 – X-/Y-Faktoren für äquivalente Last
- Statt einer einzigen ``equivalent_load_p_n``-Property werden jetzt
  ``radial_load_fr_n`` (Fr) und ``axial_load_fa_n`` (Fa) eingegeben. Die
  äquivalente Last ``P = X·Fr + Y·Fa`` wird nach ISO 281 Tabelle 4
  lagertypabhängig berechnet:
  - **Rillenkugellager (BALL/VGROOVE):** e und Y aus Fa/C0r-Tabelle
    interpoliert; X = 1 für Fa/Fr ≤ e, sonst X = 0.56.
  - **Kegelrollenlager (TAPERED):** e = 1.5·tan(α), Y = 0.4/tan(α);
    X = 1 für Fa/Fr ≤ e, sonst X = 0.4.
  - **Pendelrollenlager (SPHERICAL):** e = 1.5·tan(α); für Fa/Fr ≤ e gilt
    X = 1, Y1 ≈ 0.45/tan(α); darüber X = 0.67, Y2 ≈ 0.67/tan(α).
  - **Zylinderrollen-/Nadellager (CYLINDRICAL/NEEDLE):** rein radial,
    Fa wird ignoriert. Das Panel zeigt einen Warnhinweis, wenn der
    Anwender trotzdem Fa > 0 einträgt.
- Neue Helfer ``ratings.equivalent_load`` und ``ratings.LoadFactors``
  liefern X, Y, e und P als getrennte Werte.
- ``Ratings``-Dataclass enthält zusätzlich ``X``, ``Y``, ``e`` und
  ``P_N``. Panel zeigt die Werte live an; am erzeugten Bearing-Empty
  werden ``radial_load_Fr_N``, ``axial_load_Fa_N``, ``load_X``,
  ``load_Y``, ``load_e`` und ``equivalent_load_P_N`` als Metadaten
  hinterlegt (nur wenn mindestens eine Last > 0).
- Neue Tests in ``tests/test_ratings.py`` decken alle Lagertypen,
  Tabellen-Stützstellen, Clamping und das Zusammenspiel mit
  ``compute_ratings`` ab.

### v0.19.0 – f0/fc als γ-abhängige ISO-Tabellen
- ``ratings.py`` ersetzt die bisherigen Mittelwert-Konstanten ``f0``/``fc``
  durch interpolierte Werte aus den ISO 76- bzw. ISO 281-Annex-Tabellen,
  separat für Kugel- und Rollenlager. Zwischenwerte werden linear
  interpoliert, außerhalb des tabellierten Bereichs an den Randwerten
  geclampt.
- Neue Helfer ``ratings.gamma``, ``ratings.f0_for`` und ``ratings.fc_for``
  (öffentliche API). ``compute_ratings``/``static_load_rating``/
  ``dynamic_load_rating`` bekommen ``pitch_d_mm`` als Pflichtparameter,
  damit γ = Dw·cos(α)/dm aus der Lagergeometrie berechnet werden kann.
- ``Ratings``-Dataclass liefert zusätzlich ``gamma``, ``f0`` und ``fc``;
  diese werden im N-Panel als Live-Vorschau angezeigt und am erzeugten
  Bearing-Empty als Metadaten (``rating_gamma``, ``rating_f0``,
  ``rating_fc``) hinterlegt.
- Zusätzliche Tests in ``tests/test_ratings.py`` decken Tabellenwerte,
  Interpolation, Randwert-Clamping und die γ-Berechnung ab.

### v0.18.0 – UI-Workflow „Reihe → Bohrungskennzahl"
- Für Lagertypen mit DIN 623-Coding (BALL, CYLINDRICAL, TAPERED, SPHERICAL)
  zeigt das N-Panel zwei aufeinander aufbauende Dropdowns: erst
  ``Massreihe`` (z. B. ``60``, ``62``, ``NU3``, ``302``), dann
  ``Bohrungskennzahl`` (``00``..``96``). Pro Kennzahl wird der abgeleitete
  Bohrungs-Ø direkt im Label angezeigt (z. B. ``04  (d=20 mm)``); die
  kombinierte Lagerbezeichnung (z. B. ``6204``, ``NU306``, ``30212``) steht
  als Live-Vorschau unter den Dropdowns.
- Neuer Operator ``uni_bearing.apply_bore_code_preset`` setzt d/D/B aus
  Reihe + Kennzahl und übernimmt – bei Kegelrollenlagern – die getrennten
  Cone-/Cup-Breiten aus der Norm-Reihe. ``series_code`` wird synchron
  mitgeführt, damit ein späterer Umstieg zwischen den Workflows konsistent
  bleibt.
- Für Lagertypen mit ``direct``-Coding (NEEDLE, VGROOVE) bleibt die
  bisherige freie Code-Auswahl (z. B. ``HK1010``, ``SG20``) unverändert.
  Die UI schaltet je Lagertyp automatisch zwischen beiden Workflows um.
- Neue Helfer ``norm_engine.coding_for``, ``norm_engine.load_series_for``
  und ``norm_engine.load_bore_codes_for`` als Datenschicht für den UI-
  Workflow; abgedeckt durch ``tests/test_norm_engine.py``.

### v0.17.1 – Bugfix: Wälzkörper-Position und EnumProperty-Memory
- **Position-Bug**: Bei Zylinder-, Nadel-, Kegelrollen- und Pendelrollen-
  lagern wurden die Wälzkörper-Vertices zuerst im Mesh-Frame auf die
  Pitch-Position translatiert und anschließend per ``obj.rotation_euler[2] = a``
  zusätzlich um die Welt-Z gedreht. Da die Object-Pivot bei (0,0,0) lag,
  wirkte die Rotation um den Welt-Origin – die Rollen landeten bei Winkel
  ``2a`` statt ``a`` und überlappten sich paarweise (z. B. nur 5 statt 10
  unique Positionen bei 10 Rollen). Gleiches Problem traf die Pocket-Cage-
  Cutter. Fix in ``mesh_builders.add_uv_sphere``, ``add_cylinder``,
  ``add_tapered_roller`` und ``add_barrel_roller``: Vertices bleiben mesh-
  zentriert und die Position wird über ``obj.location`` gesetzt, sodass
  ``rotation_euler`` jetzt um den Wälzkörper-Mittelpunkt rotiert.
- **EnumProperty-Memory**: ``_series_items`` (Callback für ``series_code``)
  hat bei jedem Aufruf frische Strings erzeugt. Blender hält keine Referenz
  darauf – bekannter Pitfall, der zu UI-Korruption oder Crashes führen kann.
  Items werden nun pro Lagertyp in einem modul-globalen Cache gehalten.

### v0.17.0 – Kegelrollen-Reihen 313/320/322/323 + Cone/Cup-Breiten
- Vier zusätzliche DIN 720-Reihen (313, 320, 322, 323) als Norm-Presets
  in ``data/tapered.json``; insgesamt 46 Kegelrollen-Größen.
- JSON-Eintragsformat erweitert: ``[D, T]`` (Gesamtbreite) oder
  ``[D, T, B, C]`` mit getrennter Cone- (``B``) und Cup-Breite (``C``).
- ``norm_engine.load_ring_widths_for`` liest die getrennten Breiten aus
  und ``apply_series_preset`` überträgt sie in die neuen Properties
  ``tapered_cone_width_mm`` und ``tapered_cup_width_mm``.
- Innen- bzw. Außenring-Profil verwenden die separaten Breiten (falls
  > 0), sodass Cone und Cup tatsächlich unterschiedlich breit dargestellt
  werden statt beide T zu nutzen.
- Werte werden als Metadaten ``tapered_cone_width_mm`` und
  ``tapered_cup_width_mm`` am Bearing-Empty hinterlegt.

---

## Als Nächstes (kurzfristig) 🟡

1. **Weitere Norm-Tabellen**
   - SG-Reihe um Zwischengrößen (SG30, SG40, SG55) sowie U-Profil-Variante
     (Halbkreis-Rille statt 90°-V) ergänzen, sobald belastbare Maßquellen
     vorliegen.

2. **Käfig-Ausbaustufe**
   - Weitere Bauformen (z. B. Käfig mit Stiften/Bolzen-Verbindung,
     Schnappkäfig aus Polymer) evaluieren.

---

## Mittelfristig 🔵

(aktuell keine offenen Mittelfristig-Punkte – nächste Schritte siehe
Kurzfristig und Langfristig)

---

## Langfristig 🟣

1. Material- und Reibungsmodelle.
2. Animationssetup für Dreh-/Kontaktvisualisierung.
3. Exportprofile für CAD/CAM/Simulation (STEP-Workflow über externe Bridge).
4. Testsuite mit Referenzfällen gegen Normtabellen.
