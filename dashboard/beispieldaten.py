"""Beispieldaten, damit das Dashboard beim ersten Start sofort gefuellt ist.

Die Datei daten/studium.json wird aus dieser Funktion erzeugt, falls sie
fehlt. Dadurch passt ihr Format garantiert zu JsonDatenspeicher.
Ausser den Modulen DLBMIUID01-01, IWNF02 und DLBDSOOFPP01_D sind Kuerzel,
Titel, Noten und Termine Beispielwerte.
"""

from __future__ import annotations

from datetime import date

from .entities import Modul, Pruefungsform, Pruefungsleistung, Pruefungsstatus, Studiengang

B = Pruefungsstatus.BESTANDEN


def _bestanden(kuerzel: str, titel: str, form: Pruefungsform, termin: date,
               note: float, ects: int = 5) -> Modul:
    """Kurzform fuer ein bereits bestandenes Modul mit einer Leistung."""
    return Modul(kuerzel, titel, ects,
                 [Pruefungsleistung(form.value, form, B, termin, note=note)])


def erzeuge_beispieldaten() -> Studiengang:
    """Liefert einen Studiengang mit drei begonnenen von sechs Semestern."""
    k, f, p = Pruefungsform.KLAUSUR, Pruefungsform.FALLSTUDIE, Pruefungsform.PORTFOLIO

    semester1 = [
        _bestanden("MAT1", "Mathematik Grundlagen I", k, date(2025, 3, 14), 2.3),
        _bestanden("PRG1", "Einführung in die Programmierung mit Python", p,
                   date(2025, 2, 20), 1.3),
        _bestanden("INF1", "Grundlagen der Informatik", k, date(2025, 4, 2), 1.7),
        _bestanden("WIA1", "Wissenschaftliches Arbeiten", f, date(2025, 5, 9), 2.0),
        _bestanden("ENG1", "Business English", k, date(2025, 5, 23), 2.3),
    ]
    semester2 = [
        _bestanden("MAT2", "Mathematik Grundlagen II", k, date(2025, 8, 29), 2.3),
        _bestanden("DST1", "Algorithmen und Datenstrukturen", k, date(2025, 9, 18), 1.7),
        _bestanden("BSY1", "Betriebssysteme und Rechnernetze", k, date(2025, 10, 10), 2.0),
        _bestanden("WEB1", "Web Programmierung", p, date(2025, 11, 7), 1.3),
        _bestanden("REQ1", "Requirements Engineering", f, date(2025, 12, 5), 1.7),
        _bestanden("AGI1", "Agiles Projektmanagement", f, date(2026, 1, 16), 2.0),
    ]
    semester3 = [
        _bestanden("DLBMIUID01-01", "Gestaltung und Ergonomie von User Interfaces", f,
                   date(2026, 6, 30), 1.7),
        _bestanden("SEC1", "IT Sicherheit", k, date(2026, 5, 8), 2.0),
        Modul("IWNF02", "Projekt Agiles Software Engineering", 5, [
            Pruefungsleistung("Portfolio", p, Pruefungsstatus.ANGEMELDET,
                              date(2026, 11, 6), anzahl_teile=3, erledigte_teile=1),
        ]),
        Modul("DLBDSOOFPP01_D", "Objektorientierte und funktionale Programmierung mit Python",
              5, [
                  Pruefungsleistung("Portfolio", p, Pruefungsstatus.ANGEMELDET,
                                    date(2026, 12, 15), anzahl_teile=3, erledigte_teile=1),
              ]),
        Modul("DBS1", "Datenbanken", 5, [
            Pruefungsleistung("Klausur", k, Pruefungsstatus.ANGEMELDET,
                              date(2026, 11, 20), detailangabe="90 Min, mit Hilfsmitteln"),
        ]),
        Modul("DSC1", "Data Science", 5, [
            # Abgegeben, aber noch nicht bewertet: alle Teile erledigt
            Pruefungsleistung("Fallstudie", f, Pruefungsstatus.ANGEMELDET,
                              date(2026, 10, 30), erledigte_teile=1,
                              detailangabe="max. 15 Seiten"),
        ]),
        Modul("STA1", "Statistik", 5, [
            Pruefungsleistung("Klausur", k, Pruefungsstatus.OFFEN,
                              date(2027, 2, 12), detailangabe="90 Min, mit Hilfsmitteln"),
        ]),
    ]

    return Studiengang(
        bezeichnung="Softwareentwicklung, B.Sc.",
        ects_gesamt=180,
        startdatum=date(2024, 12, 1),
        ziel_dauer_monate=36,
        ziel_notendurchschnitt=2.0,
        semester=[
            (1, "1. Semester", semester1),
            (2, "2. Semester", semester2),
            (3, "3. Semester", semester3),
        ],
    )
