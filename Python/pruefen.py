import re, sys
import pandas as pd
X = pd.ExcelFile(sys.argv[1])
LAY = {"DE": ["qwertzuiopü", "asdfghjklöä", "yxcvbnm"], "EN": ["qwertyuiop", "asdfghjkl", "zxcvbnm"]}
def nachbarn(rows):
    nb = {}
    for r, row in enumerate(rows):
        for i, k in enumerate(row):
            c = set()
            if i > 0: c.add(row[i-1])
            if i < len(row)-1: c.add(row[i+1])
            if r > 0: c |= {rows[r-1][j] for j in (i, i+1) if j < len(rows[r-1])}
            if r < len(rows)-1: c |= {rows[r+1][j] for j in (i-1, i) if 0 <= j < len(rows[r+1])}
            nb[k] = c
    return nb
WORT = re.compile(r"[A-Za-zÄÖÜäöüß]+"); SPERR = set("0123456789/^=+*·_")
def erlaubt(t, nb):
    pos = set()
    for m in WORT.finditer(t):
        w = m.group()
        if len(w) < 3 or w.isupper(): continue
        v = t[m.start()-1] if m.start() > 0 else " "; n = t[m.end()] if m.end() < len(t) else " "
        if v in SPERR or n in SPERR: continue
        pos |= {m.start()+k for k, ch in enumerate(w) if ch.lower() in nb}
    return pos
modelle = sorted({s.rsplit(" ", 2)[0] for s in X.sheet_names})
bericht = []; fragen15 = {}
for mod in modelle:
    for l in ["DE", "EN"]:
        o = X.parse(f"{mod} {l} 0%"); f5 = X.parse(f"{mod} {l} 5%"); f = X.parse(f"{mod} {l} 15%")
        nb = nachbarn(LAY[l]); prob = []
        stat = dict(fragen=0, fehler=0, erlaubt=0)
        if not (o.id.values == f.id.values).all(): prob.append("IDs ungleich")
        for c in ["A","B","C","D","answer","answer_letter"]:
            n = (o[c].astype(str) != f[c].astype(str)).sum()
            if n: prob.append(f"Spalte {c} in {n} Zeilen verändert")
        for i in o.index:
            q0, q, q5 = str(o.at[i,"question"]), str(f.at[i,"question"]), str(f5.at[i,"question"])
            if len(q0) != len(q): prob.append(f"id {o.at[i,'id']}: Länge geändert"); continue
            pos = erlaubt(q0, nb); diff = [p for p in range(len(q0)) if q0[p] != q[p]]
            stat["fragen"] += 1; stat["fehler"] += len(diff); stat["erlaubt"] += len(pos)
            for p in diff:
                a, b = q0[p], q[p]
                if p not in pos: prob.append(f"id {o.at[i,'id']}: verbotene Stelle {p} '{a}'->'{b}' in '{q0[max(0,p-15):p+15]}'")
                elif b.lower() not in nb[a.lower()]: prob.append(f"id {o.at[i,'id']}: '{a}'->'{b}' keine Nachbartaste")
                elif a.isupper() != b.isupper(): prob.append(f"id {o.at[i,'id']}: Groß/klein geändert '{a}'->'{b}'")
            soll = round(0.15 * len(pos))
            if len(diff) != soll: prob.append(f"id {o.at[i,'id']}: {len(diff)} Fehler statt {soll}")
            if int(f.at[i,"n_fehler"]) != len(diff) or int(f.at[i,"n_buchstaben"]) != len(pos): prob.append(f"id {o.at[i,'id']}: Zählspalten stimmen nicht")
            d5 = [p for p in range(len(q0)) if q0[p] != q5[p]]
            if any(q5[p] != q[p] for p in d5): prob.append(f"id {o.at[i,'id']}: 5 % nicht Teilmenge von 15 %")
            pr = str(f.at[i,"prompt"])
            if q not in pr or any(f"{c}) {f.at[i,c]}" not in pr for c in "ABCD"): prob.append(f"id {o.at[i,'id']}: Prompt passt nicht zur Frage")
            if str(o.at[i,"question"]) == q: prob.append(f"id {o.at[i,'id']}: keine Änderung")
        fragen15.setdefault(l, {})[mod] = f.question.tolist()
        bericht.append((mod, l, stat, prob))
for mod, l, s, p in bericht:
    print(f"{mod:24s} {l}: {s['fehler']} Fehler / {s['erlaubt']} erlaubte Buchstaben = {s['fehler']/s['erlaubt']:.2%}, Probleme: {len(p)}")
    for x in p[:10]: print("    ", x)
for l, d in fragen15.items():
    v = list(d.values()); print(l, "15-%-Fragen in allen Modellen identisch:", all(x == v[0] for x in v))
