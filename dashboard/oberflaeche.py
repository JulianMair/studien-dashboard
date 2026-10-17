"""Oberflaeche: Dashboard Fenster und die sechs Anzeigebereiche A bis F.

Jeder Bereich der Skizze ist eine eigene Klasse, die von Anzeigebereich erbt
und die Methode aktualisieren mit einer eigenen Darstellung beantwortet. Das
Fenster ruft fuer alle Bereiche dieselbe Methode auf, ohne deren Typ zu
kennen. Diese Polymorphie ist der Grund fuer die Vererbung an dieser Stelle:
Die Bereiche unterscheiden sich im Verhalten, nicht nur in ihren Daten.

Diagramme werden selbst auf einem tk.Canvas gezeichnet, damit keine externe
Bibliothek noetig ist. Das Fenster hat eine feste Groesse, damit die
Zeichnungen nicht bei jeder Groessenaenderung neu berechnet werden muessen.
"""

from __future__ import annotations

import tkinter as tk
from abc import ABC, abstractmethod
from datetime import date
from tkinter import messagebox, ttk

from .entities import Studiengang
from .persistenz import Datenspeicher

# ------------------------------------------------------------------ Gestaltung
PLAN = "#2F7A45"        # Ziel erreicht oder im Plan
VERZUG = "#A8352F"      # Ziel verfehlt oder im Rueckstand
TINTE = "#1B1B1B"
LINIE = "#C4C4C4"
FLAECHE = "#F1F1F1"
GEDAEMPFT = "#777777"

BREITE_HALB = 530       # Zeichenbreite von ECTS Balken und Notenskala
BREITE_VOLL = 1100      # Zeichenbreite des Semesterverlaufs und der Tabelle

#: Monate je Semester, fuer die Zahl der geplanten Semester in Bereich D
MONATE_JE_SEMESTER = 6

#: Schwellen aus Ziel Z3: kritisch bei weniger als 14 Tagen Restfrist und mehr
#: als der Haelfte offener Teile, oder wenn die Frist bereits abgelaufen ist.
KRITISCHE_RESTFRIST = 14
KRITISCHER_OFFENER_ANTEIL = 0.5


def _komma(wert: float, stellen: int = 1) -> str:
    """Formatiert eine Zahl mit deutschem Dezimalkomma."""
    return f"{wert:.{stellen}f}".replace(".", ",")


def _plus_monate(datum: date, monate: int) -> date:
    """Addiert ganze Monate auf ein Datum, ohne externe Bibliothek."""
    jahr, monat = divmod(datum.month - 1 + monate, 12)
    return date(datum.year + jahr, monat + 1, min(datum.day, 28))


def _notenposition(note: float) -> float:
    """Waagerechte Lage einer Note auf der Skala in Bereich C, 1,0 links."""
    beste, schlechteste, rand = Notenbereich.BESTE, Notenbereich.SCHLECHTESTE, Notenbereich.RAND
    anteil = (min(max(note, beste), schlechteste) - beste) / (schlechteste - beste)
    return rand + anteil * (BREITE_HALB - 2 * rand)


def _erzwinge_helle_darstellung(fenster: tk.Tk) -> None:
    """Haelt das Fenster unter macOS auch im Dunkelmodus hell.

    Tk ab Version 8.6.10 folgt unter macOS der Systemdarstellung. Der Aufruf
    setzt fuer dieses Fenster die helle Darstellung "aqua". Auf anderen
    Systemen oder aelteren Tk Versionen gibt es den Befehl nicht, dort ist er
    auch nicht noetig.
    """
    try:
        fenster.tk.call("::tk::unsupported::MacWindowStyle", "appearance",
                        fenster._w, "aqua")
    except tk.TclError:
        pass


# =================================================================== Basis
class Anzeigebereich(ttk.Frame, ABC):
    """Abstrakte Oberklasse aller Anzeigebereiche.

    Erbt zugleich von ttk.Frame, damit jeder Bereich ein Widget ist, und von
    ABC, damit Python die Erzeugung einer Unterklasse ohne aktualisieren
    verweigert. Die Reihenfolge der Basisklassen legt fest, dass Methoden
    zuerst in ttk.Frame gesucht werden.
    """

    def __init__(self, eltern: tk.Misc, titel: str) -> None:
        super().__init__(eltern, padding=(12, 8, 12, 10), style="Bereich.TFrame")
        self.titel = titel
        if titel:
            ttk.Label(self, text=titel.upper(), style="Bereichstitel.TLabel").pack(anchor="w")

    @abstractmethod
    def aktualisieren(self, s: Studiengang, stichtag: date) -> None:
        """Stellt den Bereich fuer den uebergebenen Studiengang neu dar."""


