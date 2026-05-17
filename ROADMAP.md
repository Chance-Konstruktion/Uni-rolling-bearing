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

### Kantenfasen am Kugellager (v0.10.1)
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

---

### DIN 623 / ISO 15 Maßreihen (v0.12.0)
- Neues Modul ``din623.py`` mit DIN 623-Bohrungskennzahl-Logik
  (``bore_code_to_diameter``) sowie ISO 15-Maßtabellen für Rillenkugellager
  (Reihen 60/62/63/64/618/619), Zylinderrollenlager NU2/NU3, Kegelrollen
  302/303 und Pendelrollen 222/223.
- ``SERIES_PRESETS`` für BALL/CYLINDRICAL/TAPERED/SPHERICAL werden komplett
  aus den Tabellen generiert (~80 Rillenkugellager-Größen statt bisher 3).
- Nadellager-Presets manuell erweitert (HK0808–HK3020).
- Tests in ``tests/test_din623.py`` decken Bohrungskennzahl-Mapping und
  Konsistenz der generierten Presets ab.

---

## Als Nächstes (kurzfristig) 🟡

1. **Weitere Norm-Tabellen**
   - SG-Reihe um Zwischengrößen (SG30, SG40, SG55) sowie U-Profil-Variante
     (Halbkreis-Rille statt 90°-V) ergänzen, sobald belastbare Maßquellen
     vorliegen.
   - Kegelrollenlager-Reihen 313/320/322/323 ergänzen, Außenring-Breite C
     getrennt von T modellieren.

2. **Laufbahnen weiter verfeinern**
   - ✅ Pendelrollen: Innenring mit zwei separaten Laufbahnen + Mittelbord
     (``spherical_inner_ring_profile``); zwei Rollenreihen unter Kontaktwinkel α.

3. **Käfig-Ausbaustufe**
   - Optionale Schnapp-/Ribbon-Bauarten (zwei vernietete Halbringe) zusätzlich
     zum aktuellen Sleeve-Käfig.

---

## Mittelfristig 🔵

1. **Norm-Engine**
   - Datensatzverwaltung für DIN/ISO-Reihen als externe Datenquelle (JSON/CSV).
   - Auswahl nach Reihe + Bohrungskennzahl.

2. **Toleranzen / Passungen**
   - ✅ ISO 492-/DIN 620-Toleranzfenster werden in d, D, B umgerechnet
     (``tolerances.py``); Klassen NORMAL/P6/P5/P4 + Toleranzlage MAX/MEAN/MIN.
     Abweichungen werden in µm am Bearing-Empty hinterlegt.
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
