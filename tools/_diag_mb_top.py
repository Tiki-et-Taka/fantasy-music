import json
from collections import Counter
from pathlib import Path

s = json.loads(Path("data/census/scores.json").read_text(encoding="utf-8"))
t = json.loads(Path("data/census/qid_titles.json").read_text(encoding="utf-8"))
by = {r["qid"]: r for r in s}
print("TOP 15")
for r in s[:15]:
    name = t.get(r["qid"], {}).get("en", r["qid"])
    print(
        f"{r['rank']:3} {name:<28} rg={r['release_groups']:<5} "
        f"{r.get('contrib_source')} {r['family']}"
    )
print()
print("contrib", Counter(r.get("contrib_source") for r in s))
print("mean rg", round(sum(r["release_groups"] for r in s) / len(s), 1))
watch = [
    ("Q2831", "Jackson"),
    ("Q303", "Elvis"),
    ("Q93341", "Miles"),
    ("Q174957", "Nina"),
    ("Q37793136", "Aya"),
    ("Q19848", "Gaga"),
]
for q, n in watch:
    r = by.get(q)
    if r:
        print(
            f"{n:<12} #{r['rank']:<5} rg={r['release_groups']:<5} "
            f"{r.get('contrib_source')} final={r['score_final']:.3f}"
        )
    else:
        print(n, "OUT")
