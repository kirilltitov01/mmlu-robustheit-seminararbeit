# Robustheit kleiner, lokal betriebener Sprachmodelle gegenüber Sprachwechsel und Tippfehlern
 
**Eine empirische Untersuchung mit MMLU**
 
Seminararbeit im Seminar *Recent Developments in AI and Foundation Models*
Universität Hamburg, Professur für Statistik mit Anwendung in der Betriebswirtschaftslehre (Prof. Dr. Martin Spindler)
Betreuung: Jan Teichert-Kluge
 
**Autoren:** Kirill Titov, Talip Dablan (M.Sc. Wirtschaftsingenieurwesen)
**Abgabe:** 27.11.2026
 
---
 
## Worum geht es?
 
Kleine Open-Weight-Sprachmodelle lassen sich lokal auf normaler Hardware betreiben. Für Unternehmen mit vertraulichen Daten ist das attraktiv. Bewertet werden solche Modelle aber meist auf sauberen, englischen Benchmarks. Echte Eingaben sehen anders aus: Sie sind oft auf Deutsch und enthalten Tippfehler.
 
**Forschungsfrage:** Wie robust sind kleine, lokal betriebene Sprachmodelle gegenüber einem Sprachwechsel und gegenüber Tippfehlern?
 
Dazu haben wir 250 MMLU-Fragen (5 Fächer × 50) auf Deutsch und Englisch mit drei Tippfehlerstufen (0 %, 5 %, 15 %) an drei Modelle gestellt. Für ein Modell gab es zusätzlich einen Durchlauf mit Reasoning. Insgesamt sind das 6.000 ausgewertete Antworten.
 
| Modell | Format | Reasoning |
|---|---|---|
| Gemma 4 E2B (`google/gemma-4-e2b`) | MLX, 4 Bit | ohne und mit (zweiter Durchlauf) |
| Nemotron 3 Nano 4B (`nvidia/nemotron-3-nano-4b`) | GGUF, Q4_K_M | deaktiviert |
| Qwen3-VL 4B (`qwen/qwen3-vl-4b`) | MLX, 4 Bit | – (Instruct-Variante) |
 
## Zentrale Ergebnisse
 
- **Spracheffekt (H1 bestätigt):** Auf Deutsch beantworten die Modelle im Mittel 9,2 Prozentpunkte weniger Fragen richtig als auf Englisch.
- **Tippfehlereffekt (H2 bestätigt):** 15 % Tippfehler senken die Genauigkeit um 9,6 pp (DE) bzw. 12,8 pp (EN).
- **Keine Wechselwirkung (H3 nicht bestätigt):** Deutsch reagiert nicht stärker auf Tippfehler als Englisch. Wie robust ein System ist, hängt stärker vom Modell ab als von der Sprache.
- **Reasoning:** Mit Reasoning steigt die Genauigkeit von Gemma 4 E2B um rund 22 pp und erreicht das Niveau des größeren Qwen-Modells. Die Laufzeit pro Frage steigt dabei etwa um den Faktor 80.
Details, statistische Tests und Diskussion stehen in der Arbeit selbst (`latex/`).
 
## Aufbau des Repositorys
 
```
Daten/     Stichprobe (EN/DE), Tippfehler-Fassungen und Ergebnisdateien (Excel)
Python/    Skripte für Ziehung, Übersetzung, Tippfehler, Prüfung und Modellabfrage
latex/     LaTeX-Quelltext der Arbeit, Literaturverzeichnis (BibTeX) und Abbildungen
```
 
## Ablauf der Versuchsdurchführung
 
Die Skripte bauen aufeinander auf und werden in dieser Reihenfolge ausgeführt:
 
