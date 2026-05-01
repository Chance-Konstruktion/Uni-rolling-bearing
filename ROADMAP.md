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

### Kegelrollen-Kontaktwinkel (v0.5.0)
- Eigenschaft ``contact_angle_deg`` (Default 14°), nur für TAPERED sichtbar.
- Wälzkörper werden im Mesh-Frame um die lokale Y-Achse gekippt; alle Achsen
  treffen sich auf der Lagerachse in einem gemeinsamen Apex.
- Apex-Z wird als ``tapered_apex_z_mm`` am Assembly hinterlegt.

### Echte Laufbahnen (v0.6.0)
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

---

## Als Nächstes (kurzfristig) 🟡

1. **Vollständige DIN/ISO-Tabellen**
   - Vollständige Reihen für DIN 625 / ISO 15 implementieren.
   - Automatische Code-Generierung nach DIN 623.

2. **Laufbahnen weiter verfeinern**
   - Konformitätsfaktor (Rille) als UI-Parameter exponieren.
   - Pendelrollen: Innenring mit zwei separaten Laufbahnen (heute zylindrisch).
   - Kegelrollen: Bord am Innenring (große Stirnseite) ergänzen.

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
