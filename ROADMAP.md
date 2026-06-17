# ROADMAP – UNI Rolling Bearing Generator

Diese Datei listet die **geplanten, noch offenen** Arbeiten.
Bereits umgesetzte Änderungen stehen im [`CHANGELOG.md`](CHANGELOG.md).

---

## Als Nächstes (kurzfristig) 🟡

1. **FreeCAD-Workbench: Gegencheck am Host** (Port umgesetzt in v0.29–v0.30)
   - Kern, Bauplan, `Part`-Backend (v0.29) **und** die Workbench-GUI
     (`Part::FeaturePython`-Proxy mit Live-Rebuild, Command „Lager erzeugen",
     kontextabhängiger Eigenschaften-Editor, Toolbar/Menü – v0.30) stehen und
     sind ohne Host getestet. **Offen ist nur die Restklasse:** der manuelle
     Gegencheck in echtem FreeCAD (Workbench erscheint im Dropdown, Button
     erzeugt das Bauteil, STEP-Export). Danach ggf. Feinschliff am
     Eigenschaften-Editor und Norm-Preset-Anbindung in FreeCAD.

2. **Weitere Norm-Tabellen**
   - SG-Reihe um Zwischengrößen (SG30, SG40, SG55) ergänzen, sobald belastbare
     Maßquellen vorliegen. (Die U-Profil-Variante der Außenrille ist seit
     v0.24 umgesetzt – siehe `vgroove_shape`.)

3. **Käfig-Ausbaustufe**
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
3. STEP/CAM-Export: läuft künftig **nativ über die FreeCAD-Workbench**
   (BREP-Solids → STEP/IGES) statt über eine Bridge aus Blender. Voraussetzung
   ist die Fertigstellung der Workbench (siehe Kurzfristig).
4. Testsuite mit Referenzfällen gegen Normtabellen.
