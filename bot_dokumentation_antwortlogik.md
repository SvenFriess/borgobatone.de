# 📜 Borgo-Bot – Antwortlogik & Trigger-System

## 1. Überblick
Der Borgo-Bot reagiert auf Nachrichten in einer fest definierten Signal-Gruppe, die mit dem Präfix `!Bot` beginnen.  
Je nach Inhalt der Nachricht wird **eine feste Standardantwort** zurückgegeben oder die Anfrage an das **lokale LLM** weitergeleitet.

Die Entscheidung erfolgt in drei Stufen:
1. **HARD_RESPONSES** – Immer feste Antwort
2. **SOFT_RESPONSES** – Feste Antwort nur bei Kurzkommandos
3. **LLM** – Für alle anderen Anfragen

---

## 2. A) HARD_RESPONSES – Immer feste Antwort
| Schlüsselwort / Regex   | Zweck / Inhalt der festen Antwort |
|-------------------------|------------------------------------|
| `\\bhallo\\b`             | Begrüßung („👋 Willkommen in Borgo Batone! Wie kann ich helfen?“) |
| `\\bpizzaofen\\b`         | Anleitung für den Pizzaofen (Anfeuern, Vorheizen, Backzeit) |
| `\\bmüll\\b`              | Mülltrennungs-Infos (Rest, Papier, Plastik/Metall, Glas) |
| `\\bwlan\\b`              | WLAN-Name (SSID) & Passwort |
| `\\bhund\\b`              | Regeln für Hunde (Leine, Poolverbot, Entsorgung) |
| `\\bpool\\b`              | Pool-Infos (Öffnungszeiten, Regeln) |
| `gemeinschaftsküche`    | Hinweise zur Nutzung der Gemeinschaftsküche |
| `\\bwaschmaschine\\b`     | Standort & Nutzungszeiten der Waschmaschine |
| `\\bfahrrad\\b`           | Fahrrad-Lagerort & Schloss-Code |
| `\\balarmanlage\\b`       | Alarmanlagen-Code & Aktivierungs-Hinweis |
| `\\bwasser\\b`            | Lage der Trinkwasserquelle |
| `\\bnotfall\\b`           | Notrufnummer (112) & nächste Arztpraxis |

**Eigenschaften:**
- Höchste Priorität bei der Auswertung
- Immer feste Antwort, unabhängig von Zusatztexten oder Länge der Anfrage
- Nutzt Regex mit Wortgrenzen, um zufällige Teiltreffer zu vermeiden

---

## 3. B) SOFT_RESPONSES – Feste Antwort nur bei Kurzkommandos
*(≤ 3 Wörter, kein „?“ – sonst geht die Nachricht ans LLM)*

| Schlüsselwort / Regex         | Zweck / Inhalt der festen Antwort |
|--------------------------------|------------------------------------|
| `\\beinkaufen\\b`                | Infos zu Einkaufsmöglichkeiten in S. Martino & Alimentari Pini |
| `\\böffnungszeiten\\b`           | Öffnungszeiten kleiner Läden, Hinweis auf Siesta |
| `\\barzt\\b`                     | Arzt in S. Martino, Notdienstregelung in Italien |
| `\\btransport\\b`                | Infos zu Bahnhof, Busverbindungen, Empfehlung Auto |
| `\\bkarte\\b`                    | Grobe Ortsbeschreibung (Lucca, Küste) |
| `\\bveranstaltungen\\b`          | Hinweis auf Aushang & Signal-Gruppe für Events |
| `\\bwetter\\b`                   | Allgemeine Wetterbeschreibung (Sommer/Abend) |
| `wie ist das wetter\\?`         | Demo-Standardantwort für Wetter |
| `\\bhilfe\\b`                    | Allgemeiner Hilfetext mit Beispielthemen |

---

## 4. 📌 Was sind Kurzkommandos?
Ein **Kurzkommando** ist eine Nachricht, die folgende Kriterien erfüllt:
1. **Maximal 3 Wörter** nach dem `!Bot`-Präfix  
   - `!Bot einkaufen` ✅  
   - `!Bot einkaufen morgen` ❌
2. **Kein Fragezeichen** enthalten  
   - `!Bot hilfe` ✅  
   - `!Bot hilfe?` ❌
3. Enthält ein Stichwort aus **SOFT_RESPONSES**

---

## 5. Entscheidungslogik
1. **HARD-Trigger** erkannt → immer feste Antwort
2. Kein HARD, aber **SOFT + Kurzkommando** → feste Antwort
3. Alles andere → **LLM-Aufruf**

---

## 6. Ablaufdiagramm

![Antwortlogik Diagramm](bot_antwortlogik.png)

---

## 7. Beispiele

| Eingabe                                    | Kategorie      | Antwortquelle  |
|--------------------------------------------|----------------|----------------|
| `!Bot wlan`                                | HARD           | Standardtext   |
| `!Bot alarmanlage`                         | HARD           | Standardtext   |
| `!Bot einkaufen`                           | SOFT + kurz    | Standardtext   |
| `!Bot einkaufen morgen`                    | SOFT + lang    | LLM            |
| `!Bot wie ist das wetter?`                 | SOFT + kurz    | Standardtext   |
| `!Bot wetter in lucca morgen`              | SOFT + lang    | LLM            |
| `!Bot gibt es hier ein gutes Restaurant?`  | kein Match     | LLM            |

---

## 8. Vorteile dieser Logik
- **Effizienz:** LLM wird nur bei komplexeren Anfragen genutzt
- **Sicherheit:** Kritische Daten wie WLAN-Passwort oder Codes immer aus festen Antworten
- **Flexibilität:** Weiche Trigger ermöglichen schnelle Infos und gleichzeitig komplexe LLM-Antworten bei Bedarf
