"""Persistenzschicht: Laden und Speichern des Studiengangs.

Datenspeicher legt als abstrakte Klasse fest, was jeder Speicher koennen muss.
JsonDatenspeicher setzt dies fuer eine lokale JSON Datei um. Ein spaeterer
Wechsel auf eine Webschnittstelle waere eine weitere Unterklasse; Oberflaeche
und Entityklassen bleiben dabei unveraendert.

Aufbau der Datei
    Die Komposition zwischen Studiengang und Semester wird zur Verschachtelung,
    die Aggregation zwischen Semester und Modul zu einer Referenz ueber das
    Modulkuerzel. Module stehen deshalb in einer eigenen Liste "module", die
    Semester verweisen nur ueber Kuerzel darauf. Aufzaehlungen werden ueber
    ihren Namen gespeichert, Datumsangaben im ISO Format.
"""

from __future__ import annotations

import json
import os
import tempfile
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

from .entities import Modul, Pruefungsform, Pruefungsleistung, Pruefungsstatus, Studiengang


class Datenspeicher(ABC):
    """Abstrakte Oberklasse aller Datenspeicher.

    Die Klasse kann nicht instanziiert werden. Jede Unterklasse muss laden
    und speichern umsetzen, sonst verweigert Python die Erzeugung.
    """

    @abstractmethod
    def laden(self) -> Studiengang:
        """Liest den Studiengang vollstaendig ein."""

    @abstractmethod
    def speichern(self, s: Studiengang) -> None:
        """Schreibt den Studiengang vollstaendig."""


class JsonDatenspeicher(Datenspeicher):
    """Datenspeicher fuer eine lokale JSON Datei."""

    def __init__(self, pfad: str | Path) -> None:
        self.pfad = Path(pfad)

    def laden(self) -> Studiengang:
        """Liest die Datei und baut den Objektbaum wieder auf.

        Zuerst werden alle Module angelegt, danach die Kuerzel der Semester
        aufgeloest. Ein unbekanntes Kuerzel fuehrt zu einem verstaendlichen
        Fehler statt zu einem stillen Datenverlust.
        """
        daten = json.loads(self.pfad.read_text(encoding="utf-8"))

        module: dict[str, Modul] = {}
        for md in daten["module"]:
            leistungen = [
                Pruefungsleistung(
                    bezeichnung=p["bezeichnung"],
                    form=Pruefungsform[p["form"]],
                    status=Pruefungsstatus[p["status"]],
                    termin=date.fromisoformat(p["termin"]),
                    note=p.get("note"),
                    anzahl_teile=p.get("anzahl_teile", 1),
                    erledigte_teile=p.get("erledigte_teile", 0),
                    detailangabe=p.get("detailangabe"),
                )
                for p in md["pruefungsleistungen"]
            ]
            module[md["modulkuerzel"]] = Modul(
                md["modulkuerzel"], md["titel"], md["ects"], leistungen
            )

        semester = []
        for sd in daten["semester"]:
            fehlend = [k for k in sd["module"] if k not in module]
            if fehlend:
                raise ValueError(
                    f"Semester {sd['nummer']} verweist auf unbekannte Module: {fehlend}"
                )
            semester.append((sd["nummer"], sd["bezeichnung"], [module[k] for k in sd["module"]]))

        return Studiengang(
            bezeichnung=daten["bezeichnung"],
            ects_gesamt=daten["ects_gesamt"],
            startdatum=date.fromisoformat(daten["startdatum"]),
            ziel_dauer_monate=daten["ziel_dauer_monate"],
            ziel_notendurchschnitt=daten["ziel_notendurchschnitt"],
            semester=semester,
        )

    def speichern(self, s: Studiengang) -> None:
        """Wandelt den Objektbaum in JSON um und schreibt ihn atomar."""
        alle_module = {m.modulkuerzel: m for sem in s.semester for m in sem.module}
        daten = {
            "bezeichnung": s.bezeichnung,
            "ects_gesamt": s.ects_gesamt,
            "startdatum": s.startdatum.isoformat(),
            "ziel_dauer_monate": s.ziel_dauer_monate,
            "ziel_notendurchschnitt": s.ziel_notendurchschnitt,
            "semester": [
                {
                    "nummer": sem.nummer,
                    "bezeichnung": sem.bezeichnung,
                    "module": [m.modulkuerzel for m in sem.module],
                }
                for sem in s.semester
            ],
            "module": [
                {
                    "modulkuerzel": m.modulkuerzel,
                    "titel": m.titel,
                    "ects": m.ects,
                    "pruefungsleistungen": [
                        {
                            "bezeichnung": p.bezeichnung,
                            "form": p.form.name,
                            "status": p.status.name,
                            "termin": p.termin.isoformat(),
                            "note": p.note,
                            "anzahl_teile": p.anzahl_teile,
                            "erledigte_teile": p.erledigte_teile,
                            "detailangabe": p.detailangabe,
                        }
                        for p in m.pruefungsleistungen
                    ],
                }
                for m in alle_module.values()
            ],
        }
        self._schreibe_atomar(json.dumps(daten, indent=2, ensure_ascii=False))

    def _schreibe_atomar(self, inhalt: str) -> None:
        """Schreibt zuerst in eine temporaere Datei und benennt sie dann um.

        Das Umbenennen ist auf Dateisystemebene unteilbar. Bricht das Programm
        waehrend des Schreibens ab, bleibt die bisherige Datei unversehrt.
        """
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        deskriptor, temporaer = tempfile.mkstemp(dir=self.pfad.parent, suffix=".tmp")
        try:
            with os.fdopen(deskriptor, "w", encoding="utf-8") as datei:
                datei.write(inhalt)
            # mkstemp legt die Datei nur fuer den Besitzer lesbar an;
            # die Datendatei soll die ueblichen Rechte behalten
            os.chmod(temporaer, 0o644)
            os.replace(temporaer, self.pfad)
        except BaseException:
            # Bei einem Fehler keine verwaiste temporaere Datei zuruecklassen
            Path(temporaer).unlink(missing_ok=True)
            raise
