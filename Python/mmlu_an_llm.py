"""
Schickt die MMLU-Fragen (Frage + Antwortoptionen A-D) aus einer Excel-Datei
nacheinander an ein lokales LLM in LM Studio, liest den Antwortbuchstaben aus
und prüft, ob er richtig ist.

Erwartete Eingabe-Spalten (wie mmlu_auswahl_de.xlsx / mmlu_auswahl_en.xlsx):
  id, subject, question, A, B, C, D, answer, answer_letter

Ausgabe: eine NEUE Excel-Datei (die Eingabe bleibt unverändert) mit zusätzlich:
  prompt, antwort_roh, antwort_buchstabe, korrekt, modell, temperature,
  sprache, zeitstempel, dauer_s

Das Skript kann abgebrochen und neu gestartet werden: Fragen, die in der
Ausgabedatei schon eine Antwort haben, werden übersprungen.

Aufruf:
    python mmlu_an_llm.py mmlu_auswahl_de.xlsx
    python mmlu_an_llm.py mmlu_auswahl_en.xlsx ergebnisse_en_gemma.xlsx
"""

import re
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from openai import OpenAI

# ======================= EINSTELLUNGEN =======================
MODELL = "google/gemma-4-e2b_reasoning"     # None = automatisch; sonst exakter Name aus LM Studio - qwen/qwen3-vl-4b, google/gemma-4-e2b, nvidia/nemotron-3-nano-4b
SPRACHE = None                    # None = automatisch aus Dateiname (_de / _en), sonst "de" oder "en"
TEMPERATURE = 0.0
MAX_TOKENS = 2                   # reicht für "B"; bei Modellen mit <think> (z. B. Qwen3) deutlich erhöhen, z. B. 1024
SEED = 42

ENTFERNE_THINK = True             # entfernt <think>...</think>
SPEICHERN_ALLE = 5                # nach wie vielen Antworten gespeichert wird
UEBERSCHREIBEN = False            # True = vorhandene Antworten neu erzeugen

BASE_URL = "http://localhost:1234/v1"
# =============================================================

# Anweisungen in der Sprache der Frage. Für alle Modelle und alle Fehlerstufen gleich lassen!
VORLAGEN = {
    "de": {
        "system": "Du bist ein hilfreicher Assistent. Du beantwortest Multiple-Choice-Fragen.",
        "prompt": ("Beantworte die folgende Multiple-Choice-Frage. Antworte ausschließlich mit dem "
                   "Buchstaben der richtigen Antwort (A, B, C oder D), ohne Erklärung.\n\n"
                   "Frage: {question}\n\nA) {A}\nB) {B}\nC) {C}\nD) {D}\n\nAntwort:"),
    },
    "en": {
        "system": "You are a helpful assistant. You answer multiple-choice questions.",
        "prompt": ("Answer the following multiple-choice question. Respond only with the letter "
                   "of the correct answer (A, B, C, or D), without explanation.\n\n"
                   "Question: {question}\n\nA) {A}\nB) {B}\nC) {C}\nD) {D}\n\nAnswer:"),
    },
}

client = OpenAI(base_url=BASE_URL, api_key="lm-studio")  # Key wird lokal nicht geprüft


def modell_bestimmen():
    try:
        modelle = [m.id for m in client.models.list().data]
    except Exception as e:
        sys.exit(f"Keine Verbindung zu LM Studio ({BASE_URL}).\nLäuft der Server? Fehler: {e}")
    if MODELL:
        return MODELL
    if len(modelle) == 1:
        return modelle[0]
    print("Mehrere Modelle gefunden. Bitte eines oben bei MODELL eintragen:")
    for m in modelle:
        print("  -", m)
    sys.exit(1)


def sprache_bestimmen(pfad):
    if SPRACHE:
        return SPRACHE
    name = pfad.stem.lower()
    if "_de" in name:
        return "de"
    if "_en" in name:
        return "en"
    sys.exit("Sprache nicht erkennbar. Bitte oben SPRACHE = 'de' oder 'en' setzen.")


def buchstabe_auslesen(text):
    """Liest A/B/C/D aus der Modellantwort. Gibt None zurück, wenn nicht eindeutig."""
    t = text.strip().replace("*", "")
    # 1) Antwort beginnt mit dem Buchstaben: "B", "B)", "B.", "B: ...", "(B)"
    m = re.match(r"^\(?([ABCD])(?:[).:]|\s*$)", t)
    if m:
        return m.group(1)
    # 2) "Antwort: B" / "Answer: B" / "Die richtige Antwort ist B"
    m = re.search(r"(?:antwort|answer)\s*(?:ist|is)?\s*:?\s*\(?([ABCD])\b", t, flags=re.IGNORECASE)
    if m:
        return m.group(1).upper()
    # 3) genau ein einzelner Buchstabe A-D im Text, z. B. "Option C"
    treffer = set(re.findall(r"(?<![A-Za-zÄÖÜäöü])([ABCD])(?![A-Za-zÄÖÜäöü])", t))
    if len(treffer) == 1:
        return treffer.pop()
    return None


