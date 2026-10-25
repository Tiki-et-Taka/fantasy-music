"""Recalcule le score de l'échantillon avec les pageviews du dump 2026-09.

Approximation du dénominateur : on n'a pas encore la médiane des musiciens par
édition, donc on normalise par √(V_w) où V_w est le trafic total Wikipedia.
L'ordre relatif reste comparable ; les centiles définitifs attendront les dumps
complémentaires + le pool de musiciens.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from validate_scoring import (  # noqa: E402
    LAMBDA,
    W_DISCO,
    W_SITELINKS,
    W_STATEMENTS,
    composite,
    enforce_band_monotonicity,
    get_entities,
    titles_to_qids,
    wikipedia_sitelinks,
    zscores,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    spec = json.loads((ROOT / "tools" / "reference_set.json").read_text(encoding="utf-8"))
    prev = json.loads((ROOT / "data" / "validation.json").read_text(encoding="utf-8"))
    views = json.loads((ROOT / "data" / "pageviews" / "2026-09" / "sample_views.json").read_text(encoding="utf-8"))
    totals = json.loads((ROOT / "data" / "pageviews" / "2026-09" / "wiki_totals.json").read_text(encoding="utf-8"))

    titles = [a["wiki"] for a in spec["artists"]] + list(spec["bands"].values())
    qids = titles_to_qids(titles)
    entities = get_entities(sorted(set(qids.values())))

    prev_by_name = {a["name"]: a for a in prev["artists"]}
    prev_bands = {b["name"]: b for b in prev["bands"]}

    def dump_score(label: str, wiki_title: str) -> tuple[float, float, dict[str, int]]:
        qid = qids.get(wiki_title)
        ent = entities.get(qid) if qid else None
        per_wiki: dict[str, int] = {}
        if ent:
            for code, page in wikipedia_sitelinks(ent).items():
                domain = f"{code}.wikipedia"
                hits = views.get(domain, {}).get(page.replace(" ", "_"), 0)
                if hits:
                    per_wiki[domain] = hits
        raw = sum(per_wiki.values())
        part = 0.0
        for domain, v in per_wiki.items():
            vw = totals.get(domain)
            if vw:
                part += math.sqrt(vw) * (v / vw)  # = v / √(V_w)
        return raw, part, per_wiki

    artists = []
    for item in spec["artists"]:
        old = prev_by_name.get(item["wiki"])
        if not old:
            continue
        raw, part, per_wiki = dump_score(item["wiki"], item["wiki"])
        rec = {
            "name": item["wiki"],
            "band_label": item["band"],
            "sitelinks": old["sitelinks"],
            "statements": old["statements"],
            "releases": old["releases"],
            "pageviews": part,  # composite() lit ce champ
            "pageviews_raw": raw,
            "per_wiki": per_wiki,
        }
        artists.append(rec)

    bands = []
    for label, wiki in spec["bands"].items():
        old = prev_bands.get(label)
        if not old:
            continue
        raw, part, per_wiki = dump_score(label, wiki)
        bands.append({
            "name": label,
            "sitelinks": old["sitelinks"],
            "statements": old["statements"],
            "releases": old["releases"],
            "pageviews": part,
            "pageviews_raw": raw,
        })

    pool = artists + bands
    # Pondérations 40/20/15/10/15 : on réécrit le composite localement.
    zp = zscores([r["pageviews"] for r in pool])
    zs = zscores([r["sitelinks"] for r in pool])
    zt = zscores([r["statements"] for r in pool])
    zd = zscores([r["releases"] for r in pool])
    # Entropie : -Σ p log p sur la répartition des vues, clampée ensuite.
    for r in artists:
        vals = list(r["per_wiki"].values())
        tot = sum(vals)
        if tot <= 0 or len(vals) < 2:
            r["entropy"] = 0.0
        else:
            r["entropy"] = -sum((v / tot) * math.log(v / tot) for v in vals if v)
    for r in bands:
        r["entropy"] = 0.0
    ze = zscores([r.get("entropy", 0.0) for r in pool])
    for i, r in enumerate(pool):
        r["score_perso"] = (
            0.40 * zp[i] + 0.20 * zs[i] + 0.15 * max(0.0, ze[i])
            + 0.10 * zt[i] + 0.15 * zd[i]
        )

    band_score = {b["name"]: b["score_perso"] for b in bands}
    for a in artists:
        bs = band_score.get(a["band_label"]) if a["band_label"] else None
        a["gain"] = LAMBDA * 0.6 * max(0.0, bs - a["score_perso"]) if bs is not None else 0.0
        a["score_final"] = a["score_perso"] + a["gain"]

    enforce_band_monotonicity(artists)
    artists.sort(key=lambda a: a["score_final"], reverse=True)
    old_rank = {a["name"]: a["rank"] for a in prev["artists"]}

    print(f"{'#':>3}  {'Artiste':<26} {'brut':>10} {'part':>8} {'old':>4} {'new':>4}  delta")
    print("=" * 80)
    focus = {"Aya Nakamura", "Miles Davis", "Nina Simone", "John Lennon",
             "Dave Mustaine", "Marilyn Manson", "Mike Portnoy", "James LaBrie"}
    for i, a in enumerate(artists, 1):
        a["rank"] = i
        d = (old_rank.get(a["name"]) or i) - i
        mark = f"{d:+d}" if d else " 0"
        line = (f"{i:>3}  {a['name'][:26]:<26} {int(a['pageviews_raw']):>10} "
                f"{a['pageviews']:>8.3f} {old_rank.get(a['name'], 0):>4} {i:>4}  {mark}")
        if a["name"] in focus or i <= 8 or i >= 35:
            print(line)

    print("\nAya Nakamura — top editions")
    aya = next(a for a in artists if a["name"] == "Aya Nakamura")
    for w, v in sorted(aya["per_wiki"].items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {w:<16} {v:>8}")
    print("\nMiles Davis — top editions")
    miles = next(a for a in artists if a["name"] == "Miles Davis")
    for w, v in sorted(miles["per_wiki"].items(), key=lambda kv: -kv[1])[:8]:
        print(f"  {w:<16} {v:>8}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
