"""Classe le vivier : signal ListenBrainz dispo vs mis de côté (sans retirer).

Sonde POST /1/popularity/artist (totaux all-time, proxy « on peut choper des
écoutes »). Un artiste est OK s'il a un MBID perso ou un groupe rattaché avec
total_listen_count > 0. Sinon → data/census/fantasy_listen_aside.json.

Usage :
  python tools/probe_listenbrainz_coverage.py
  python tools/probe_listenbrainz_coverage.py --limit 200   # smoke test
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "census"
UA = "fantasy-music/0.1 (coverage probe; local dataset)"
BATCH = 500
SLEEP = 1.05

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def post_popularity(mbids: list[str]) -> list[dict]:
    body = json.dumps({"artist_mbids": mbids}).encode()
    req = urllib.request.Request(
        "https://api.listenbrainz.org/1/popularity/artist",
        data=body,
        headers={
            "User-Agent": UA,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def fetch_all(mbids: list[str]) -> dict[str, int | None]:
    out: dict[str, int | None] = {}
    total = len(mbids)
    for i in range(0, total, BATCH):
        batch = mbids[i:i + BATCH]
        for attempt in range(4):
            try:
                rows = post_popularity(batch)
                break
            except urllib.error.HTTPError as exc:
                if exc.code in (429, 503) and attempt < 3:
                    time.sleep(5 * (attempt + 1))
                    continue
                raise
        for row in rows:
            mbid = row.get("artist_mbid")
            if not mbid:
                continue
            out[mbid] = row.get("total_listen_count")
        print(f"  popularity {min(i + BATCH, total)}/{total}", flush=True)
        time.sleep(SLEEP)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="limiter le vivier (test)")
    args = ap.parse_args()

    eligible = json.loads((OUT / "eligible.json").read_text(encoding="utf-8"))
    mb = json.loads((OUT / "musicbrainz.json").read_text(encoding="utf-8"))
    if args.limit:
        eligible = eligible[: args.limit]

    credits: set[str] = set()
    for rec in eligible:
        info = mb.get(rec["qid"]) or {}
        if info.get("mbid"):
            credits.add(info["mbid"])
        for g in info.get("groups") or []:
            if g.get("mbid"):
                credits.add(g["mbid"])

    credit_list = sorted(credits)
    print(f"{len(eligible)} éligibles  {len(credit_list)} MBID crédit à sonder", flush=True)
    counts = fetch_all(credit_list)

    aside: list[dict] = []
    ok_n = 0
    for rec in eligible:
        qid = rec["qid"]
        info = mb.get(qid) or {}
        personal = info.get("mbid")
        groups = [g.get("mbid") for g in (info.get("groups") or []) if g.get("mbid")]
        # uniques
        seen: set[str] = set()
        group_u: list[str] = []
        for g in groups:
            if g not in seen:
                seen.add(g)
                group_u.append(g)

        if not personal:
            aside.append({
                "qid": qid,
                "reason": "no_mbid",
                "mbid": None,
                "groups": [],
            })
            continue

        pers_n = counts.get(personal)
        hit_groups = [g for g in group_u if (counts.get(g) or 0) > 0]
        if (pers_n or 0) > 0 or hit_groups:
            ok_n += 1
            continue

        aside.append({
            "qid": qid,
            "reason": "no_lb_signal",
            "mbid": personal,
            "personal_listens": pers_n,
            "groups_checked": len(group_u),
            "groups": group_u[:12],
        })

    payload = {
        "version": 1,
        "comment": (
            "Artistes du vivier sans signal ListenBrainz (popularité all-time "
            "perso + groupes). Restent dans eligible.json ; exclus du pool "
            "Fantasy écoutes jusqu'à autre source / re-probe."
        ),
        "source": "listenbrainz_popularity_all_time",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "eligible_scanned": len(eligible),
        "credit_mbids_probed": len(credit_list),
        "counts": {
            "ok": ok_n,
            "aside": len(aside),
            "aside_no_mbid": sum(1 for a in aside if a["reason"] == "no_mbid"),
            "aside_no_signal": sum(1 for a in aside if a["reason"] == "no_lb_signal"),
        },
        "aside": aside,
    }
    dest = OUT / "fantasy_listen_aside.json"
    dest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"OK={ok_n}  aside={len(aside)} "
        f"(no_mbid={payload['counts']['aside_no_mbid']}, "
        f"no_signal={payload['counts']['aside_no_signal']})",
        flush=True,
    )
    print(f"Écrit : {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
