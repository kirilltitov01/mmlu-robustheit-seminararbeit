"""
Übersetzt die gezogene MMLU-Stichprobe (Englisch) mit der DeepL-API ins Deutsche
und speichert das Ergebnis als eigene Excel-Datei.

Vorher einmalig:
    pip install deepl pandas openpyxl

API-Key als Umgebungsvariable setzen (nicht ins Skript schreiben!):
    macOS/Linux:  export DEEPL_API_KEY="euer-key"
    Windows:      set DEEPL_API_KEY=euer-key

Aufruf:
    python uebersetzen.py mmlu_auswahl_en.xlsx mmlu_auswahl_de.xlsx

"""
import os
import sys

import deepl
import pandas as pd

ZU_UEBERSETZEN = ["question", "A", "B", "C", "D"]

eingabe = sys.argv[1] if len(sys.argv) > 1 else "mmlu_auswahl_en.xlsx"
ausgabe = sys.argv[2] if len(sys.argv) > 2 else "mmlu_auswahl_de.xlsx"
testlauf = "--test" in sys.argv

api_key = os.environ.get("DEEPL_API_KEY")
if not api_key:
    sys.exit("Kein API-Key gefunden. Bitte DEEPL_API_KEY als Umgebungsvariable setzen.")

translator = deepl.DeepLClient(api_key)

df = pd.read_excel(eingabe)
if testlauf:
    df = df.head(5)

# Zeichenzahl vorab prüfen
zeichen = sum(df[c].astype(str).str.len().sum() for c in ZU_UEBERSETZEN)
nutzung = translator.get_usage()
print(f"Zu übersetzen: {zeichen:,} Zeichen")
if nutzung.character.valid:
    rest = nutzung.character.limit - nutzung.character.count
    print(f"Noch frei im Kontingent: {rest:,} Zeichen")
    if zeichen > rest:
        sys.exit("Nicht genug Kontingent übrig - Abbruch.")

de = df.copy()
for spalte in ZU_UEBERSETZEN:
    texte = df[spalte].astype(str).tolist()
    uebersetzt = []
    # In Paketen zu 25 Texten senden (DeepL begrenzt Anzahl und Größe pro Anfrage).
    # Jede Frage/Option bleibt dabei ein eigener Text.
    for start in range(0, len(texte), 25):
        ergebnisse = translator.translate_text(
            texte[start:start + 25],
            source_lang="EN",
            target_lang="DE",
            preserve_formatting=True,  # Zeilenumbrüche/Satzzeichen nicht verändern
        )
        uebersetzt += [r.text for r in ergebnisse]
    de[spalte] = uebersetzt
    print(f"Spalte '{spalte}' übersetzt")

# id, subject, answer und answer_letter bleiben unverändert aus dem Original
de.to_excel(ausgabe, index=False)
print(f"{len(de)} Fragen gespeichert in {ausgabe}")
