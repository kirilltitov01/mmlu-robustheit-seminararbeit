"""
Baut Tippfehler (Vertauschung mit einer Nachbartaste) in die MMLU-Fragen ein.

- Tippfehler nur in der Frage (inkl. Quelltext); die Antwortoptionen A-D bleiben unverändert
- Fehlerrate bezogen auf die Buchstaben der Frage
- Nur Ersetzung durch eine benachbarte Taste: QWERTZ für Deutsch, QWERTY für Englisch
- Groß-/Kleinschreibung bleibt erhalten
- Nicht verändert werden: Zahlen, Satz- und Formelzeichen, Leerzeichen, Wörter mit
  weniger als 3 Buchstaben, Abkürzungen in GROSSBUCHSTABEN (NATO, ATC, AUSSER ...)
  und Buchstaben direkt neben Ziffern oder Formelzeichen (z. B. rad/s, v0^2)
- Fester Seed pro Frage; die 5-%-Fehler sind eine Teilmenge der 15-%-Fehler

Aufruf:
    python tippfehler_einbauen.py mmlu_auswahl_de.xlsx mmlu_auswahl_en.xlsx
Erzeugt z. B. mmlu_auswahl_de_tippfehler05.xlsx und mmlu_auswahl_de_tippfehler15.xlsx
"""
import random
import re
import sys
from pathlib import Path

import pandas as pd

STUFEN = [0.05, 0.15]
SEED = 42
FELDER = ["question"]  # nur die Frage bekommt Tippfehler, Antwortoptionen A-D bleiben fehlerfrei

LAYOUTS = {
    "de": ["qwertzuiopü", "asdfghjklöä", "yxcvbnm"],
    "en": ["qwertyuiop", "asdfghjkl", "zxcvbnm"],
}


def nachbarn_berechnen(reihen):
    nb = {}
    for r, reihe in enumerate(reihen):
        for i, taste in enumerate(reihe):
            kandidaten = []
            if i > 0:
                kandidaten.append(reihe[i - 1])
            if i < len(reihe) - 1:
                kandidaten.append(reihe[i + 1])
            if r > 0:  # Reihe darüber (versetzt)
                oben = reihen[r - 1]
                kandidaten += [oben[j] for j in (i, i + 1) if j < len(oben)]
            if r < len(reihen) - 1:  # Reihe darunter
                unten = reihen[r + 1]
                kandidaten += [unten[j] for j in (i - 1, i) if 0 <= j < len(unten)]
            nb[taste] = kandidaten
    return nb


WORT = re.compile(r"[A-Za-zÄÖÜäöüß]+")
SPERRZEICHEN = set("0123456789/^=+*·_")


def erlaubte_positionen(text, nachbarn):
    """Positionen der Buchstaben, die verändert werden dürfen."""
    pos = []
    for m in WORT.finditer(text):
        wort = m.group()
        if len(wort) < 3 or wort.isupper():
            continue
        davor = text[m.start() - 1] if m.start() > 0 else " "
        danach = text[m.end()] if m.end() < len(text) else " "
        if davor in SPERRZEICHEN or danach in SPERRZEICHEN:
            continue
        pos += [m.start() + k for k, ch in enumerate(wort) if ch.lower() in nachbarn]
    return pos


def sprache_aus_name(pfad):
    name = pfad.stem.lower()
    if "_de" in name:
        return "de"
    if "_en" in name:
        return "en"
    sys.exit(f"Sprache in {pfad.name} nicht erkennbar (_de / _en im Namen).")


def verarbeite(pfad):
    sprache = sprache_aus_name(pfad)
    nachbarn = nachbarn_berechnen(LAYOUTS[sprache])
    df = pd.read_excel(pfad)
    ergebnisse = {s: df.copy() for s in STUFEN}
    for s in STUFEN:
        ergebnisse[s]["fehlerrate"] = s
        ergebnisse[s]["n_buchstaben"] = 0
        ergebnisse[s]["n_fehler"] = 0

    for i in df.index:
        rng = random.Random(f"{SEED}-{sprache}-{df.at[i, 'id']}")
        # Pool der veränderbaren Buchstabenpositionen
        pool = []
        for f in FELDER:
            pool += [(f, p) for p in erlaubte_positionen(str(df.at[i, f]), nachbarn)]
        rng.shuffle(pool)
        # Ersatzbuchstabe pro Position einmal festlegen -> 5 % ist Teilmenge von 15 %
        ersatz = {}
        for f, p in pool:
            ch = str(df.at[i, f])[p]
            neu = rng.choice(nachbarn[ch.lower()])
            ersatz[(f, p)] = neu.upper() if ch.isupper() else neu

        for s in STUFEN:
            n = round(s * len(pool))
            texte = {f: list(str(df.at[i, f])) for f in FELDER}
            for f, p in pool[:n]:
                texte[f][p] = ersatz[(f, p)]
            for f in FELDER:
                ergebnisse[s].at[i, f] = "".join(texte[f])
            ergebnisse[s].at[i, "n_buchstaben"] = len(pool)
            ergebnisse[s].at[i, "n_fehler"] = n

    for s in STUFEN:
        ziel = pfad.with_name(f"{pfad.stem}_tippfehler{round(s * 100):02d}.xlsx")
        ergebnisse[s].to_excel(ziel, index=False)
        e = ergebnisse[s]
        print(f"{ziel.name}: {int(e.n_fehler.sum())} Fehler auf {int(e.n_buchstaben.sum())} "
              f"Buchstaben ({e.n_fehler.sum() / e.n_buchstaben.sum():.1%}), "
              f"im Schnitt {e.n_fehler.mean():.1f} pro Frage")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Aufruf: python tippfehler_einbauen.py <datei_de.xlsx> [<datei_en.xlsx> ...]")
    for arg in sys.argv[1:]:
        verarbeite(Path(arg))
