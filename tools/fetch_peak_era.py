"""Période emblématique : décennie des albums studio adultes, pas le premier single enfant."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from census_vivier import CFG, era_of  # noqa: E402
from ingest_musicbrainz_dump import (  # noqa: E402
    ALBUM_TYPE,
    DUMP_NAME,
    DUMPS,
    extract_tables,
    iter_rows,
    nul,
    year,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = ROOT / "data" / "census"
ADULT_AGE = 16
CHILD_AGE = 14
WINDOW = 12
OVERRIDES = CFG.get("artist_era_override") or {}


def adult_start(start: int | None, birth: int | None) -> int | None:
    if birth is not None and start is not None and start < birth + ADULT_AGE:
        return birth + 18
    return start if start is not None else (birth + 18 if birth is not None else None)


def peak_from_years(years: list[int]) -> tuple[str, int]:
    years = sorted(y for y in years if 1920 <= y <= 2026)
    mid = years[len(years) // 2]
    if len(years) < 3:
        return era_of(mid, None), mid
    buckets = Counter(era_of(y, None) for y in years)
    top_n = buckets.most_common(1)[0][1]
    tied = [era for era, n in buckets.items() if n == top_n]
    if len(tied) == 1:
        return tied[0], mid
    return era_of(mid, None), mid


def main() -> int:
    people = json.loads((OUT / "people_raw.json").read_text(encoding="utf-8"))
    eligible = json.loads((OUT / "eligible.json").read_text(encoding="utf-8"))
    qids = [r["qid"] for r in eligible]
    mb = json.loads((OUT / "musicbrainz.json").read_text(encoding="utf-8"))

    wanted_mbids = {mb[q]["mbid"] for q in qids if q in mb and mb[q].get("mbid")}
    tables = extract_tables(DUMPS / DUMP_NAME, DUMPS / "mbtables", extra={"release", "release_country"})

    print("  artist…", flush=True)
    mbid_to_id: dict[str, int] = {}
    for cols in iter_rows(tables, "artist"):
        if len(cols) < 2:
            continue
        if cols[1] in wanted_mbids:
            mbid_to_id[cols[1]] = int(cols[0])
    our_ids = set(mbid_to_id.values())
    print(f"    {len(our_ids)} artistes", flush=True)

    print("  artist_credit_name…", flush=True)
    credit_to_artists: dict[int, list[int]] = defaultdict(list)
    for cols in iter_rows(tables, "artist_credit_name"):
        if len(cols) < 3:
            continue
        artist = int(cols[2])
        if artist in our_ids:
            credit_to_artists[int(cols[0])].append(artist)
    print(f"    {len(credit_to_artists)} crédits", flush=True)

    print("  release_group albums…", flush=True)
    artist_albums: dict[int, set[int]] = defaultdict(set)
    wanted_credits = set(credit_to_artists)
    for cols in iter_rows(tables, "release_group"):
        if len(cols) < 5 or nul(cols[4]) != ALBUM_TYPE:
            continue
        credit = int(cols[3])
        if credit not in wanted_credits:
            continue
        rg = int(cols[0])
        for aid in credit_to_artists[credit]:
            artist_albums[aid].add(rg)
    album_ids = {rg for rgs in artist_albums.values() for rg in rgs}
    print(f"    {len(album_ids)} albums", flush=True)

    print("  release → release_group…", flush=True)
    release_to_rg: dict[int, int] = {}
    for cols in iter_rows(tables, "release"):
        if len(cols) < 5:
            continue
        rg = int(cols[4])
        if rg in album_ids:
            release_to_rg[int(cols[0])] = rg

    print("  release_country…", flush=True)
    rg_year: dict[int, int] = {}
    for cols in iter_rows(tables, "release_country"):
        if len(cols) < 3:
            continue
        rg = release_to_rg.get(int(cols[0]))
        if rg is None:
            continue
        y = year(cols[2])
        if y is None:
            continue
        prev = rg_year.get(rg)
        if prev is None or y < prev:
            rg_year[rg] = y
    print(f"    {len(rg_year)} albums datés", flush=True)

    id_to_qid = {mbid_to_id[mb[q]["mbid"]]: q for q in qids
                 if q in mb and mb[q].get("mbid") in mbid_to_id}

    out: dict[str, dict] = {}
    src_c: Counter[str] = Counter()
    for qid in qids:
        raw = people.get(qid) or {}
        start, birth = raw.get("start"), raw.get("birth")
        fallback_year = adult_start(start, birth)
        fallback_era = era_of(fallback_year, None) if fallback_year else (raw.get("era") or "inconnu")

        years = []
        aid = mbid_to_id.get((mb.get(qid) or {}).get("mbid") or "")
        if aid:
            min_year = (birth + ADULT_AGE) if birth else 1920
            for rg in artist_albums.get(aid, ()):
                y = rg_year.get(rg)
                if y is not None and y >= min_year:
                    years.append(y)

        child = birth is not None and start is not None and start < birth + CHILD_AGE
        if qid in OVERRIDES:
            era = OVERRIDES[qid]
            peak_year = fallback_year
            source = "override"
        elif child and len(years) >= 2:
            first = min(years)
            era, peak_year = peak_from_years([y for y in years if y <= first + WINDOW])
            source = "enfance"
        elif child:
            era, peak_year = fallback_era, fallback_year
            source = "debut_adulte"
        else:
            y = start if start is not None else fallback_year
            era, peak_year = (era_of(y, None) if y else "inconnu"), y
            source = "debut"

        out[qid] = {
            "era_start": era_of(start, birth) if start or birth else "inconnu",
            "era_peak": era,
            "peak_year": peak_year,
            "albums_dated": len(years),
            "source": source,
        }
        src_c[source] += 1

    dest = OUT / "peak_era.json"
    dest.write_text(json.dumps(out), encoding="utf-8")
    print(f"{len(out)} → {dest.relative_to(ROOT)}")
    print("Sources : " + ", ".join(f"{k}={v}" for k, v in src_c.most_common()))
    moved = sum(1 for v in out.values() if v["era_start"] != v["era_peak"])
    print(f"Période décalée vs début de carrière : {moved}")

    titles = {}
    tpath = OUT / "qid_titles.json"
    if tpath.exists():
        titles = json.loads(tpath.read_text(encoding="utf-8"))
    print("\nIcônes")
    for qid in ("Q2831", "Q303", "Q392", "Q1744", "Q2599", "Q1203", "Q19848", "Q23215", "Q2632"):
        rec = out.get(qid, {})
        name = (titles.get(qid) or {}).get("en") or (titles.get(qid) or {}).get("fr") or qid
        print(f"  {name:<22} start={rec.get('era_start')}  peak={rec.get('era_peak')}  "
              f"year={rec.get('peak_year')}  n={rec.get('albums_dated')}  {rec.get('source')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
