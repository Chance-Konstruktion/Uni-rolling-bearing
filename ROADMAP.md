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

### Pocket-Käfig (v0.7.0)
- Standard-Käfig ist jetzt ein einteiliger Sleeve mit typabhängigen Pockets,
  erzeugt per Boolean-Difference aus oversized Wälzkörper-Stempeln.
- Pocket-Form folgt dem Lagertyp: sphärisch (Kugel), zylindrisch (Zylinder/
  Nadel), kegelig (Kegelrolle), tonnenförmig (Tonnenlager).
- Fallback auf den bisherigen Leiter-Käfig, wenn der Boolean nicht
  durchgreift; ``cage_style`` (``"pocket"``/``"ladder"``) wird als Meta-
  daten am Assembly hinterlegt.
- Neue Helfer ``mesh_builders.apply_boolean_difference`` als zentrale
  Schnittstelle für Boolean-basierte Mesh-Operationen.

### U-Rillen-Kugellager / SG-Reihe (v0.8.0)
- Neuer Lagertyp ``VGROOVE`` (Führungsrollen-Kugellager).
- Norm-Presets ``SG10``, ``SG15``, ``SG20``, ``SG25``, ``SG35``, ``SG66``
  mit handelsüblichen Hauptmaßen (Bishop-Wisecarver / Misumi „SG/W“-Reihe).
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

### Konformitätsfaktor als UI-Parameter (v0.9.1)
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

### Detailliertes Fehlerfeedback (v0.9.0)
- Geometrie-Resolver liefert nun konkrete Korrekturvorschläge mit Zahlen
  (max. zulässige Ringstärke, max. Lagerluft, max. Wälzkörper-Ø/-anzahl)
  statt rein generischer Meldungen.
- Operator-Reports (Auto-Berechnen, Preset-Übernahme, Erstellen) geben
  Hinweise auf konkrete nächste Schritte (z. B. „Auto-Fit aktivieren",
  „Reihen-Code wechseln").

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

### Käfig-Ausbau & Kegelrollen-Bord (v0.10.0)
- Käfig-Werkstoff (``Stahlblech``/``Messing``/``Polymer``) als UI-Auswahl,
  wird als Metadatum ``cage_material`` am Bearing-Empty hinterlegt.
- Pocket-Spiel als UI-Parameter ``pocket_clearance_mm`` (Default 0.20 mm,
  Bereich 0–1 mm) – ersetzt die bisherige Konstante in den Boolean-Cuttern.
- Kegelrollenlager: optionaler Bord am Innenring (große Stirnseite,
  ``tapered_flange_height_mm``, Default 1.0 mm). Höhe wird auf den verbleibenden
  Bauraum bis zur Außenlaufbahn (abzgl. Lagerluft) begrenzt.

---

## Als Nächstes (kurzfristig) 🟡

1. **Vollständige DIN/ISO-Tabellen**
   - Vollständige Reihen für DIN 625 / ISO 15 implementieren.
   - Automatische Code-Generierung nach DIN 623.
   - SG-Reihe um Zwischengrößen (SG30, SG40, SG55) sowie U-Profil-Variante
     (Halbkreis-Rille statt 90°-V) ergänzen, sobald belastbare Maßquellen
     vorliegen.

2. **Laufbahnen weiter verfeinern**
   - Pendelrollen: Innenring mit zwei separaten Laufbahnen (heute zylindrisch).

3. **Käfig-Ausbaustufe**
   - Optionale Schnapp-/Ribbon-Bauarten (zwei vernietete Halbringe) zusätzlich
     zum aktuellen Sleeve-Käfig.

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
