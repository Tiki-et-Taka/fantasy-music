"""
Branche albums de l'héritage : albums studio du groupe ∩ années d'appartenance.

Ajoute albums_total / albums_played sur chaque groupe de musicbrainz.json.
Extrait `release` et `release_country` du dump s'il manque.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

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
ALBUM_TABLES = {"release", "release_country"}


def main() -> int:
    mb = json.loads((OUT / "musicbrainz.json").read_text(encoding="utf-8"))
    group_mbids = {
        g["mbid"]
        for rec in mb.values()
        for g in rec.get("groups") or []
        if g.get("mbid")
    }
    print(f"{len(group_mbids)} groupes à dater", flush=True)

    dest = DUMPS / DUMP_NAME
    tables = extract_tables(dest, DUMPS / "mbtables", extra=ALBUM_TABLES)

    print("  artist (groupes)…", flush=True)
    mbid_to_id: dict[str, int] = {}
    id_to_mbid: dict[int, str] = {}
    for cols in iter_rows(tables, "artist"):
        if len(cols) < 2:
            continue
        gid = cols[1]
        if gid in group_mbids:
            aid = int(cols[0])
            mbid_to_id[gid] = aid
            id_to_mbid[aid] = gid
    group_ids = set(mbid_to_id.values())
    print(f"    {len(group_ids)} groupes trouvés", flush=True)

    print("  artist_credit_name (groupes)…", flush=True)
    credit_to_groups: dict[int, list[int]] = defaultdict(list)
    for cols in iter_rows(tables, "artist_credit_name"):
        if len(cols) < 3:
            continue
        artist = int(cols[2])
        if artist in group_ids:
            credit_to_groups[int(cols[0])].append(artist)
    print(f"    {len(credit_to_groups)} crédits de groupes", flush=True)

    print("  release_group albums…", flush=True)
    group_albums: dict[int, set[int]] = defaultdict(set)
    wanted_credits = set(credit_to_groups)
    for cols in iter_rows(tables, "release_group"):
        if len(cols) < 5 or nul(cols[4]) != ALBUM_TYPE:
            continue
        credit = int(cols[3])
        if credit not in wanted_credits:
            continue
        rg = int(cols[0])
        for gid in credit_to_groups[credit]:
            group_albums[gid].add(rg)
    album_ids = {rg for rgs in group_albums.values() for rg in rgs}
    print(f"    {len(album_ids)} albums de groupes", flush=True)

    print("  release → release_group…", flush=True)
    release_to_rg: dict[int, int] = {}
    for cols in iter_rows(tables, "release"):
        if len(cols) < 5:
            continue
        rg = int(cols[4])
        if rg in album_ids:
            release_to_rg[int(cols[0])] = rg
    print(f"    {len(release_to_rg)} releases d'albums", flush=True)

    print("  release_country (années)…", flush=True)
    rg_year: dict[int, int] = {}
    for cols in iter_rows(tables, "release_country"):
        if len(cols) < 3:
            continue
        rel = int(cols[0])
        rg = release_to_rg.get(rel)
        if rg is None:
            continue
        y = year(cols[2])
        if y is None:
            continue
        prev = rg_year.get(rg)
        if prev is None or y < prev:
            rg_year[rg] = y
    print(f"    {len(rg_year)} albums datés", flush=True)

    dated = played = 0
    for rec in mb.values():
        for g in rec.get("groups") or []:
            gid = mbid_to_id.get(g.get("mbid") or "")
            albums = group_albums.get(gid, set()) if gid else set()
            g["albums_total"] = len(albums)
            start, end = g.get("start"), g.get("end") or 2026
            n_played = 0
            if start and albums:
                for rg in albums:
                    y = rg_year.get(rg)
                    if y is not None and int(start) <= y <= int(end):
                        n_played += 1
            g["albums_played"] = n_played
            if start:
                dated += 1
            if n_played:
                played += 1

    (OUT / "musicbrainz.json").write_text(json.dumps(mb, ensure_ascii=False), encoding="utf-8")
    print(f"appartenances datées : {dated}   avec au moins 1 album joué : {played}")
    print("Écrit : data/census/musicbrainz.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