| Schritt | Skript | Was passiert |
|---|---|---|
| 1 | `stichprobe_ziehen.py` | Zieht aus dem MMLU-Test-Split 50 Fragen je Fach (Seed 42) und teilt die Antwortoptionen in die Spalten A–D auf. |
| 2 | `uebersetzen.py` | Übersetzt Fragen und Antwortoptionen feldweise mit der DeepL-API ins Deutsche (durchgeführt am 22.11.2026). Danach wurde die Übersetzung manuell geprüft und korrigiert. |
| 3 | `tippfehler_einbauen.py` | Erzeugt die Stufen 5 % und 15 %: Buchstaben im Fragetext werden durch eine Nachbartaste ersetzt (QWERTZ für Deutsch, QWERTY für Englisch). Die 5-%-Fehler sind eine Teilmenge der 15-%-Fehler. |
| 4 | `pruefen.py` | Kontrolliert die erzeugten Tippfehler: nur zulässige Stellen und echte Nachbartasten, richtige Fehlerzahl, Teilmengen-Eigenschaft, identische Fragen über alle Modelle. |
| 5 | `mmlu_an_llm.py` | Stellt jede Frage einzeln über die API von LM Studio, liest den Antwortbuchstaben aus und bewertet ihn. Das Skript kann abgebrochen und fortgesetzt werden. |
 
Die Auswertung (Genauigkeiten, Konfidenzintervalle, Binomialtest, exakter McNemar-Test, gepaarter t-Test) erfolgte anschließend in Microsoft Excel mit Tabellenformeln.
 
### Beispielaufrufe
 
```bash
python stichprobe_ziehen.py Datensätze_merged.xlsx mmlu_auswahl_en.xlsx
python uebersetzen.py mmlu_auswahl_en.xlsx mmlu_auswahl_de.xlsx
python tippfehler_einbauen.py mmlu_auswahl_de.xlsx mmlu_auswahl_en.xlsx
python mmlu_an_llm.py mmlu_auswahl_de_tippfehler15.xlsx
```
 
`mmlu_an_llm.py` erkennt die Sprache am Dateinamen (`_de` / `_en`). Modell, Temperatur, Token-Limit und Seed werden oben im Skript eingestellt.
 
## Voraussetzungen
 
**Software, mit der die Ergebnisse erzeugt wurden:**
 
- Python 3.9.6
- pandas 2.3.3, openpyxl 3.1.5, openai 2.48.0, deepl 1.33.0
- LM Studio 0.4.26 (Build 4)
- macOS 26.6.2 auf einem MacBook Air M1 mit 8 GB Arbeitsspeicher
- Microsoft Excel für Mac 16.115.2
**Installation der Pakete:**
 
```bash
pip install pandas==2.3.3 openpyxl==3.1.5 openai==2.48.0 deepl==1.33.0
```
 
**DeepL-API-Key** (nur für `uebersetzen.py`): Der Key wird aus einer Umgebungsvariable gelesen und steht nicht im Code.
 
```bash
export DEEPL_API_KEY="euer-key"
```
 
**LM Studio:** Die Modelle über den Modellkatalog von LM Studio laden und den lokalen Server starten (Standard: `http://localhost:1234/v1`).
 
## Einstellungen der Modellabfrage
 
- Temperatur 0, Seed 42
- Token-Limit: 2 ohne Reasoning, 2.000 mit Reasoning
- Reasoning über die Modelleinstellungen in LM Studio ein- bzw. ausgeschaltet
- Systemanweisung und Prompt in der Sprache der Frage, fehlerfrei; Tippfehler stehen nur im Fragetext, nicht in den Antwortoptionen
Der genaue Wortlaut der Prompts steht in `mmlu_an_llm.py` und in Anhang B der Arbeit.
 
## Datengrundlage
 
Die Fragen stammen aus dem Benchmark **MMLU** (Massive Multitask Language Understanding), Datensatz [`cais/mmlu`](https://huggingface.co/datasets/cais/mmlu) auf Hugging Face, Test-Split, Commit `c30699e8356da336a370243923dbaf21066bb9fe`. Verwendete Fächer: High School Biology, Geography, Microeconomics, Physics und World History.
 
> Hendrycks, D., Burns, C., Basart, S., Zou, A., Mazeika, M., Song, D. & Steinhardt, J. (2021). Measuring Massive Multitask Language Understanding. *International Conference on Learning Representations (ICLR 2021).*
 
MMLU steht unter der MIT-Lizenz. Die deutsche Übersetzung und die Tippfehler-Fassungen haben wir selbst erzeugt.
 
## Grenzen
 
Die Stichprobe ist mit 250 Fragen klein (50 je Fach). Es gab nur einen deterministischen Durchlauf pro Bedingung. Simuliert wurde nur ein Fehlertyp (Nachbartaste), und die deutsche Fassung ist eine korrigierte maschinelle Übersetzung. Mehr dazu in Abschnitt 4.4 der Arbeit.
