"""
Agrège les dumps pageviews mensuels en une médiane par (wiki, titre).

Lit data/pageviews/AAAA-MM/sample_views.json et écrit :
  data/pageviews/aggregate.json

La médiane écrase les pics (décès, sorties) — cf. docs/03-rarete-scoring.md.

Usage :
  python tools/aggregate_pageviews.py
  python tools/aggregate_pageviews.py --months 2026-04,2026-09
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PV = ROOT / "data" / "pageviews"
OUT = PV / "aggregate.json"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def list_months() -> list[str]:
    if not PV.exists():
        return []
    months = []
    for p in PV.iterdir():
        if p.is_dir() and (p / "sample_views.json").exists():
            months.append(p.name)
    return sorted(months)


def load_month(month: str) -> dict[str, dict[str, int]]:
    path = PV / month / "sample_views.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {
        wiki: {title: int(v) for title, v in titles.items()}
        for wiki, titles in raw.items()
    }


def aggregate(months: list[str]) -> dict:
    monthly = [load_month(m) for m in months]
    title_universe: dict[str, set[str]] = defaultdict(set)
    for data in monthly:
        for wiki, titles in data.items():
            title_universe[wiki].update(titles.keys())

    # wiki → title → views per month (0 si absent ce mois-là)
    series: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
    for data in monthly:
        for wiki, titles_set in title_universe.items():
            bucket = data.get(wiki) or {}
            for title in titles_set:
                series[wiki][title].append(int(bucket.get(title) or 0))

    sample: dict[str, dict[str, int]] = {}
    for wiki, titles in series.items():
        sample[wiki] = {
            title: int(statistics.median(vals))
            for title, vals in titles.items()
        }

    return {
        "months": months,
        "month_count": len(months),
        "method": "median",
        "sample_views": sample,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", help="AAAA-MM,AAAA-MM,… (défaut : tous les mois présents)")
    ap.add_argument("-o", "--output", type=Path, default=OUT)
    args = ap.parse_args()

    months = (
        [m.strip() for m in args.months.split(",") if m.strip()]
        if args.months
        else list_months()
    )
    if not months:
        print("Aucun mois dans data/pageviews/*/sample_views.json", file=sys.stderr)
        print("Lance d'abord : python tools/ingest_pageviews_dump.py --month AAAA-MM",
              file=sys.stderr)
        return 1

    missing = [m for m in months if not (PV / m / "sample_views.json").exists()]
    if missing:
        print(f"Mois manquants : {', '.join(missing)}", file=sys.stderr)
        return 1

    doc = aggregate(months)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    hits = sum(len(t) for t in doc["sample_views"].values())
    print(
        f"Écrit {args.output.relative_to(ROOT)} — "
        f"{doc['month_count']} mois ({', '.join(months)}), "
        f"{hits} paires wiki/titre (médiane)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
