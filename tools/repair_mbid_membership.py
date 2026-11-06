"""Reconstruit la fiche musicbrainz.json pour les QID d'artist_mbid_override.

Usage : python tools/repair_mbid_membership.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from census_vivier import CFG  # noqa: E402
from ingest_musicbrainz_dump import (  # noqa: E402
    ALBUM_TYPE,
    DUMP_NAME,
    DUMPS,
    extract_tables,
    iter_rows,
    load_link_types,
    load_links,
    nul,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = ROOT / "data" / "census"


def main() -> int:
    overrides = CFG.get("artist_mbid_override") or {}
    if not overrides:
        print("Aucun artist_mbid_override")
        return 0

    mbids_path = OUT / "mbids.json"
    mbids = json.loads(mbids_path.read_text(encoding="utf-8"))
    for qid, mbid in overrides.items():
        mbids[qid] = mbid
    mbids_path.write_text(json.dumps(mbids, ensure_ascii=False), encoding="utf-8")

    mb_path = OUT / "musicbrainz.json"
    records = json.loads(mb_path.read_text(encoding="utf-8"))

    wanted = set(overrides.values())
    dest = DUMPS / DUMP_NAME
    tables = extract_tables(dest, DUMPS / "mbtables")
    keep_types, _ = load_link_types(tables)

    mbid_to_id: dict[str, int] = {}
    id_to_mbid: dict[int, str] = {}
    id_to_type: dict[int, str] = {}
    print("artist…", flush=True)
    for cols in iter_rows(tables, "artist"):
        if len(cols) < 11:
            continue
        aid = int(cols[0])
        gid = cols[1]
        id_to_mbid[aid] = gid
        id_to_type[aid] = nul(cols[10]) or ""
        if gid in wanted:
            mbid_to_id[gid] = aid
    our_ids = set(mbid_to_id.values())
    print(f"  cibles trouvées : {len(our_ids)}/{len(wanted)}", flush=True)

    links = load_links(tables, keep_types)
    by_person: dict[int, list[dict]] = defaultdict(list)
    print("l_artist_artist…", flush=True)
    for cols in iter_rows(tables, "l_artist_artist"):
        if len(cols) < 4:
            continue
        link_id = int(cols[1])
        if link_id not in links:
            continue
        entity0, entity1 = int(cols[2]), int(cols[3])
        if entity0 not in our_ids:
            continue
        _, start, end = links[link_id]
        by_person[entity0].append({"group_id": entity1, "start": start, "end": end})

    print("artist_credit_name…", flush=True)
    credit_to_artists: dict[int, list[int]] = defaultdict(list)
    for cols in iter_rows(tables, "artist_credit_name"):
        if len(cols) < 3:
            continue
        artist = int(cols[2])
        if artist in our_ids:
            credit_to_artists[int(cols[0])].append(artist)

    print("release_group…", flush=True)
    rg_total: dict[int, int] = defaultdict(int)
    rg_albums: dict[int, int] = defaultdict(int)
    wanted_credits = set(credit_to_artists)
    for cols in iter_rows(tables, "release_group"):
        if len(cols) < 5:
            continue
        credit = int(cols[3])
        if credit not in wanted_credits:
            continue
        is_album = nul(cols[4]) == ALBUM_TYPE
        for artist in credit_to_artists[credit]:
            rg_total[artist] += 1
            if is_album:
                rg_albums[artist] += 1

    for qid, mbid in overrides.items():
        aid = mbid_to_id.get(mbid)
        if aid is None:
            records[qid] = {"mbid": mbid, "release_groups": 0, "albums": 0, "groups": []}
            print(f"{qid}: MBID introuvable dans le dump")
            continue
        groups = []
        for rel in by_person.get(aid, []):
            gid = rel["group_id"]
            groups.append({
                "mbid": id_to_mbid.get(gid),
                "type": id_to_type.get(gid),
                "start": rel["start"],
                "end": rel["end"],
            })
        records[qid] = {
            "mbid": mbid,
            "release_groups": rg_total.get(aid, 0),
            "albums": rg_albums.get(aid, 0),
            "groups": groups,
        }
        queen = [g for g in groups if g.get("mbid") == "0383dadf-2a4e-4d10-a46a-e9e041da8eb3"]
        print(
            f"{qid}: groups={len(groups)} rg={rg_total.get(aid, 0)} "
            f"albums={rg_albums.get(aid, 0)} queen_links={len(queen)}",
            flush=True,
        )

    mb_path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    print(f"Écrit : {mb_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
