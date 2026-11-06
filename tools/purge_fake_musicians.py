"""Retire du vivier les faux musiciens (célébrités à signal musical faible).

Ne touche pas à eligible « pour toujours » sans trace : les QID partent dans
`artist_exclude` + `data/census/fake_musicians_purged.json`.

Règle (après occupations WD + musicbrainz.json) :
  - déjà dans artist_exclude → out
  - monarque / souverain → out
  - occupation célébrité (acteur, mannequin, politicien, écrivain, sportif…)
    ET pas de métier musical « fort » (rappeur, DJ, auteur-compositeur…)
    ET pas d'artist_group_override
    ET albums studio perso < 8
    ET pas de membership de groupe daté ni ≥ 3 groupes
  → out

Les vraies stars taguées acteur (Beyoncé, Cher…) restent via albums ≥ 8.
Dave Grohl reste via artist_group_override (Foo Fighters).

Usage :
  python tools/purge_fake_musicians.py --dry-run
  python tools/purge_fake_musicians.py
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from census_vivier import CFG, SPARQL, fetch_json, qid_of  # noqa: E402
from score_vivier import FAMILY_LABEL, display_name  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = ROOT / "data" / "census"
BATCH = 150

HARD_VETO = {"Q116", "Q1097498"}  # monarch / ruler


def ensure_occupations(qids: list[str]) -> dict[str, list[str]]:
    path = OUT / "occupations.json"
    occ: dict[str, list[str]] = {}
    if path.exists():
        occ = json.loads(path.read_text(encoding="utf-8"))
    todo = [q for q in qids if q not in occ]
    if not todo:
        return occ
    print(f"Occupations manquantes : {len(todo)}", flush=True)
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        values = " ".join(f"wd:{q}" for q in batch)
        query = f"""
        SELECT ?item ?occ WHERE {{
          VALUES ?item {{ {values} }}
          ?item wdt:P106 ?occ .
        }}
        """
        body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
        data = fetch_json(SPARQL, f"sparql_purge_occ_{batch[0]}_{len(batch)}", data=body)
        for row in (data or {}).get("results", {}).get("bindings", []):
            qid = qid_of(row.get("item", {}).get("value", ""))
            oid = qid_of(row.get("occ", {}).get("value", ""))
            if qid.startswith("Q") and oid.startswith("Q"):
                occ.setdefault(qid, [])
                if oid not in occ[qid]:
                    occ[qid].append(oid)
        for q in batch:
            occ.setdefault(q, [])
        print(f"  occ {min(i + BATCH, len(todo))}/{len(todo)}", flush=True)
        time.sleep(1.15)
    path.write_text(json.dumps(occ), encoding="utf-8")
    return occ


def has_band_signal(info: dict) -> bool:
    groups = info.get("groups") or []
    if len(groups) >= 3:
        return True
    return any(g.get("start") for g in groups)


def is_fake(
    qid: str,
    occupations: list[str],
    info: dict,
    *,
    celeb: set[str],
    strong: set[str],
    exclude: set[str],
    group_override: set[str],
) -> tuple[bool, str | None]:
    occs = set(occupations or [])
    if qid in exclude:
        return True, "artist_exclude"
    if occs & HARD_VETO:
        return True, "monarch"
    if qid in group_override:
        return False, None
    if not (occs & celeb):
        return False, None
    if occs & strong:
        return False, None
    albums = int(info.get("albums") or 0)
    if albums >= 8:
        return False, None
    if has_band_signal(info):
        return False, None
    return True, "celeb_weak_music"


def rewrite_ranking(keep: set[str], titles: dict) -> int:
    scores = json.loads((OUT / "scores.json").read_text(encoding="utf-8"))
    scores = [r for r in scores if r.get("qid") in keep]
    scores.sort(key=lambda r: (-float(r.get("score_final") or 0), -int(r.get("sitelinks") or 0)))
    for i, r in enumerate(scores, 1):
        r["rank"] = i
    (OUT / "scores.json").write_text(json.dumps(scores, ensure_ascii=False), encoding="utf-8")

    path = ROOT / "docs" / "vivier-ranking.csv"
    lines = ["rank;name;family;silhouette;instrument;nationality"]
    for r in scores:
        qid = r["qid"]
        name = display_name(qid, titles)
        fam = FAMILY_LABEL.get(r.get("family") or "", r.get("family") or "")
        lines.append(
            f"{r['rank']};{name};{fam};{r.get('silhouette') or ''};"
            f"{r.get('instrument') or ''};{r.get('nationality') or ''}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(scores)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    celeb = set(CFG.get("celebrity_occupations") or [])
    # Liste étroite : chanteur/musicien/compositeur ne sauvent pas un acteur
    # à 2 albums (Seagal). Le census utilise strong_music_occupations (large).
    strong = set(
        CFG.get("purge_strong_music_occupations")
        or CFG.get("strong_music_occupations")
        or []
    )
    exclude = set(CFG.get("artist_exclude") or [])
    group_override = set(CFG.get("artist_group_override") or {})

    eligible = json.loads((OUT / "eligible.json").read_text(encoding="utf-8"))
    mb = json.loads((OUT / "musicbrainz.json").read_text(encoding="utf-8"))
    titles = {}
    tp = OUT / "qid_titles.json"
    if tp.exists():
        titles = json.loads(tp.read_text(encoding="utf-8"))

    occ = ensure_occupations([r["qid"] for r in eligible])

    purged: list[dict] = []
    kept: list[dict] = []
    reasons = Counter()
    for rec in eligible:
        qid = rec["qid"]
        fake, reason = is_fake(
            qid,
            occ.get(qid) or [],
            mb.get(qid) or {},
            celeb=celeb,
            strong=strong,
            exclude=exclude,
            group_override=group_override,
        )
        if fake:
            reasons[reason or "?"] += 1
            purged.append({
                "qid": qid,
                "reason": reason,
                "family": rec.get("family"),
                "sitelinks": rec.get("sitelinks"),
                "name": display_name(qid, titles),
                "albums": (mb.get(qid) or {}).get("albums"),
                "groups": len((mb.get(qid) or {}).get("groups") or []),
            })
        else:
            kept.append(rec)

    print(f"Vivier {len(eligible)} → garder {len(kept)}  purger {len(purged)}")
    print("Raisons :", dict(reasons))
    print("Top sitelinks purgés :")
    for row in sorted(purged, key=lambda r: -int(r.get("sitelinks") or 0))[:25]:
        print(
            f"  {row['sitelinks']:>4} {row.get('family'):<8} "
            f"alb={row.get('albums')} g={row.get('groups')} "
            f"{row['name']} ({row['qid']}) {row['reason']}"
        )

    if args.dry_run:
        print("Dry-run : aucune écriture")
        return 0

    report = {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "before": len(eligible),
        "after": len(kept),
        "purged_n": len(purged),
        "reasons": dict(reasons),
        "purged": purged,
    }
    (OUT / "fake_musicians_purged.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    (OUT / "eligible.json").write_text(
        json.dumps(kept, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    keep_q = {r["qid"] for r in kept}
    if (OUT / "scores.json").exists():
        n = rewrite_ranking(keep_q, titles)
        print(f"scores + vivier-ranking : {n}")

    aside_path = OUT / "fantasy_listen_aside.json"
    if aside_path.exists():
        aside = json.loads(aside_path.read_text(encoding="utf-8"))
        before_a = len(aside.get("aside") or [])
        aside["aside"] = [a for a in (aside.get("aside") or []) if a.get("qid") in keep_q]
        aside["counts"] = {
            **(aside.get("counts") or {}),
            "aside": len(aside["aside"]),
            "eligible_after_purge": len(kept),
        }
        aside_path.write_text(json.dumps(aside, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"fantasy_listen_aside : {before_a} → {len(aside['aside'])}")

    print("Écrit : eligible.json, fake_musicians_purged.json (+ scores/ranking/aside)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
