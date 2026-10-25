"""
Orchestrateur du pipeline catalogue (hors ligne).

Étapes (dans l'ordre) :
  pageviews   — ingest dumps mensuels (gros, local / self-hosted)
  aggregate   — médiane multi-mois → data/pageviews/aggregate.json
  score       — score_vivier.py
  draft       — draft_serie1.py (si besoin)
  export      — export_catalog.py
  prerender   — PNG → WebP

Usage :
  python tools/run_pipeline.py --stage validate
  python tools/run_pipeline.py --stage aggregate,export,prerender
  python tools/run_pipeline.py --stage pageviews --months 2026-04,2026-09
  python tools/run_pipeline.py --stage all-light   # sans retélécharger les dumps
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

STAGES_LIGHT = ["aggregate", "export", "prerender", "validate"]
STAGES_ALL = ["pageviews", "aggregate", "score", "draft", "export", "prerender", "validate"]


def run(script: str, *args: str) -> None:
    cmd = [PY, str(ROOT / "tools" / script), *args]
    print(f"\n>>> {' '.join(cmd)}", flush=True)
    subprocess.check_call(cmd, cwd=ROOT)


def stage_validate() -> None:
    schema = json.loads((ROOT / "data" / "schema" / "catalog.schema.json").read_text(encoding="utf-8"))
    assert schema.get("$schema"), "JSON Schema invalide"
    sql = (ROOT / "data" / "schema" / "catalog.sql").read_text(encoding="utf-8")
    db = tempfile.mktemp(suffix=".db")
    con = sqlite3.connect(db)
    con.executescript(sql)
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    con.close()
    Path(db).unlink(missing_ok=True)
    need = {"series", "artist", "group", "membership", "plate", "card", "rarity_event"}
    missing = need - tables
    if missing:
        raise SystemExit(f"Tables manquantes : {missing}")
    cat = ROOT / "data" / "census" / "catalog_s1.json"
    if cat.exists():
        doc = json.loads(cat.read_text(encoding="utf-8"))
        n = len(doc.get("cards") or [])
        print(f"catalog_s1.json : {n} cartes")
        if doc.get("version") != 1:
            raise SystemExit("catalog version != 1")
    print("validate OK")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--stage",
        default="validate",
        help="étape ou liste (virgules), ou all-light / all",
    )
    ap.add_argument("--months", default="", help="pour pageviews / aggregate")
    ap.add_argument("--skip-download", action="store_true", help="pageviews : dumps déjà locaux")
    ap.add_argument("--prerender-limit", type=int, default=0)
    args = ap.parse_args()

    raw = args.stage.strip().lower()
    if raw == "all-light":
        stages = list(STAGES_LIGHT)
    elif raw == "all":
        stages = list(STAGES_ALL)
    else:
        stages = [s.strip() for s in raw.split(",") if s.strip()]

    for stage in stages:
        print(f"\n===== {stage} =====", flush=True)
        if stage == "validate":
            stage_validate()
        elif stage == "pageviews":
            if not args.months:
                raise SystemExit("pageviews exige --months AAAA-MM,AAAA-MM")
            extra = ["--months", args.months]
            if args.skip_download:
                extra.append("--skip-download")
            run("ingest_pageviews_dump.py", *extra)
        elif stage == "aggregate":
            extra = ["--months", args.months] if args.months else []
            run("aggregate_pageviews.py", *extra)
        elif stage == "score":
            run("score_vivier.py")
        elif stage == "draft":
            run("draft_serie1.py")
        elif stage == "export":
            run("export_catalog.py", "--sqlite", "--validate")
        elif stage == "prerender":
            extra = []
            if args.prerender_limit:
                extra.extend(["--limit", str(args.prerender_limit)])
            run("prerender_illustrations.py", *extra)
        else:
            raise SystemExit(f"Étape inconnue : {stage}")

    print("\nPipeline terminé.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
