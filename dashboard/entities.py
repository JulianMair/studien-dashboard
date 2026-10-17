"""Entityschicht: die fachlichen Klassen des Studiendashboards.

Die Klassen entsprechen dem Klassendiagramm der Gesamtarchitektur. Namen sind
von der sprachunabhaengigen Schreibweise des Diagramms (ermittleErreichteEcts)
in die Python Konvention nach PEP 8 uebertragen (ermittle_erreichte_ects).

Alle Kennzahlen werden hier berechnet, und zwar ohne veraenderlichen Zustand:
Die Methoden lesen die Objekte, veraendern sie aber nicht. Methoden, deren
Ergebnis vom Datum abhaengt, erhalten den Stichtag als Parameter und fragen
das aktuelle Datum nicht selbst ab. Dadurch liefern sie bei gleichen
Eingaben stets dasselbe Ergebnis und sind reproduzierbar testbar.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from functools import reduce
from math import floor
from typing import Iterable

#: Durchschnittliche Laenge eines Monats in Tagen, fuer den Sollverlauf.
TAGE_PRO_MONAT = 365.25 / 12

#: ECTS werden nur in ganzen Modulen vergeben, ein Modul hat ein Vielfaches
#: von 5 ECTS. Auch der Sollstand wird deshalb auf dieses Raster gerundet.
ECTS_RASTER = 5


class Pruefungsform(Enum):
    """Im Studiengang vorkommende Pruefungsformen.

    Die Formen unterscheiden sich in ihren Daten, nicht in ihrem Verhalten.
    Sie werden deshalb als Aufzaehlung gefuehrt und nicht als Unterklassen.
    Der Wert ist die Bezeichnung, die in der Oberflaeche erscheint.
    """

    KLAUSUR = "Klausur"
    FALLSTUDIE = "Fallstudie"
    PORTFOLIO = "Portfolio"
    ADVANCED_WORKBOOK = "Advanced Workbook"
    SEMINARARBEIT = "Seminararbeit"


class Pruefungsstatus(Enum):
    """Bearbeitungsstand einer Pruefungsleistung."""

    OFFEN = "offen"
    ANGEMELDET = "angemeldet"
    BESTANDEN = "bestanden"
    NICHT_BESTANDEN = "nicht bestanden"


class Pruefungsleistung:
    """Eine Pruefungsleistung, die zu genau einem Modul gehoert.

    Attribute
        bezeichnung      frei waehlbarer Name, etwa "Klausur" oder "Portfolio"
        form             Pruefungsform als Aufzaehlung
        status           Bearbeitungsstand als Aufzaehlung
        termin           Klausurtermin oder Abgabefrist
        note             Note zwischen 1,0 und 5,0 oder None, solange keine vorliegt
        anzahl_teile     Zahl der Teile, mindestens 1
        erledigte_teile  Zahl bereits erledigter Teile
        detailangabe     reine Anzeigeangabe, etwa Dauer und Hilfsmittel, oder None
    """

    def __init__(
        self,
        bezeichnung: str,
        form: Pruefungsform,
        status: Pruefungsstatus,
        termin: date,
        note: float | None = None,
        anzahl_teile: int = 1,
        erledigte_teile: int = 0,
        detailangabe: str | None = None,
    ) -> None:
        if anzahl_teile < 1:
            # Untergrenze aus dem Diagramm {>= 1}: verhindert eine Division
            # durch null in ermittle_dringlichkeit.
            raise ValueError("anzahl_teile muss mindestens 1 sein")
        if note is not None and not 1.0 <= note <= 5.0:
            raise ValueError(f"Note {note} liegt ausserhalb von 1,0 bis 5,0")
        self.bezeichnung = bezeichnung
        self.form = form
        self.status = status
        self.termin = termin
        self.note = note
        self.anzahl_teile = anzahl_teile
        self.erledigte_teile = erledigte_teile
        self.detailangabe = detailangabe

    @property
    def erledigte_teile(self) -> int:
        """Zahl der erledigten Teile.

        Als Property umgesetzt, damit jede Zuweisung geprueft wird, ohne dass
        sich die Schnittstelle der Klasse aendert. Von aussen bleibt es die
        gewohnte Attributschreibweise.
        """
        return self._erledigte_teile

    @erledigte_teile.setter
    def erledigte_teile(self, wert: int) -> None:
        """Setzt die Zahl erledigter Teile und prueft den Bereich."""
        if not 0 <= wert <= self.anzahl_teile:
            raise ValueError(
                f"erledigte_teile muss zwischen 0 und {self.anzahl_teile} liegen"
            )
        self._erledigte_teile = wert

    def ist_bestanden(self) -> bool:
        """Liefert True, wenn die Leistung bestanden ist."""
        return self.status is Pruefungsstatus.BESTANDEN

    def ermittle_restfrist_in_tagen(self, stichtag: date) -> int:
        """Tage vom Stichtag bis zum Termin. Negativ, wenn der Termin vorbei ist."""
        return (self.termin - stichtag).days

    def ermittle_dringlichkeit(self, stichtag: date) -> float:
        """Offener Anteil der Leistung, geteilt durch die Restfrist in Tagen.

        Eine einteilige Leistung ist der Sonderfall mit einem Teil und wird
        von derselben Rechnung behandelt, eine Fallunterscheidung nach der
        Pruefungsform ist nicht noetig. Bei abgelaufener Frist wird durch
        eins geteilt, die Dringlichkeit entspricht dann dem offenen Anteil.
        """
        offen = 1.0 - self.erledigte_teile / self.anzahl_teile
        return offen / max(self.ermittle_restfrist_in_tagen(stichtag), 1)

    def ermittle_detailangabe(self) -> str:
        """Text fuer die Spalte Detail in Bereich E.

        Bei mehrteiligen Leistungen wird der Teilfortschritt aus den beiden
        Zaehlern berechnet, statt ihn doppelt zu speichern. Die gespeicherte
        detailangabe enthaelt nur, was sich nicht ableiten laesst.
        """
        teile = []
        if self.anzahl_teile > 1:
            teile.append(f"Teil {self.erledigte_teile} von {self.anzahl_teile}")
        if self.detailangabe:
            teile.append(self.detailangabe)
        return ", ".join(teile)


class Modul:
    """Ein Modul des Studiengangs mit seinen Pruefungsleistungen.

    Die Pruefungsleistungen stehen in Komposition zum Modul: Sie werden dem
    Modul bei der Erzeugung uebergeben, die Liste wird kopiert und gehoert
    danach allein dem Modul. Wiederholungsversuche sind weitere Eintraege.
    """

    def __init__(
        self,
        modulkuerzel: str,
        titel: str,
        ects: int,
        pruefungsleistungen: Iterable[Pruefungsleistung],
    ) -> None:
        if ects <= 0 or ects % ECTS_RASTER:
            raise ValueError(f"Modul {modulkuerzel}: ECTS muessen ein Vielfaches von "
                             f"{ECTS_RASTER} sein, nicht {ects}")
        self.modulkuerzel = modulkuerzel
        self.titel = titel
        self.ects = ects
        self.pruefungsleistungen: list[Pruefungsleistung] = list(pruefungsleistungen)
        if not self.pruefungsleistungen:
            raise ValueError(f"Modul {modulkuerzel} braucht mindestens eine Pruefungsleistung")

    def ist_bestanden(self) -> bool:
        """Ein Modul gilt als bestanden, sobald eine seiner Leistungen bestanden ist."""
        return any(p.ist_bestanden() for p in self.pruefungsleistungen)

    def ermittle_note(self) -> float | None:
        """Note der zuletzt bestandenen Leistung oder None.

        None bedeutet: noch nicht bestanden oder unbenotet bestanden.
        """
        bestandene = [p for p in self.pruefungsleistungen if p.ist_bestanden()]
        return bestandene[-1].note if bestandene else None


class Semester:
    """Ein Semester, das bestehende Module zusammenfasst.

    Die Module stehen in Aggregation zum Semester: Sie existieren unabhaengig
    davon und werden fertig uebergeben. In der gespeicherten Datei verweist
    ein Semester deshalb nur ueber die Modulkuerzel auf seine Module.
    """

    def __init__(self, nummer: int, bezeichnung: str, module: Iterable[Modul]) -> None:
        self.nummer = nummer
        self.bezeichnung = bezeichnung
        self.module: list[Modul] = list(module)

    def ermittle_erreichte_ects(self) -> int:
        """Summe der ECTS aller bestandenen Module dieses Semesters."""
        return sum(m.ects for m in self.module if m.ist_bestanden())


class Studiengang:
    """Der Studiengang als Wurzel des Objektbaums.

    Die Semester stehen in Komposition zum Studiengang. Er erzeugt sie selbst
    aus den uebergebenen Angaben und gibt sie nur als unveraenderliches Tupel
    heraus. Ein Semester existiert damit nicht ausserhalb seines Studiengangs.
    """

    def __init__(
        self,
        bezeichnung: str,
        ects_gesamt: int,
        startdatum: date,
        ziel_dauer_monate: int,
        ziel_notendurchschnitt: float,
        semester: Iterable[tuple[int, str, Iterable[Modul]]],
    ) -> None:
        self.bezeichnung = bezeichnung
        self.ects_gesamt = ects_gesamt
        self.startdatum = startdatum
        self.ziel_dauer_monate = ziel_dauer_monate
        self.ziel_notendurchschnitt = ziel_notendurchschnitt
        self._semester = tuple(
            Semester(nummer, bez, module) for nummer, bez, module in semester
        )
        if not self._semester:
            # Multiplizitaet 1..* aus dem Klassendiagramm
            raise ValueError("Ein Studiengang braucht mindestens ein Semester")

    @property
    def semester(self) -> tuple[Semester, ...]:
        """Die Semester, nur lesend. Komposition: Erzeugung erfolgt hier."""
        return self._semester

    def ermittle_erreichte_ects(self) -> int:
        """Summe der erreichten ECTS ueber alle Semester."""
        return sum(map(lambda s: s.ermittle_erreichte_ects(), self._semester))

    def ermittle_notendurchschnitt(self) -> float | None:
        """Nach ECTS gewichteter Durchschnitt aller Module mit Note.

        Funktional formuliert: filter waehlt die benoteten Module, reduce
        faltet Summe der gewichteten Noten und Summe der Gewichte in einem
        Durchlauf zusammen. Liefert None, solange kein Modul benotet ist.
        """
        alle_module = (m for s in self._semester for m in s.module)
        benotet = list(filter(lambda m: m.ermittle_note() is not None, alle_module))
        if not benotet:
            return None
        summe, gewicht = reduce(
            lambda acc, m: (acc[0] + m.ermittle_note() * m.ects, acc[1] + m.ects),
            benotet,
            (0.0, 0),
        )
        return summe / gewicht

    def ermittle_sollstand(self, stichtag: date) -> float:
        """ECTS, die nach linearem Sollverlauf zum Stichtag erreicht sein sollten.

        Da ECTS nur in Schritten von ECTS_RASTER erreichbar sind, wird der
        lineare Wert auf das naechste Vielfache gerundet. Dadurch ist auch die
        Soll Ist Abweichung stets ein Vielfaches davon.
        """
        vergangene_monate = (stichtag - self.startdatum).days / TAGE_PRO_MONAT
        anteil = min(max(vergangene_monate / self.ziel_dauer_monate, 0.0), 1.0)
        exakt = self.ects_gesamt * anteil
        return float(floor(exakt / ECTS_RASTER + 0.5) * ECTS_RASTER)

    def ermittle_soll_ist_abweichung(self, stichtag: date) -> float:
        """Erreichte minus Soll ECTS. Positiv bedeutet Vorsprung, negativ Rueckstand."""
        return self.ermittle_erreichte_ects() - self.ermittle_sollstand(stichtag)

    def ermittle_offene_abgaben(
        self, stichtag: date
    ) -> list[tuple[Modul, Pruefungsleistung]]:
        """Alle offenen oder angemeldeten Leistungen, dringlichste zuerst.

        Geliefert werden Paare aus Modul und Leistung, weil die Anzeige den
        Modultitel zur Leistung braucht.
        """
        offen = (Pruefungsstatus.OFFEN, Pruefungsstatus.ANGEMELDET)
        paare = [
            (m, p)
            for s in self._semester
            for m in s.module
            for p in m.pruefungsleistungen
            if p.status in offen
        ]
        return sorted(
            paare, key=lambda mp: mp[1].ermittle_dringlichkeit(stichtag), reverse=True
        )
