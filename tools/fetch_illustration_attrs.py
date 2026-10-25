"""Sexe P21 + instrument P1303 pour rattacher une plaque d'illustration."""

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
    dest = OUT / "illustration_raw.json"
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
    for i in range(0, len(todo), BATCH):
        batch = todo[i:i + BATCH]
        values = " ".join(f"wd:{q}" for q in batch)
        query = f"""
        SELECT ?item ?sex ?instr WHERE {{
          VALUES ?item {{ {values} }}
          OPTIONAL {{ ?item wdt:P21 ?sex }}
          OPTIONAL {{ ?item wdt:P1303 ?instr }}
        }}
        """
        body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
        data = fetch_json(SPARQL, f"sparql_illu_{batch[0]}_{batch[-1]}_{len(batch)}", data=body)
        bucket: dict[str, dict] = {
            q: {"sex": [], "instruments": []} for q in batch
        }
        for row in (data or {}).get("results", {}).get("bindings", []):
            qid = qid_of(row.get("item", {}).get("value", ""))
            if qid not in bucket:
                continue
            sex = qid_of(row.get("sex", {}).get("value", ""))
            instr = qid_of(row.get("instr", {}).get("value", ""))
            if sex.startswith("Q") and sex not in bucket[qid]["sex"]:
                bucket[qid]["sex"].append(sex)
            if instr.startswith("Q") and instr not in bucket[qid]["instruments"]:
                bucket[qid]["instruments"].append(instr)
        out.update(bucket)
        print(f"  {min(i + BATCH, len(todo))}/{len(todo)}  {len(out)}", flush=True)
        if (i // BATCH) % 15 == 14:
            dest.write_text(json.dumps(out), encoding="utf-8")
        time.sleep(1.2)
    dest.write_text(json.dumps(out), encoding="utf-8")
    print(f"{len(out)}/{len(qids)} → {dest.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
