"""
Télécharge et filtre un dump mensuel pageview_complete Wikimedia.

Le dump brut (~6 Go compressé) n'est pas conservé après filtrage : on stream
la décompression, on ne retient que les lignes Wikipedia + agent user déjà
pré-filtré dans le fichier `-user.bz2`, et on agrège :

  - vues par (wiki, titre) pour une allowlist d'artistes (échantillon) ;
  - trafic total par édition Wikipedia (dénominateur √(V_w)).

Usage :
  python tools/ingest_pageviews_dump.py --month 2026-09
  python tools/ingest_pageviews_dump.py --month 2026-09 --keep-dump
  python tools/ingest_pageviews_dump.py --months 2026-04,2026-05,2026-06,2026-07,2026-08,2026-09

Aucune dépendance externe. Reprend un téléchargement interrompu (Range).
"""

from __future__ import annotations

import argparse
import bz2
import json
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
DUMPS = DATA / "dumps"
OUT = DATA / "pageviews"
UA = "fantasy-music-ingest/0.1 (prototype de jeu de cartes; contact: edouard@localhost)"

# Première vague : les plus grosses éditions + celles qui corrigent le biais.
# On peut élargir plus tard sans retélécharger : le dump contient toutes les langues.
DEFAULT_WIKIS = {
    "en.wikipedia", "de.wikipedia", "fr.wikipedia", "es.wikipedia",
    "it.wikipedia", "ja.wikipedia", "ru.wikipedia", "pt.wikipedia",
    "pl.wikipedia", "nl.wikipedia", "zh.wikipedia", "sv.wikipedia",
    "ar.wikipedia", "ko.wikipedia", "tr.wikipedia", "id.wikipedia",
    "fa.wikipedia", "uk.wikipedia", "cs.wikipedia", "fi.wikipedia",
    "hu.wikipedia", "he.wikipedia", "ca.wikipedia", "no.wikipedia",
    "da.wikipedia", "ro.wikipedia", "el.wikipedia", "th.wikipedia",
    "vi.wikipedia", "hi.wikipedia",
}


def dump_url(month: str) -> str:
    y, m = month.split("-")
    return (
        "https://dumps.wikimedia.org/other/pageview_complete/monthly/"
        f"{y}/{month}/pageviews-{y}{m}-user.bz2"
    )


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = dest.stat().st_size if dest.exists() else 0
    headers = {"User-Agent": UA}
    if existing:
        headers["Range"] = f"bytes={existing}-"
        print(f"  reprise a {existing / 1e9:.2f} Go", flush=True)

    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and existing:
            print("  deja complet", flush=True)
            return
        raise

    total = int(resp.headers.get("Content-Length") or 0)
    if resp.status == 206:
        total += existing
    elif existing and resp.status == 200:
        existing = 0  # le serveur ignore Range : on recommence
        dest.unlink(missing_ok=True)

    mode = "ab" if existing else "wb"
    t0 = time.time()
    got = existing
    last_report = t0
    with dest.open(mode) as fh:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            fh.write(chunk)
            got += len(chunk)
            now = time.time()
            if now - last_report >= 15:
                speed = (got - existing) / max(now - t0, 1) / 1e6
                pct = f"{100 * got / total:5.1f}%" if total else "  ?  "
                print(f"  {pct}  {got / 1e9:.2f} Go  {speed:.1f} Mo/s", flush=True)
                last_report = now
    print(f"  telecharge : {got / 1e9:.2f} Go", flush=True)


def load_allowlist() -> dict[str, set[str]]:
    """wiki_code → titres (underscores) issus de l'échantillon de validation."""
    path = DATA / "title_allowlist.json"
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {wiki: set(titles) for wiki, titles in raw.items()}


def filter_dump(src: Path, month: str, allowlist: dict[str, set[str]], wikis: set[str]) -> dict:
    """Stream-décompresse et agrège. Ne charge jamais le dump en mémoire."""
    per_title: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    per_wiki: dict[str, int] = defaultdict(int)
    matched = 0
    kept_lines = 0
    t0 = time.time()

    with bz2.open(src, "rt", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            # Format pageview_complete mensuel (-user.bz2) :
            #   wiki_code  page_title  page_id  access_method  views  daily_vector
            # Le dernier champ est un encodage jour par jour (S4T4U2…), pas un entier.
            # Le titre peut contenir des espaces : tout ce qui est entre le wiki et
            # les 4 champs de queue.
            parts = line.split()
            if len(parts) < 6:
                continue
            domain = parts[0]
            if domain not in wikis:
                continue
            try:
                views = int(parts[-2])
            except ValueError:
                continue
            title = "_".join(parts[1:-4])
            per_wiki[domain] += views
            kept_lines += 1
            if title in allowlist.get(domain, ()):
                per_title[domain][title] += views
                matched += 1
            if i % 5_000_000 == 0:
                elapsed = time.time() - t0
                print(f"    {i/1e6:.0f} M lignes  {elapsed:.0f}s  "
                      f"{matched} titres echantillon", flush=True)

    out_month = OUT / month
    out_month.mkdir(parents=True, exist_ok=True)
    (out_month / "wiki_totals.json").write_text(
        json.dumps(dict(sorted(per_wiki.items(), key=lambda kv: -kv[1])), indent=2),
        encoding="utf-8",
    )
    sample = {w: dict(titles) for w, titles in per_title.items()}
    (out_month / "sample_views.json").write_text(
        json.dumps(sample, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary = {
        "month": month,
        "wikis": sorted(wikis),
        "sample_title_hits": matched,
        "wikipedia_lines_kept": kept_lines,
        "wiki_count": len(per_wiki),
    }
    (out_month / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"  filtrage : {matched} titres echantillon, {len(per_wiki)} editions, "
          f"{kept_lines} lignes Wikipedia", flush=True)
    return summary


def process_month(month: str, *, keep_dump: bool, skip_download: bool, wikis: set[str]) -> None:
    url = dump_url(month)
    dest = DUMPS / f"pageviews-{month.replace('-', '')}-user.bz2"
    print(f"\n=== {month} ===", flush=True)
    print(f"  {url}", flush=True)
    if skip_download:
        if not dest.exists():
            raise FileNotFoundError(dest)
        print(f"  dump local : {dest.stat().st_size / 1e9:.2f} Go", flush=True)
    else:
        download(url, dest)
    allowlist = load_allowlist()
    if not allowlist:
        print("  ATTENTION : pas d'allowlist (data/title_allowlist.json). "
              "On calcule seulement les totaux par edition.", flush=True)
    filter_dump(dest, month, allowlist, wikis)
    if not keep_dump:
        dest.unlink(missing_ok=True)
        print("  dump brut supprime", flush=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--month", help="AAAA-MM")
    p.add_argument("--months", help="liste AAAA-MM separee par des virgules")
    p.add_argument("--keep-dump", action="store_true")
    p.add_argument("--skip-download", action="store_true",
                   help="refiltre un dump deja present, sans retélécharger")
    args = p.parse_args()

    months = []
    if args.month:
        months.append(args.month)
    if args.months:
        months.extend(m.strip() for m in args.months.split(",") if m.strip())
    if not months:
        p.error("indiquer --month ou --months")

    for month in months:
        process_month(month, keep_dump=args.keep_dump, skip_download=args.skip_download,
                      wikis=DEFAULT_WIKIS)
    return 0


if __name__ == "__main__":
    sys.exit(main())