# =================================================================== A
class Kopfbereich(Anzeigebereich):
    """Bereich A: Studiengang, Beginn, Zieltermin und verbleibende Zeit (Z1)."""

    def __init__(self, eltern: tk.Misc, titel: str) -> None:
        super().__init__(eltern, titel)
        zeile = ttk.Frame(self, style="Bereich.TFrame")
        zeile.pack(fill="x", pady=(4, 0))
        self.werte: dict[str, ttk.Label] = {}
        for spalte, (schluessel, gross) in enumerate(
            (("Studiengang", False), ("Beginn", False),
             ("Zieltermin", False), ("Verbleibend", True))
        ):
            ttk.Label(zeile, text=schluessel, style="Klein.TLabel").grid(
                row=0, column=spalte, sticky="w", padx=(0, 36))
            wert = ttk.Label(zeile, style="Gross.TLabel" if gross else "Wert.TLabel")
            wert.grid(row=1, column=spalte, sticky="w", padx=(0, 36))
            self.werte[schluessel] = wert

    def aktualisieren(self, s: Studiengang, stichtag: date) -> None:
        """Siehe Anzeigebereich.aktualisieren."""
        self._zeige_stammdaten(s, stichtag)

    def _zeige_stammdaten(self, s: Studiengang, stichtag: date) -> None:
        """Schreibt Studiengang, Beginn, Zieltermin und verbleibende Monate."""
        zieltermin = _plus_monate(s.startdatum, s.ziel_dauer_monate)
        rest = (zieltermin.year - stichtag.year) * 12 + (zieltermin.month - stichtag.month)
        self.werte["Studiengang"].config(text=s.bezeichnung)
        self.werte["Beginn"].config(text=f"{s.startdatum:%d.%m.%Y}")
        self.werte["Zieltermin"].config(text=f"{zieltermin:%d.%m.%Y}")
        self.werte["Verbleibend"].config(
            text=f"{max(rest, 0)} Monate" if rest >= 0 else "Zieltermin überschritten")


# =================================================================== B
class Fortschrittsbereich(Anzeigebereich):
    """Bereich B: ECTS als Balken mit Marke fuer den Sollstand (Z1)."""

    HOEHE = 26

    def __init__(self, eltern: tk.Misc, titel: str) -> None:
        super().__init__(eltern, titel)
        self.leinwand = tk.Canvas(self, width=BREITE_HALB, height=self.HOEHE + 16,
                                  bg="white", highlightthickness=0)
        self.leinwand.pack(anchor="w", pady=(6, 4))
        self.text = ttk.Label(self, style="Wert.TLabel", justify="left")
        self.text.pack(anchor="w")
        self.lage = ttk.Label(self, style="Wert.TLabel")
        self.lage.pack(anchor="w")

    def aktualisieren(self, s: Studiengang, stichtag: date) -> None:
        """Siehe Anzeigebereich.aktualisieren."""
        self._zeichne_balken(s, stichtag)

    def _zeichne_balken(self, s: Studiengang, stichtag: date) -> None:
        """Zeichnet erreichte ECTS als Balken und den Sollstand als senkrechte Marke."""
        erreicht = s.ermittle_erreichte_ects()
        soll = s.ermittle_sollstand(stichtag)
        abweichung = s.ermittle_soll_ist_abweichung(stichtag)
        farbe = PLAN if abweichung >= 0 else VERZUG

        c, b, h, y = self.leinwand, BREITE_HALB - 2, self.HOEHE, 12
        c.delete("all")
        c.create_rectangle(1, y, b, y + h, fill=FLAECHE, outline=LINIE)
        c.create_rectangle(1, y, 1 + b * min(erreicht / s.ects_gesamt, 1.0), y + h,
                           fill=farbe, outline="")
        x_soll = 1 + b * min(soll / s.ects_gesamt, 1.0)
        c.create_line(x_soll, y - 4, x_soll, y + h + 4, fill=TINTE, width=2)
        c.create_text(x_soll + 4, y - 6, text="Soll heute", anchor="w",
                      font=("TkDefaultFont", 8), fill=TINTE)

        anteil = erreicht / s.ects_gesamt * 100
        self.text.config(text=f"{erreicht} von {s.ects_gesamt} ECTS, {anteil:.0f} Prozent\n"
                              f"Soll zum Stichtag {soll:.0f} ECTS")
        richtung = "im Rückstand" if abweichung < 0 else "Vorsprung"
        self.lage.config(text=f"{abs(abweichung):.0f} ECTS {richtung}", foreground=farbe)


