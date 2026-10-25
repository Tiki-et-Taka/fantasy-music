"""Richesse Wikidata : statements + identifiants + récompenses P166."""

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
BATCH = 80


def main() -> int:
    dest = OUT / "wikidata_richness.json"
    qids = [r["qid"] for r in json.loads((OUT / "eligible.json").read_text(encoding="utf-8"))]
    out: dict[str, dict] = {}
    if dest.exists():
        out = json.loads(dest.read_text(encoding="utf-8"))
        print(f"reprise : {len(out)} déjà là", flush=True)
        if len(out) >= len(qids):
            print(f"Déjà complet : {len(out)} fiches", flush=True)
            return 0
    todo = [q for q in qids if q not in out]
    print(f"{len(todo)} à aller chercher ({len(qids)} éligibles)", flush=True)
    qids = todo
    for i in range(0, len(qids), BATCH):
        batch = qids[i:i + BATCH]
        values = " ".join(f"wd:{q}" for q in batch)
        query = f"""
        SELECT ?item ?st ?ids (COUNT(DISTINCT ?award) AS ?awards) WHERE {{
          VALUES ?item {{ {values} }}
          ?item wikibase:statements ?st .
          OPTIONAL {{ ?item wikibase:identifiers ?ids }}
          OPTIONAL {{ ?item wdt:P166 ?award }}
        }}
        GROUP BY ?item ?st ?ids
        """
        body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
        data = fetch_json(SPARQL, f"sparql_rich_{batch[0]}_{batch[-1]}_{len(batch)}", data=body)
        for row in (data or {}).get("results", {}).get("bindings", []):
            qid = qid_of(row.get("item", {}).get("value", ""))
            if not qid.startswith("Q"):
                continue
            st = int(float(row.get("st", {}).get("value") or 0))
            ids = int(float(row.get("ids", {}).get("value") or 0))
            awards = int(float(row.get("awards", {}).get("value") or 0))
            out[qid] = {
                "statements": st,
                "identifiers": ids,
                "awards": awards,
                "richesse": st + ids + awards,
            }
        print(f"  {min(i + BATCH, len(qids))}/{len(qids)}  {len(out)}", flush=True)
        if (i // BATCH) % 20 == 19:
            dest.write_text(json.dumps(out), encoding="utf-8")
        time.sleep(1.2)
    dest.write_text(json.dumps(out), encoding="utf-8")
    print(f"{len(out)}/{len(qids)} → {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
