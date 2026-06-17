# ROADMAP – UNI Rolling Bearing Generator

Diese Datei listet die **geplanten, noch offenen** Arbeiten.
Bereits umgesetzte Änderungen stehen im [`CHANGELOG.md`](CHANGELOG.md).

---

## Als Nächstes (kurzfristig) 🟡

1. **FreeCAD-Workbench fertigstellen** (Port begonnen in v0.29)
   - Der host-freie Kern wird seit v0.29 von einem zweiten Frontend genutzt
     (`freecad_backend/`, `InitGui.py`, `package.xml`). Offen sind die
     GUI-Commands/Toolbar (Button „Lager erzeugen"), ein
     `Part::FeaturePython`-Proxy mit Live-Rebuild und ein kontextabhängiger
     Eigenschaften-Editor (`setEditorMode`). Danach Gegencheck in echtem FreeCAD
     (Workbench im Dropdown, Button erzeugt das Bauteil).

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