# =================================================================== C
class Notenbereich(Anzeigebereich):
    """Bereich C: Notenskala von 1,0 bis 4,0 mit Ziel und aktuellem Wert (Z2).

    Bewusst kein Fortschrittsbalken: Eine Note ist keine Fortschrittsgroesse,
    und ein kleinerer Wert ist besser. Die Skala laeuft deshalb von links
    (beste Note) nach rechts.
    """

    BESTE, SCHLECHTESTE, RAND = 1.0, 4.0, 14

    def __init__(self, eltern: tk.Misc, titel: str) -> None:
        super().__init__(eltern, titel)
        self.leinwand = tk.Canvas(self, width=BREITE_HALB, height=46,
                                  bg="white", highlightthickness=0)
        self.leinwand.pack(anchor="w", pady=(6, 4))
        self.text = ttk.Label(self, style="Wert.TLabel")
        self.text.pack(anchor="w")
        self.lage = ttk.Label(self, style="Wert.TLabel")
        self.lage.pack(anchor="w")

    def aktualisieren(self, s: Studiengang, stichtag: date) -> None:
        """Siehe Anzeigebereich.aktualisieren."""
        self._zeichne_skala(s)

    def _zeichne_skala(self, s: Studiengang) -> None:
        """Zeichnet die Notenskala mit Zielmarke und dem aktuellen Schnitt als Dreieck."""
        c, y = self.leinwand, 24
        c.delete("all")
        c.create_line(_notenposition(self.BESTE), y, _notenposition(self.SCHLECHTESTE), y,
                      fill=LINIE, width=2)
        stufe = self.BESTE
        while stufe <= self.SCHLECHTESTE + 1e-9:
            x = _notenposition(stufe)
            c.create_line(x, y - 4, x, y + 4, fill=LINIE)
            c.create_text(x, y + 14, text=_komma(stufe), font=("TkDefaultFont", 8),
                          fill=GEDAEMPFT)
            stufe += 0.5

        ziel = s.ziel_notendurchschnitt
        xz = _notenposition(ziel)
        c.create_line(xz, 2, xz, y + 2, fill=TINTE, dash=(3, 2))
        c.create_text(xz + 4, 6, text=f"Ziel {_komma(ziel)}", anchor="w",
                      font=("TkDefaultFont", 8), fill=TINTE)

        schnitt = s.ermittle_notendurchschnitt()
        if schnitt is None:
            self.text.config(text=f"noch keine Note, Ziel {_komma(ziel)} oder besser")
            self.lage.config(text="")
            return
        farbe = PLAN if schnitt <= ziel else VERZUG
        xi = _notenposition(schnitt)
        c.create_polygon(xi - 7, y - 14, xi + 7, y - 14, xi, y - 2, fill=farbe, outline="")
        self.text.config(text=f"aktuell {_komma(schnitt, 2)}, Ziel {_komma(ziel)} oder besser, "
                              f"gewichtet nach ECTS")
        self.lage.config(text="Ziel erreicht" if schnitt <= ziel else "Ziel verfehlt",
                         foreground=farbe)


