"""
Zieht aus dem zusammengeführten MMLU-Datensatz pro Fach 50 zufällige Fragen
(fester Seed -> reproduzierbar) und speichert sie als neue Excel-Datei.

Aufruf:
    python stichprobe_ziehen.py Datensätze_merged.xlsx mmlu_auswahl_en.xlsx
"""
import json
import sys

import pandas as pd

SEED = 42            # fester Seed: gleiche Auswahl bei jedem Durchlauf
N_PRO_FACH = 50

eingabe = sys.argv[1] if len(sys.argv) > 1 else "Datensätze_merged.xlsx"
ausgabe = sys.argv[2] if len(sys.argv) > 2 else "mmlu_auswahl_en.xlsx"

df = pd.read_excel(eingabe)

# Ursprüngliche Zeilennummer als feste ID behalten (wichtig für die Zuordnung EN <-> DE)
df.insert(0, "id", df.index)

# Pro Fach 50 Fragen ziehen
auswahl = (
    df.groupby("subject", group_keys=False)
      .sample(n=N_PRO_FACH, random_state=SEED)
      .sort_values(["subject", "id"])
      .reset_index(drop=True)
)

# Antwortoptionen aus der JSON-Liste in eigene Spalten A-D aufteilen
optionen = auswahl["choices"].apply(json.loads)
for i, buchstabe in enumerate("ABCD"):
    auswahl[buchstabe] = optionen.str[i]

# Lösung zusätzlich als Buchstaben (0->A, 1->B, ...)
auswahl["answer_letter"] = auswahl["answer"].map(lambda i: "ABCD"[i])

auswahl = auswahl[["id", "subject", "question", "A", "B", "C", "D",
                   "answer", "answer_letter"]]
auswahl.to_excel(ausgabe, index=False)

print(f"{len(auswahl)} Fragen gespeichert in {ausgabe}")
print(auswahl["subject"].value_counts().to_string())
