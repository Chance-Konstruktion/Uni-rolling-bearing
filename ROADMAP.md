# ROADMAP – UNI Rolling Bearing Generator

## Erledigt ✅

### Basis-Addon & UI
- Addon-Struktur mit `bl_info`, Registrierung und N-Panel erstellt.
- Lagertyp-Dropdown als Einstieg umgesetzt.
- Unterstützte Typen: Kugel-, Zylinderrollen-, Nadel-, Kegelrollen- und Tonnenlager.
- Erstellen-Button am Panel-Ende integriert.

### Normorientierung
- Start-Presets für mehrere Lagerreihen eingebaut.
- Toleranzklasse (ISO 492-Orientierung) und radiale Lagerluft als Parameter aufgenommen.
- Normhinweise als Objekt-Metadaten hinterlegt.

### Funktionsfähigkeit (Fix)
- Geometrie-Resolver ergänzt, der Laufbahnspalt und nutzbaren Wälzkörperraum prüft.
- Auto-Fit ergänzt:
  - begrenzt Wälzkörperdurchmesser auf geometrisch zulässigen Wert,
  - begrenzt Anzahl nach Umfangsabstand.
- Ergebnis als funktionale Baugruppe geändert:
  - Komponenten bleiben getrennt,
  - gemeinsame Assembly über Empty-Parent.

### Mesh-Qualität
- Manifold-orientierte Erzeugung je Ring/Wälzkörper via BMesh.
- Non-manifold-Kantenprüfung pro erzeugter Komponente.

### Käfig (v0.4.0)
- Optionaler parametrischer Käfig im Stil "Leitercage": zwei axiale Endplatten
  zwischen Lagerrand und Wälzkörperende, dazwischen tangentiale Webs in den
  Lücken zwischen den Wälzkörpern.
- Endplatten werden gegen die Laufbahnen geclippt (Sicherheitsabstand), Webs
  nutzen den verbleibenden Tangentialspalt.
- UI-Toggle ``Käfig erzeugen``; bei zu wenig Platz wird der Käfig
  übersprungen und eine Warnung gemeldet.

---

## Als Nächstes (kurzfristig) 🟡

1. **Vollständige DIN/ISO-Tabellen**
   - Vollständige Reihen für DIN 625 / ISO 15 implementieren.
   - Automatische Code-Generierung nach DIN 623.

2. **Typ-spezifische Laufbahnen verbessern**
   - Geometrisch genauere raceway-Profile pro Lagertyp.
   - Verbesserte Kegelgeometrie (Kontaktwinkel-basiert).

3. **Käfig-Ausbaustufe**
   - Typ-spezifische Pocket-Geometrie (sphärische Pockets für Kugellager,
     trapezförmig für Kegelrollen).
   - Werkstoffvarianten (Stahlblech, Messing, Polymer) als Metadatum.

4. **Fehlerfeedback erweitern**
   - Detailliertere UI-Meldungen mit konkreten Korrekturvorschlägen.

---

## Mittelfristig 🔵

1. **Norm-Engine**
   - Datensatzverwaltung für DIN/ISO-Reihen als externe Datenquelle (JSON/CSV).
   - Auswahl nach Reihe + Bohrungskennzahl.

2. **Toleranzen / Passungen**
   - ISO 492-/DIN 620-Toleranzfenster in Geometrie umsetzen.
   - Passungen für Welle/Gehäuse (DIN 5418-orientiert).

3. **Technische Kennwerte**
   - Statische/dynamische Tragzahl (ISO 76 / ISO 281) als Ausgabewerte.
   - Optional Lebensdauerabschätzung in UI.

---

## Langfristig 🟣

1. Material- und Reibungsmodelle.
2. Animationssetup für Dreh-/Kontaktvisualisierung.
3. Exportprofile für CAD/CAM/Simulation (STEP-Workflow über externe Bridge).
4. Testsuite mit Referenzfällen gegen Normtabellen.
