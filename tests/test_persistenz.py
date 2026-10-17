"""Tests der Persistenzschicht: Hin und Rueckweg, Dateiaufbau und Fehlerfaelle."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from dashboard.beispieldaten import erzeuge_beispieldaten
from dashboard.persistenz import Datenspeicher, JsonDatenspeicher

STICHTAG = date(2026, 10, 9)


class TestJsonDatenspeicher(unittest.TestCase):

    def setUp(self):
        self.verzeichnis = Path(tempfile.mkdtemp())
        self.speicher = JsonDatenspeicher(self.verzeichnis / "studium.json")
        self.original = erzeuge_beispieldaten()
        self.speicher.speichern(self.original)

    def test_abstrakte_klasse_nicht_instanziierbar(self):
        with self.assertRaises(TypeError):
            Datenspeicher()

    def test_kennzahlen_ueberstehen_hin_und_rueckweg(self):
        geladen = self.speicher.laden()
        for methode in ("ermittle_erreichte_ects", "ermittle_notendurchschnitt"):
            self.assertEqual(getattr(geladen, methode)(), getattr(self.original, methode)())
        self.assertEqual(geladen.ermittle_sollstand(STICHTAG),
                         self.original.ermittle_sollstand(STICHTAG))

    def test_fehlende_note_bleibt_none(self):
        offene = [p for _, p in self.speicher.laden().ermittle_offene_abgaben(STICHTAG)]
        self.assertTrue(offene)
        self.assertTrue(all(p.note is None for p in offene))

    def test_aggregation_als_referenz_ueber_kuerzel(self):
        daten = json.loads(self.speicher.pfad.read_text(encoding="utf-8"))
        self.assertTrue(all(isinstance(k, str) for s in daten["semester"] for k in s["module"]))

    def test_aufzaehlungen_ueber_namen_gespeichert(self):
        daten = json.loads(self.speicher.pfad.read_text(encoding="utf-8"))
        leistung = daten["module"][0]["pruefungsleistungen"][0]
        self.assertEqual(leistung["form"], leistung["form"].upper())

    def test_atomares_schreiben_hinterlaesst_keine_reste(self):
        self.speicher.speichern(self.original)
        self.assertEqual(list(self.verzeichnis.glob("*.tmp")), [])

    def test_unbekanntes_kuerzel_wird_gemeldet(self):
        daten = json.loads(self.speicher.pfad.read_text(encoding="utf-8"))
        daten["semester"][0]["module"].append("GIBTESNICHT")
        self.speicher.pfad.write_text(json.dumps(daten), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.speicher.laden()


if __name__ == "__main__":
    unittest.main()
