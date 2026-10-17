"""Startpunkt des Studien Dashboards.

Aufruf
    python main.py                         zeigt daten/studium.json zum heutigen Tag
    python main.py --stichtag 2026-08-22   zeigt den Stand zu einem festen Datum
    python main.py --daten pfad/datei.json verwendet eine andere Datendatei

Fehlt die Datendatei, wird sie aus den Beispieldaten erzeugt.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

MINDESTVERSION = (3, 10)
STANDARDDATEI = Path(__file__).resolve().parent / "daten" / "studium.json"


def pruefe_umgebung() -> None:
    """Bricht mit einer verstaendlichen Meldung ab, wenn Python oder Tk fehlt."""
    if sys.version_info < MINDESTVERSION:
        sys.exit(f"Benötigt wird Python {MINDESTVERSION[0]}.{MINDESTVERSION[1]} oder neuer, "
                 f"gefunden wurde {sys.version.split()[0]}.")
    try:
        import tkinter  # noqa: F401  nur Verfuegbarkeit pruefen
    except ImportError:
        hinweise = {
            "darwin": "macOS mit Homebrew:  brew install python-tk@3.13",
            "linux": "Linux mit apt:        sudo apt install python3-tk",
            "win32": "Windows: Python neu installieren und 'tcl/tk and IDLE' anhaken",
        }
        sys.exit("Die Tk Anbindung fehlt (Modul _tkinter).\n"
                 + hinweise.get(sys.platform, "Bitte Tk für Python nachinstallieren."))


def datum(text: str) -> date:
    """Wandelt JJJJ-MM-TT in ein Datum, mit verstaendlicher Fehlermeldung."""
    try:
        return date.fromisoformat(text)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"'{text}' ist kein Datum im Format JJJJ-MM-TT, etwa 2026-08-22") from None


def lies_argumente() -> argparse.Namespace:
    """Liest Datendatei und Stichtag von der Kommandozeile."""
    zerleger = argparse.ArgumentParser(description="Studien Dashboard")
    zerleger.add_argument("--daten", type=Path, default=STANDARDDATEI,
                          help="Pfad zur JSON Datei mit den Studiendaten")
    zerleger.add_argument("--stichtag", type=datum, default=date.today(),
                          help="Datum der Auswertung im Format JJJJ-MM-TT, Standard: heute")
    return zerleger.parse_args()


def main() -> int:
    """Prueft die Umgebung, legt fehlende Daten an und startet das Fenster."""
    pruefe_umgebung()
    argumente = lies_argumente()

    # Importe erst nach der Pruefung, damit eine fehlende Tk Anbindung zu
    # einer Meldung fuehrt und nicht zu einem Traceback.
    from dashboard.beispieldaten import erzeuge_beispieldaten
    from dashboard.oberflaeche import DashboardFenster
    from dashboard.persistenz import JsonDatenspeicher

    speicher = JsonDatenspeicher(argumente.daten)
    if not speicher.pfad.exists():
        speicher.speichern(erzeuge_beispieldaten())
        print(f"Beispieldaten angelegt: {speicher.pfad}")

    fenster = DashboardFenster(speicher, argumente.stichtag)
    try:
        fenster.aufbauen()
    except (OSError, ValueError, KeyError) as fehler:
        fenster.destroy()
        sys.exit(f"Die Daten in {speicher.pfad} konnten nicht gelesen werden:\n{fehler}")
    fenster.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
