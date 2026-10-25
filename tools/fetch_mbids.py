"""MBID MusicBrainz (P434) des éligibles, par lots SPARQL."""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from census_vivier import SPARQL, fetch_json, qid_of  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = ROOT / "data" / "census"
BATCH = 150


def main() -> int:
    dest = OUT / "mbids.json"
    eligible = json.loads((OUT / "eligible.json").read_text(encoding="utf-8"))
    all_qids = [r["qid"] for r in eligible]
    mapping: dict[str, str] = {}
    if dest.exists():
        mapping = json.loads(dest.read_text(encoding="utf-8"))
        print(f"reprise : {len(mapping)} MBID déjà là", flush=True)
    todo = [q for q in all_qids if q not in mapping]
    if not todo:
        print(f"Déjà complet : {len(mapping)}/{len(all_qids)}", flush=True)
        return 0
    print(f"{len(todo)} à aller chercher ({len(all_qids)} éligibles)", flush=True)
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        values = " ".join(f"wd:{q}" for q in batch)
        query = f"""
        SELECT ?item ?mbid WHERE {{
          VALUES ?item {{ {values} }}
          ?item wdt:P434 ?mbid .
        }}
        """
        body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
        data = fetch_json(SPARQL, f"sparql_mbid_{batch[0]}_{batch[-1]}_{len(batch)}", data=body)
        for row in (data or {}).get("results", {}).get("bindings", []):
            qid = qid_of(row.get("item", {}).get("value", ""))
            mbid = row.get("mbid", {}).get("value", "")
            if qid.startswith("Q") and mbid:
                mapping[qid] = mbid
        print(f"  {min(i + BATCH, len(todo))}/{len(todo)}  {len(mapping)} MBID", flush=True)
        if (i // BATCH) % 10 == 9:
            dest.write_text(json.dumps(mapping), encoding="utf-8")
        time.sleep(1.2)
    dest.write_text(json.dumps(mapping), encoding="utf-8")
    print(f"{len(mapping)}/{len(all_qids)} avec P434 → {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
