"""Tests der Entityschicht: Kennzahlen, Grenzfaelle und Pruefungen beim Anlegen."""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from dashboard.entities import (Modul, Pruefungsform, Pruefungsleistung,
                                Pruefungsstatus, Studiengang)

K, P = Pruefungsform.KLAUSUR, Pruefungsform.PORTFOLIO
BESTANDEN, OFFEN = Pruefungsstatus.BESTANDEN, Pruefungsstatus.OFFEN
STICHTAG = date(2026, 1, 1)


def leistung(**kwargs) -> Pruefungsleistung:
    """Erzeugt eine Leistung mit sinnvollen Standardwerten."""
    werte = dict(bezeichnung="x", form=K, status=OFFEN, termin=date(2026, 1, 11))
    werte.update(kwargs)
    return Pruefungsleistung(**werte)


def studiengang(*module: Modul) -> Studiengang:
    return Studiengang("Test", 180, date(2025, 1, 1), 36, 2.0, [(1, "1. Sem", module)])


class TestPruefungsleistung(unittest.TestCase):

    def test_note_darf_fehlen(self):
        self.assertIsNone(leistung().note)

    def test_note_ausserhalb_des_bereichs_wird_abgewiesen(self):
        with self.assertRaises(ValueError):
            leistung(note=0.7)

    def test_null_teile_werden_abgewiesen(self):
        with self.assertRaises(ValueError):
            leistung(anzahl_teile=0)

    def test_property_prueft_auch_spaetere_zuweisung(self):
        p = leistung(anzahl_teile=3)
        p.erledigte_teile = 3
        with self.assertRaises(ValueError):
            p.erledigte_teile = 4

    def test_restfrist(self):
        self.assertEqual(leistung().ermittle_restfrist_in_tagen(STICHTAG), 10)

    def test_dringlichkeit_einteilig(self):
        self.assertAlmostEqual(leistung().ermittle_dringlichkeit(STICHTAG), 1 / 10)

    def test_dringlichkeit_mehrteilig_beruecksichtigt_fortschritt(self):
        p = leistung(anzahl_teile=4, erledigte_teile=3)
        self.assertAlmostEqual(p.ermittle_dringlichkeit(STICHTAG), 0.25 / 10)

    def test_dringlichkeit_bei_abgelaufener_frist_ohne_division_durch_null(self):
        p = leistung(termin=STICHTAG)
        self.assertAlmostEqual(p.ermittle_dringlichkeit(STICHTAG), 1.0)

    def test_detailangabe_kombiniert_fortschritt_und_text(self):
        p = leistung(form=P, anzahl_teile=3, erledigte_teile=2, detailangabe="digital")
        self.assertEqual(p.ermittle_detailangabe(), "Teil 2 von 3, digital")

    def test_detailangabe_ohne_teile_nur_text(self):
        self.assertEqual(leistung(detailangabe="90 Min").ermittle_detailangabe(), "90 Min")


class TestModul(unittest.TestCase):

    def test_note_der_bestandenen_leistung(self):
        m = Modul("M", "M", 5, [leistung(status=Pruefungsstatus.NICHT_BESTANDEN, note=5.0),
                                leistung(status=BESTANDEN, note=2.3)])
        self.assertTrue(m.ist_bestanden())
        self.assertEqual(m.ermittle_note(), 2.3)

    def test_offenes_modul_hat_keine_note(self):
        self.assertIsNone(Modul("M", "M", 5, [leistung()]).ermittle_note())

    def test_ects_nur_in_fuenferschritten(self):
        with self.assertRaises(ValueError):
            Modul("M", "M", 7, [leistung()])

    def test_modul_ohne_leistung_wird_abgewiesen(self):
        with self.assertRaises(ValueError):
            Modul("M", "M", 5, [])


class TestStudiengang(unittest.TestCase):

    def test_gewichteter_durchschnitt(self):
        s = studiengang(Modul("A", "A", 5, [leistung(status=BESTANDEN, note=1.0)]),
                        Modul("B", "B", 10, [leistung(status=BESTANDEN, note=2.5)]))
        self.assertAlmostEqual(s.ermittle_notendurchschnitt(), (5 * 1.0 + 10 * 2.5) / 15)

    def test_unbenotet_bestanden_zaehlt_ects_aber_nicht_zur_note(self):
        s = studiengang(Modul("A", "A", 5, [leistung(status=BESTANDEN)]),
                        Modul("B", "B", 5, [leistung(status=BESTANDEN, note=2.0)]))
        self.assertEqual(s.ermittle_erreichte_ects(), 10)
        self.assertEqual(s.ermittle_notendurchschnitt(), 2.0)

    def test_ohne_note_kein_durchschnitt(self):
        s = studiengang(Modul("A", "A", 5, [leistung()]))
        self.assertIsNone(s.ermittle_notendurchschnitt())

    def test_sollstand_begrenzt_auf_null_und_gesamt(self):
        s = studiengang(Modul("A", "A", 5, [leistung()]))
        self.assertEqual(s.ermittle_sollstand(date(2024, 1, 1)), 0)
        self.assertEqual(s.ermittle_sollstand(date(2030, 1, 1)), 180)
        self.assertAlmostEqual(s.ermittle_sollstand(date(2026, 7, 2)), 90, delta=1)

    def test_sollstand_immer_vielfaches_von_fuenf(self):
        s = studiengang(Modul("A", "A", 5, [leistung()]))
        for tag in range(0, 1200, 7):
            soll = s.ermittle_sollstand(date(2025, 1, 1) + timedelta(days=tag))
            self.assertEqual(soll % 5, 0, soll)

    def test_offene_abgaben_dringlichste_zuerst_ohne_bestandene(self):
        frueh = leistung(termin=date(2026, 1, 3))
        spaet = leistung(termin=date(2026, 3, 1))
        fertig = leistung(status=BESTANDEN, note=1.0)
        s = studiengang(Modul("A", "A", 5, [spaet]), Modul("B", "B", 5, [frueh]),
                        Modul("C", "C", 5, [fertig]))
        reihenfolge = [p for _, p in s.ermittle_offene_abgaben(STICHTAG)]
        self.assertEqual(reihenfolge, [frueh, spaet])

    def test_studiengang_ohne_semester_wird_abgewiesen(self):
        with self.assertRaises(ValueError):
            Studiengang("S", 180, date(2025, 1, 1), 36, 2.0, [])

    def test_semester_von_aussen_nicht_austauschbar(self):
        s = studiengang(Modul("A", "A", 5, [leistung()]))
        self.assertIsInstance(s.semester, tuple)
        with self.assertRaises(AttributeError):
            s.semester = ()


if __name__ == "__main__":
    unittest.main()
