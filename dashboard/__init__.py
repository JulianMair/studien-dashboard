"""Studien Dashboard, Prototyp zum Portfolio DLBDSOOFPP01_D.

Das Paket ist in drei Schichten gegliedert, die der Gesamtarchitektur aus
Phase 2 entsprechen:

    entities      fachliche Klassen, berechnen die Kennzahlen selbst
    persistenz    Laden und Speichern des Studiengangs
    oberflaeche   Fenster und Anzeigebereiche auf Basis von tkinter

Abhaengigkeiten verlaufen nur in eine Richtung: Die Oberflaeche kennt
Persistenz und Entityklassen, die Persistenz kennt die Entityklassen, die
Entityklassen kennen keine der anderen Schichten.
"""

__version__ = "1.0.0"
