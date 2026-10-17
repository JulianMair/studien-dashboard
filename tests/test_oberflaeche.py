"""Tests der Oberflaeche. Werden uebersprungen, wenn keine Anzeige verfuegbar ist."""

from __future__ import annotations

import tempfile
import unittest
from datetime import date
from pathlib import Path

try:
    import tkinter as tk
    from dashboard.oberflaeche import Anzeigebereich, DashboardFenster
    from dashboard.persistenz import JsonDatenspeicher
    from dashboard.beispieldaten import erzeuge_beispieldaten
    _wurzel = tk.Tk()
    _wurzel.destroy()
    ANZEIGE = True
except Exception:  # keine Tk Anbindung oder kein Bildschirm
    ANZEIGE = False


@unittest.skipUnless(ANZEIGE, "keine grafische Anzeige verfuegbar")
class TestOberflaeche(unittest.TestCase):

    def setUp(self):
        pfad = Path(tempfile.mkdtemp()) / "studium.json"
        speicher = JsonDatenspeicher(pfad)
        speicher.speichern(erzeuge_beispieldaten())
        self.fenster = DashboardFenster(speicher, date(2026, 10, 30))
        self.fenster.aufbauen()

    def tearDown(self):
        self.fenster.destroy()

    def test_sechs_bereiche_alle_unterschiedlich(self):
        typen = {type(b) for b in self.fenster.bereiche}
        self.assertEqual(len(typen), 6)
        self.assertTrue(all(isinstance(b, Anzeigebereich) for b in self.fenster.bereiche))

    def test_anzeigebereich_ohne_aktualisieren_nicht_erzeugbar(self):
        class Unvollstaendig(Anzeigebereich):
            pass
        with self.assertRaises(TypeError):
            Unvollstaendig(self.fenster, "x")

    def test_kurze_restfrist_wird_als_kritisch_markiert(self):
        # Agiles Projekt: Abgabe am 06.11.2026, Stichtag 30.10.2026, 1 von 3 Teilen
        termin = self.fenster.bereiche[4]
        # erste Spalte ist das Modulkuerzel
        zeilen = {termin.tabelle.item(i)["values"][0]: termin.tabelle.item(i)["tags"]
                  for i in termin.tabelle.get_children()}
        self.assertIn("kritisch", zeilen["IWNF02"])
        # Python Portfolio: noch 46 Tage, deshalb nicht kritisch
        self.assertNotIn("kritisch", zeilen["DLBDSOOFPP01_D"])


if __name__ == "__main__":
    unittest.main()
