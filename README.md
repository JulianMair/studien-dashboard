# Studien Dashboard

Prototyp eines Dashboards zur Überwachung des eigenen Studienfortschritts,
entstanden im Portfolio des Kurses *Objektorientierte und funktionale
Programmierung mit Python* (DLBDSOOFPP01_D) an der IU.

Das Dashboard zeigt vier Ziele auf einen Blick:

| Ziel | Bereich | Aussage |
|---|---|---|
| Z1 Abschluss in der Zielzeit | A, B | erreichte ECTS gegenüber dem Sollstand zum Stichtag |
| Z2 Notendurchschnitt | C | nach ECTS gewichteter Schnitt gegenüber dem Zielwert |
| Z3 keine Abgabe versäumen | E | offene Leistungen nach Dringlichkeit, kritische rot |
| Z4 gleichmäßige Auslastung | D | ECTS je Semester gegenüber dem Richtwert |

## Voraussetzungen

* Python 3.10 oder neuer
* die Tk Anbindung von Python. Unter Windows ist sie im Installationsprogramm
  enthalten. Unter macOS mit Homebrew: `brew install python-tk@3.13`, unter
  Linux: `sudo apt install python3-tk`

Externe Pakete werden nicht benötigt.

## Starten

```
git clone <Repository-Link>
cd studien-dashboard
python main.py
```

Unter macOS und Linux gegebenenfalls `python3` statt `python`.

Weitere Aufrufe:

```
python main.py --stichtag 2026-11-12      Stand zu einem festen Datum
python main.py --daten meine_daten.json   andere Datendatei
```

Fehlt die Datendatei, wird sie aus Beispieldaten angelegt. Nach einer
Änderung an der Datei lädt die Taste F5 die Anzeige neu.

## Tests

```
python -m unittest -v
```

Die Oberflächentests werden übersprungen, wenn keine grafische Anzeige
verfügbar ist.

## Aufbau

```
main.py                    Startpunkt, prüft Python Version und Tk
dashboard/entities.py      Studiengang, Semester, Modul, Prüfungsleistung
dashboard/persistenz.py    Datenspeicher, JsonDatenspeicher
dashboard/oberflaeche.py   DashboardFenster, Anzeigebereich und die Bereiche A bis F
dashboard/beispieldaten.py Beispieldaten für den ersten Start
daten/studium.json         Studiendaten
tests/                     Tests mit unittest
```

Die Klassen entsprechen dem Klassendiagramm der Gesamtarchitektur aus
Phase 2. Bezeichner sind von der Schreibweise des Diagramms
(`ermittleErreichteEcts`) in die Python Konvention nach PEP 8 übertragen
(`ermittle_erreichte_ects`).

## Datenformat

Die Komposition Studiengang zu Semester ist verschachtelt, die Aggregation
Semester zu Modul ist eine Referenz über das Modulkürzel:

```json
{
  "bezeichnung": "Softwareentwicklung, B.Sc.",
  "ects_gesamt": 180,
  "startdatum": "2024-12-01",
  "ziel_dauer_monate": 36,
  "ziel_notendurchschnitt": 2.0,
  "semester": [
    {"nummer": 1, "bezeichnung": "1. Semester", "module": ["MAT1", "PRG1"]}
  ],
  "module": [
    {
      "modulkuerzel": "MAT1", "titel": "Mathematik Grundlagen I", "ects": 5,
      "pruefungsleistungen": [
        {"bezeichnung": "Klausur", "form": "KLAUSUR", "status": "BESTANDEN",
         "termin": "2025-03-14", "note": 2.3, "anzahl_teile": 1,
         "erledigte_teile": 0, "detailangabe": null}
      ]
    }
  ]
}
```

Zulässige Werte für `form`: KLAUSUR, FALLSTUDIE, PORTFOLIO, ADVANCED_WORKBOOK,
SEMINARARBEIT. Für `status`: OFFEN, ANGEMELDET, BESTANDEN, NICHT_BESTANDEN.
Eine fehlende Note wird als `null` eingetragen.

ECTS eines Moduls müssen ein Vielfaches von 5 sein. Auch der Sollstand wird
auf ein Vielfaches von 5 gerundet, da sich ECTS nur in ganzen Modulen erreichen
lassen.