# =================================================================== D
class Verlaufsbereich(Anzeigebereich):
    """Bereich D: erreichte ECTS je Semester gegen den Sollwert (Z4)."""

    HOEHE = 130

    def __init__(self, eltern: tk.Misc, titel: str) -> None:
        super().__init__(eltern, titel)
        self.leinwand = tk.Canvas(self, width=BREITE_VOLL, height=self.HOEHE,
                                  bg="white", highlightthickness=1,
                                  highlightbackground=LINIE)
        self.leinwand.pack(anchor="w", pady=(6, 0))

    def aktualisieren(self, s: Studiengang, stichtag: date) -> None:
        """Siehe Anzeigebereich.aktualisieren."""
        self._zeichne_saeulen(s)

    def _zeichne_saeulen(self, s: Studiengang) -> None:
        """Zeichnet je geplantem Semester eine Saeule; offene Semester als Linie."""
        geplant = max(-(-s.ziel_dauer_monate // MONATE_JE_SEMESTER), len(s.semester))
        soll = s.ects_gesamt / geplant
        erreicht = {sem.nummer: sem.ermittle_erreichte_ects() for sem in s.semester}
        maximum = max([soll, *erreicht.values()]) * 1.3

        c, unten, nutz = self.leinwand, self.HOEHE - 22, self.HOEHE - 40
        c.delete("all")
        y_soll = unten - soll / maximum * nutz
        c.create_line(0, y_soll, BREITE_VOLL, y_soll, fill=VERZUG, dash=(4, 3))
        c.create_text(BREITE_VOLL - 6, y_soll - 8, text=f"Soll {soll:.0f} ECTS",
                      anchor="e", font=("TkDefaultFont", 8), fill=VERZUG)

        schritt = BREITE_VOLL / geplant
        for i in range(geplant):
            nummer = i + 1
            wert = erreicht.get(nummer, 0)
            mitte = schritt * (i + 0.5)
            if nummer in erreicht and wert > 0:
                farbe = PLAN if wert >= soll else VERZUG
                y = unten - wert / maximum * nutz
                c.create_rectangle(mitte - schritt * 0.3, y, mitte + schritt * 0.3, unten,
                                   fill=farbe, outline="")
                beschriftung = c.create_text(mitte, y - 9, text=str(wert),
                                             font=("TkDefaultFont", 9))
                # weisser Hintergrund, damit die Zahl auf der Sollinie lesbar bleibt
                hintergrund = c.create_rectangle(c.bbox(beschriftung), fill="white", outline="")
                c.tag_lower(hintergrund, beschriftung)
            else:
                # Semester noch nicht begonnen oder ohne Ergebnis
                c.create_line(mitte - schritt * 0.3, unten, mitte + schritt * 0.3, unten,
                              fill=LINIE, width=2)
            c.create_text(mitte, unten + 11, text=f"{nummer}. Sem",
                          font=("TkDefaultFont", 8), fill=GEDAEMPFT)


# =================================================================== E
class Terminbereich(Anzeigebereich):
    """Bereich E: offene Abgaben, dringlichste zuerst (Z3).

    Die Detailangabe liefert jede Pruefungsleistung selbst; diese Klasse
    enthaelt keine Fallunterscheidung nach der Pruefungsform.
    """

    SPALTEN = (("kuerzel", "Kürzel", 145, "w"), ("modul", "Modul", 430, "w"),
               ("form", "Form", 115, "w"), ("status", "Status", 95, "w"),
               ("detail", "Detail", 190, "w"), ("frist", "Restfrist", 115, "e"))

    def __init__(self, eltern: tk.Misc, titel: str) -> None:
        super().__init__(eltern, titel)
        self.tabelle = ttk.Treeview(self, columns=[sp[0] for sp in self.SPALTEN],
                                    show="headings", height=6, selectmode="none")
        for schluessel, ueberschrift, breite, ausrichtung in self.SPALTEN:
            self.tabelle.heading(schluessel, text=ueberschrift, anchor=ausrichtung)
            self.tabelle.column(schluessel, width=breite, anchor=ausrichtung, stretch=False)
        self.tabelle.tag_configure("kritisch", foreground=VERZUG)
        self.tabelle.tag_configure("abgegeben", foreground=GEDAEMPFT)
        self.tabelle.pack(anchor="w", pady=(6, 0))

    def aktualisieren(self, s: Studiengang, stichtag: date) -> None:
        """Siehe Anzeigebereich.aktualisieren."""
        self._fuelle_tabelle(s, stichtag)

    def _fuelle_tabelle(self, s: Studiengang, stichtag: date) -> None:
        """Fuellt die Tabelle mit den offenen Abgaben und markiert kritische rot."""
        self.tabelle.delete(*self.tabelle.get_children())
        for modul, leistung in s.ermittle_offene_abgaben(stichtag):
            rest = leistung.ermittle_restfrist_in_tagen(stichtag)
            offen = 1 - leistung.erledigte_teile / leistung.anzahl_teile
            if offen == 0:
                frist, markierung = "abgegeben", "abgegeben"
            elif rest < 0:
                frist, markierung = f"{-rest} Tage überfällig", "kritisch"
            else:
                frist = f"{rest} Tage"
                kritisch = rest < KRITISCHE_RESTFRIST and offen > KRITISCHER_OFFENER_ANTEIL
                markierung = "kritisch" if kritisch else ""
            self.tabelle.insert("", "end", tags=(markierung,), values=(
                modul.modulkuerzel, modul.titel, leistung.form.value, leistung.status.value,
                leistung.ermittle_detailangabe(), frist))


# =================================================================== F
class Statusleiste(Anzeigebereich):
    """Bereich F: Stand der angezeigten Daten, keinem Ziel zugeordnet."""

    def __init__(self, eltern: tk.Misc, titel: str) -> None:
        super().__init__(eltern, titel)
        self.text = ttk.Label(self, style="Klein.TLabel")
        self.text.pack(anchor="w")

    def aktualisieren(self, s: Studiengang, stichtag: date) -> None:
        """Siehe Anzeigebereich.aktualisieren."""
        self._zeige_stand(s, stichtag)

    def _zeige_stand(self, s: Studiengang, stichtag: date) -> None:
        """Zeigt Stichtag und Zahl der erfassten Module."""
        anzahl = sum(len(sem.module) for sem in s.semester)
        self.text.config(text=f"Stand: {stichtag:%d.%m.%Y}   ·   {anzahl} Module erfasst"
                              f"   ·   F5 lädt die Daten neu")


# =================================================================== Fenster
class DashboardFenster(tk.Tk):
    """Hauptfenster. Laedt den Studiengang und setzt die Bereiche zusammen."""

    def __init__(self, datenspeicher: Datenspeicher, stichtag: date) -> None:
        super().__init__()
        self.datenspeicher = datenspeicher
        self.studiengang: Studiengang | None = None
        self.stichtag = stichtag
        self.bereiche: list[Anzeigebereich] = []

    def aufbauen(self) -> None:
        """Legt Stile und die sechs Bereiche an und zeigt die Daten an."""
        self.title("Studien Dashboard")
        self.configure(bg="white")
        self.resizable(False, False)
        _erzwinge_helle_darstellung(self)

        stil = ttk.Style(self)
        # Das Thema "clam" folgt nicht dem Dunkelmodus des Betriebssystems.
        # Alle Farben werden zusaetzlich ausdruecklich gesetzt, damit kein
        # Element eine Systemfarbe uebernimmt.
        stil.theme_use("clam")
        stil.configure(".", background="white", foreground=TINTE)
        stil.configure("Bereich.TFrame", background="white")
        stil.configure("Bereichstitel.TLabel", background="white", foreground=GEDAEMPFT,
                       font=("TkDefaultFont", 8))
        stil.configure("Klein.TLabel", background="white", foreground=GEDAEMPFT,
                       font=("TkDefaultFont", 8))
        stil.configure("Wert.TLabel", background="white", foreground=TINTE,
                       font=("TkDefaultFont", 10))
        stil.configure("Gross.TLabel", background="white", foreground=TINTE,
                       font=("TkDefaultFont", 15, "bold"))
        stil.configure("Treeview", background="white", fieldbackground="white",
                       foreground=TINTE, rowheight=22, bordercolor=LINIE)
        stil.configure("Treeview.Heading", background=FLAECHE, foreground=GEDAEMPFT,
                       relief="flat", font=("TkDefaultFont", 9))
        stil.map("Treeview", background=[("selected", "white")],
                 foreground=[("selected", TINTE)])
        stil.map("Treeview.Heading", background=[("active", FLAECHE)])

        aufbau = (
            (Kopfbereich, "", 0, 0, 2),
            (Fortschrittsbereich, "ECTS im Sollverlauf", 1, 0, 1),
            (Notenbereich, "Notendurchschnitt", 1, 1, 1),
            (Verlaufsbereich, "ECTS je Semester", 2, 0, 2),
            (Terminbereich, "Nächste Abgaben", 3, 0, 2),
            (Statusleiste, "", 4, 0, 2),
        )
        for klasse, titel, zeile, spalte, breite in aufbau:
            bereich = klasse(self, titel)
            bereich.grid(row=zeile, column=spalte, columnspan=breite, sticky="nsew")
            self.bereiche.append(bereich)

        self.bind("<F5>", lambda _ereignis: self.aktualisieren())
        self.aktualisieren()

    def aktualisieren(self) -> None:
        """Laedt die Daten neu und stellt alle Bereiche dar.

        Polymorphie: Jeder Bereich erhaelt denselben Aufruf und beantwortet
        ihn auf seine Weise. Schlaegt das Laden fehl, bleibt die bisherige
        Anzeige erhalten und eine Meldung erklaert den Fehler.
        """
        try:
            self.studiengang = self.datenspeicher.laden()
        except (OSError, ValueError, KeyError) as fehler:
            if self.studiengang is None:
                raise
            messagebox.showerror("Daten konnten nicht geladen werden", str(fehler), parent=self)
            return
        for bereich in self.bereiche:
            bereich.aktualisieren(self.studiengang, self.stichtag)