def frage_modell(modell, system, prompt):
    antwort = client.chat.completions.create(
        model=modell,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": prompt}],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        seed=SEED,
    )
    text = antwort.choices[0].message.content or ""
    if ENTFERNE_THINK:
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    return text


def speichern(df, pfad):
    while True:
        try:
            df.to_excel(pfad, index=False)
            return
        except PermissionError:
            input("Datei ist gesperrt (in Excel geöffnet?). Bitte schließen und Enter drücken ...")


def main():
    if len(sys.argv) < 2:
        sys.exit("Aufruf: python mmlu_an_llm.py <eingabe.xlsx> [ausgabe.xlsx]")
    eingabe = Path(sys.argv[1])
    if not eingabe.exists():
        sys.exit(f"Datei nicht gefunden: {eingabe.resolve()}")

    modell = modell_bestimmen()
    sprache = sprache_bestimmen(eingabe)
    vorlage = VORLAGEN[sprache]
    modell_kurz = re.sub(r"[^A-Za-z0-9.-]+", "-", modell.split("/")[-1])
    ausgabe = Path(sys.argv[2]) if len(sys.argv) > 2 else \
        eingabe.with_name(f"ergebnisse_{eingabe.stem}_{modell_kurz}.xlsx")
    print(f"Modell: {modell} | Sprache: {sprache} | Ausgabe: {ausgabe}")

    # Fortsetzen, falls die Ausgabedatei schon existiert
    if ausgabe.exists():
        df = pd.read_excel(ausgabe)
    else:
        df = pd.read_excel(eingabe)
        for spalte in ["prompt", "antwort_roh", "antwort_buchstabe", "korrekt",
                       "modell", "temperature", "sprache", "zeitstempel", "dauer_s"]:
            df[spalte] = None
    df = df.astype({"prompt": object, "antwort_roh": object, "antwort_buchstabe": object,
                    "modell": object, "sprache": object, "zeitstempel": object})

    seit_speichern = 0
    for i in df.index:
        vorhanden = df.at[i, "antwort_roh"]
        if pd.notna(vorhanden) and not UEBERSCHREIBEN and not str(vorhanden).startswith("FEHLER"):
            continue

        zeile = df.loc[i]
        prompt = vorlage["prompt"].format(question=zeile["question"], A=zeile["A"],
                                          B=zeile["B"], C=zeile["C"], D=zeile["D"])
        print(f"[{i + 1}/{len(df)}] id {zeile['id']} ...", end=" ", flush=True)
        start = time.time()
        try:
            text = frage_modell(modell, vorlage["system"], prompt)
        except Exception as e:
            text = f"FEHLER: {e}"
        dauer = round(time.time() - start, 1)

        buchstabe = None if text.startswith("FEHLER") else buchstabe_auslesen(text)
        korrekt = None if buchstabe is None else int(buchstabe == zeile["answer_letter"])
        print(f"{buchstabe or '?'} (richtig: {zeile['answer_letter']}) {dauer}s")

        df.at[i, "prompt"] = prompt
        df.at[i, "antwort_roh"] = text
        df.at[i, "antwort_buchstabe"] = buchstabe
        df.at[i, "korrekt"] = korrekt
        df.at[i, "modell"] = modell
        df.at[i, "temperature"] = TEMPERATURE
        df.at[i, "sprache"] = sprache
        df.at[i, "zeitstempel"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df.at[i, "dauer_s"] = dauer

        seit_speichern += 1
        if seit_speichern >= SPEICHERN_ALLE:
            speichern(df, ausgabe)
            seit_speichern = 0

    speichern(df, ausgabe)

    # Kurze Zusammenfassung
    k = pd.to_numeric(df["korrekt"], errors="coerce")
    print(f"\nFertig. Ergebnisse in {ausgabe.resolve()}")
    print(f"Genauigkeit gesamt: {k.fillna(0).mean():.1%}  "
          f"(nicht auswertbare Antworten: {int(k.isna().sum())}, zählen als falsch)")
    print(df.assign(k=k.fillna(0)).groupby("subject")["k"].mean().map("{:.1%}".format).to_string())


if __name__ == "__main__":
    main()
