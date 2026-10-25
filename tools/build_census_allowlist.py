"""
Titres Wikipédia des 23 833 éligibles, pour refiltrer le dump de pageviews.

SPARQL par lots de 120 QID, 30 éditions. Relançable via le cache disque.
Écrit data/census/allowlist.json et data/title_allowlist.json (lu par l'ingest).
"""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from census_vivier import SPARQL, fetch_json, qid_of  # noqa: E402
from ingest_pageviews_dump import DEFAULT_WIKIS  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = ROOT / "data" / "census"
BATCH = 120
LANGS = sorted({w.split(".", 1)[0] for w in DEFAULT_WIKIS})


def sitelinks_batch(qids: list[str]) -> list[tuple[str, str, str]]:
    values = " ".join(f"wd:{q}" for q in qids)
    langs = " ".join(f'"{lang}"' for lang in LANGS)
    query = f"""
    SELECT ?item ?lang ?title WHERE {{
      VALUES ?item {{ {values} }}
      VALUES ?lang {{ {langs} }}
      ?article schema:about ?item ;
               schema:inLanguage ?lang ;
               schema:name ?title ;
               schema:isPartOf ?wiki .
      FILTER(CONTAINS(STR(?wiki), "wikipedia.org"))
    }}
    """
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    data = fetch_json(SPARQL, f"sitelinks_{qids[0]}_{qids[-1]}_{len(qids)}", data=body)
    rows = []
    for row in (data or {}).get("results", {}).get("bindings", []):
        qid = qid_of(row.get("item", {}).get("value", ""))
        lang = row.get("lang", {}).get("value", "")
        title = row.get("title", {}).get("value", "")
        if qid.startswith("Q") and lang and title:
            rows.append((qid, lang, title.replace(" ", "_")))
    return rows


def main() -> int:
    dest = OUT / "allowlist.json"
    map_path = OUT / "qid_titles.json"
    if dest.exists() and map_path.exists():
        print(f"Déjà là : {dest.relative_to(ROOT)}", flush=True)
        return 0

    eligible = json.loads((OUT / "eligible.json").read_text(encoding="utf-8"))
    qids = [row["qid"] for row in eligible]
    print(f"{len(qids)} éligibles, {len(LANGS)} langues", flush=True)

    by_qid: dict[str, dict[str, str]] = {}
    allow: dict[str, set[str]] = {f"{lang}.wikipedia": set() for lang in LANGS}

    for i in range(0, len(qids), BATCH):
        batch = qids[i:i + BATCH]
        rows = sitelinks_batch(batch)
        for qid, lang, title in rows:
            by_qid.setdefault(qid, {})[lang] = title
            allow[f"{lang}.wikipedia"].add(title)
        print(f"  {min(i + BATCH, len(qids))}/{len(qids)}  "
              f"{sum(len(v) for v in allow.values())} titres", flush=True)
        time.sleep(1.2)

    allow_out = {w: sorted(titles) for w, titles in sorted(allow.items()) if titles}
    OUT.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(allow_out, ensure_ascii=False), encoding="utf-8")
    map_path.write_text(json.dumps(by_qid, ensure_ascii=False), encoding="utf-8")
    ingest = ROOT / "data" / "title_allowlist.json"
    ingest.write_text(json.dumps(allow_out, ensure_ascii=False), encoding="utf-8")
    n = sum(len(v) for v in allow_out.values())
    print(f"{len(by_qid)} fiches, {n} titres, {len(allow_out)} éditions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
