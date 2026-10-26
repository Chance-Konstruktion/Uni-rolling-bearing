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


---

## Audit-Ergänzung (2026-10): Korrektheit vor Feature-Ausbau

Die folgenden Punkte sind aus einer statischen Codeprüfung abgeleitet. Sie sind
keine Behauptung, dass die gesamte Anwendung bereits zur Laufzeit verifiziert
wurde. Jeder Punkt muss mit reproduzierbaren Tests bzw. Host-Tests abgeschlossen
werden.

### P0 – Berechnungsfehler und Sicherheitsgrenzen

- [ ] Tragzahl-/Lebensdauerformeln gegen veröffentlichte Hersteller-Referenzfälle
  und lizenzrechtlich nutzbare Normauszüge validieren; Modellgrenzen in der UI
  sichtbar machen.
- [x] Reproduzierbarer Fehlerfall „Kegelrollenlager, Fr = 0, Fa > 0“ behoben;
  ein Regressionstest stellt sicher, dass die Axiallast in P eingeht.
- [ ] Lastfälle mit ausschließlich axialer Belastung systematisch für alle
  Lagertypen gegen Referenzfälle prüfen; die vereinfachten Beiwerte sind damit
  noch nicht als vollständig normvalidiert anzusehen.
- [x] Hostfreie Eingabevalidierung für nicht-endliche Werte, nichtpositive
  Hauptmaße, negative Lagerluft/Umfangsspalte, ungültige Wälzkörperzahlen,
  Konformitäten, Kontaktwinkel und unbekannte Lagertypen ergänzt.
- [x] Typabhängige Optionen (V/U-Rille, Winkel, Fasen, Käfigstil/-werkstoff,
  Clearances und Mesh-Auflösung) in einem gemeinsamen Validator ergänzt.
- [x] Die unterstützte Wälzkörperzahl auf das UI-Limit von 256 begrenzt, um
  unkontrolliert große Baupläne/Meshes bei extremen Maßverhältnissen zu verhindern.
- [x] Last-/Drehzahlwerte in der FreeCAD-Auswertung auf negative und nicht-endliche
  Eingaben geprüft; Fehler werden angezeigt statt stillschweigend normalisiert.
- [ ] Grenzen und Einheiten zusätzlich an den echten Blender-/FreeCAD-UI-
  Eingabepunkten prüfen; insbesondere alle hostseitigen Eigenschaften testen.
- [x] Auto-fit-Korrekturen für Wälzkörper-Ø und Anzahl werden in den
  Ergebnisanzeigen ausgewiesen; Resolverfehler liefern eine erklärende Meldung.

### P1 – Geometrie und CAD-Topologie

- [ ] Referenzfälle für alle sechs Lagertypen definieren: Hauptmaße, Teilkreis,
  Wälzkörperzahl, Laufbahnabstände und Mindestwandstärken.
- [ ] Blender-Meshes auf geschlossene/manifold Topologie, Normalen, Selbst-
  schnitte und Maßhaltigkeit prüfen; zusätzlich grobe und feine Auflösung testen.
- [ ] FreeCAD-Formen in einer echten unterstützten FreeCAD-Version prüfen:
  `Shape.isValid()`, Solid-Anzahl, Volumen, Bounding Box und STEP-Roundtrip.
- [x] FreeCAD-Käfig-Boolean-Fehler werden nicht mehr still übersprungen:
  ein fehlgeschlagener/nuller/ungültiger Schnitt löst eine erklärende Exception
  mit Hinweis auf Geometrieprüfung oder LADDER-Käfig aus.
- [x] FreeCAD-Rebuild-Fehler erscheinen in einer schreibgeschützten Status-
  Property; bestehende Dokumentobjekte erhalten die Property beim nächsten
  Rebuild. Der letzte gültige Shape bleibt erhalten, wird aber als nicht
  aktualisiert gekennzeichnet.
- [x] Der Part-Backend prüft Ring-, Wälzkörper-, Käfig- und Compound-Ergebnisse
  auf leere/ungültige Solids, sofern die Host-API diese Prüfungen bereitstellt.
- [ ] Boolean-Stabilität und Fallbacks zusätzlich in echtem FreeCAD mit
  unterschiedlichen Käfigstilen und Lagerabmessungen prüfen.
- [ ] Blender- und FreeCAD-Ergebnisse anhand derselben numerischen Referenzfälle
  vergleichen; hostfreie Plan-Tests ersetzen diese Integrationstests nicht.

### P1 – Normdaten, Toleranzen und Passungen

- [ ] Jede Datenreihe mit Quelle, Normausgabe/Jahr, Tabellenreferenz und
  Gültigkeitsbereich dokumentieren.
- [x] Größen außerhalb des abgedeckten Toleranztabellenbereichs (>250 mm)
  geben jetzt eine explizite Meldung aus, statt stillschweigend auf den letzten
  Tabellenwert zu klemmen.
- [ ] ISO-492-Toleranzfenster je Größenbereich und Präzisionsklasse gegen
  Referenzwerte prüfen; pauschale Skalierungsfaktoren nicht als vollständige
  Normtabellen ausgeben.
- [ ] ISO-286-Abmaße an allen Bereichsgrenzen testen, insbesondere exakt an
  Grenzdurchmessern und außerhalb des abgedeckten Bereichs.
- [ ] DIN-5418-Passungsempfehlungen gegen Lastfall, Lastniveau, Ringrotation,
  Temperatur und gewünschte Verschiebbarkeit validieren.
- [ ] Katalog-Presets stichprobenartig gegen Herstellerdaten prüfen; geometrische
  Plausibilität allein ist kein Beleg für Normkonformität.

### P2 – Automatisierte Qualitätssicherung und Release

- [x] Finale CI-Matrix für Python 3.10/3.11/3.12 ist grün: je 279 hostfreie
  Unit-Tests bestanden, Syntaxcheck bestanden und `build_addon_zip.py --check`
  bestätigt die Synchronität des ausgelieferten ZIP.
- [ ] Weiterhin offen: reale Blender-/FreeCAD-Integrationsläufe und unabhängige
  Referenzfälle gegen Norm-/Herstellerdaten.
- [ ] Property-/Grenzwerttests und unabhängige Referenzdatentests weiter ausbauen;
  die bestehende CI prüft derzeit Syntax, hostfreie Unit-Tests und ZIP-Synchronität.
- [ ] Separaten, optionalen Integrationslauf für Blender und FreeCAD einrichten,
  mit protokollierten Versionen und exportierten Testartefakten.
- [ ] STEP-Export und Reimport mit mindestens einem Kugel-, Zylinder- und
  Kegelrollenlager als Release-Gate etablieren.
- [ ] Dokumentation auf den belegten Funktionsumfang begrenzen und Näherungen
  klar von normativ validierten Berechnungen trennen.

### P2 – Danach: Funktionsausbau

- [ ] Fehlende SG-Zwischengrößen erst nach verifizierter Maßquelle ergänzen.
- [ ] Käfigvarianten nach Robustheit und Fertigbarkeit priorisieren.
- [ ] Material-/Reibungsmodelle und Kontaktvisualisierung erst nach stabiler
  Geometrie- und Berechnungsvalidierung beginnen.
