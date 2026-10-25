"""
Télécharge mbdump.tar.bz2 et n'en extrait que ce qui sert au vivier :

  - volume de release-groups (discographie) ;
  - relations « member of band » avec années de début/fin.

Usage :
  python tools/ingest_musicbrainz_dump.py
  python tools/ingest_musicbrainz_dump.py --skip-download
"""

from __future__ import annotations

import argparse
import bz2
import json
import sys
import tarfile
import time
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DUMPS = ROOT / "data" / "dumps"
OUT = ROOT / "data" / "census"
UA = "fantasy-music-mb/0.1 (prototype de jeu de cartes; contact: edouard@localhost)"
DUMP_URL = (
    "https://data.metabrainz.org/pub/musicbrainz/data/fullexport/"
    "20261017-002244/mbdump.tar.bz2"
)
DUMP_NAME = "mbdump-20261017.tar.bz2"

# Types de release-group MusicBrainz : 1 = Album.
ALBUM_TYPE = "1"
MEMBER_TYPE_NAMES = {"member of band", "founder", "vocalist", "instrumentalist"}
SKIP_TYPE_NAMES = {"supporting musician", "tribute", "conductor", "teacher"}


def download(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = dest.stat().st_size if dest.exists() else 0
    headers = {"User-Agent": UA}
    if existing:
        headers["Range"] = f"bytes={existing}-"
        print(f"  reprise à {existing / 1e9:.2f} Go", flush=True)
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as exc:
        if exc.code == 416 and existing:
            print("  déjà complet", flush=True)
            return
        raise
    total = int(resp.headers.get("Content-Length") or 0)
    if resp.status == 206:
        total += existing
    elif existing and resp.status == 200:
        existing = 0
        dest.unlink(missing_ok=True)
    mode = "ab" if existing else "wb"
    t0 = time.time()
    got = existing
    last = t0
    with dest.open(mode) as fh:
        while True:
            chunk = resp.read(1024 * 1024)
            if not chunk:
                break
            fh.write(chunk)
            got += len(chunk)
            now = time.time()
            if now - last >= 15:
                speed = (got - existing) / max(now - t0, 1) / 1e6
                pct = f"{100 * got / total:5.1f}%" if total else "  ?"
                print(f"  {pct}  {got / 1e9:.2f} Go  {speed:.1f} Mo/s", flush=True)
                last = now
    print(f"  téléchargé : {got / 1e9:.2f} Go", flush=True)


NEEDED_TABLES = {
    "artist", "link_type", "link", "l_artist_artist",
    "artist_credit_name", "release_group",
}


def extract_tables(src: Path, dest_dir: Path, extra: set[str] | None = None) -> Path:
    """Une seule décompression : on sort les tables utiles."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    needed = set(NEEDED_TABLES)
    if extra:
        needed |= extra
    have = {p.name for p in dest_dir.iterdir() if p.is_file()}
    if needed <= have:
        print(f"  tables déjà extraites dans {dest_dir}", flush=True)
        return dest_dir
    print("  extraction des tables (une passe sur le tar.bz2)…", flush=True)
    raw = bz2.open(src, "rb")
    tar = tarfile.open(fileobj=raw, mode="r|")
    try:
        for member in tar:
            base = member.name.rsplit("/", 1)[-1]
            if base not in needed or (dest_dir / base).exists():
                continue
            print(f"    {base}  ({(member.size or 0) / 1e6:.0f} Mo)…", flush=True)
            fh = tar.extractfile(member)
            if fh is None:
                continue
            with (dest_dir / base).open("wb") as out:
                while True:
                    chunk = fh.read(8 * 1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
            fh.close()
            have = {p.name for p in dest_dir.iterdir() if p.is_file()}
            if needed <= have:
                print("  toutes les tables sont là, on arrête l'extraction", flush=True)
                break
    finally:
        tar.close()
        raw.close()
    missing = needed - {p.name for p in dest_dir.iterdir()}
    if missing:
        raise FileNotFoundError(f"tables absentes du dump : {sorted(missing)}")
    return dest_dir


def iter_rows(table_dir: Path, table: str):
    path = table_dir / table
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh, 1):
            yield line.rstrip("\n").split("\t")
            if i % 5_000_000 == 0:
                print(f"      {table} {i/1e6:.1f} M lignes", flush=True)


def nul(value: str) -> str | None:
    return None if value == "\\N" or value == "" else value


def year(value: str) -> int | None:
    v = nul(value)
    if not v:
        return None
    try:
        y = int(v)
    except ValueError:
        return None
    if y < 1800 or y > 2030:
        return None
    return y


def load_link_types(src: Path) -> tuple[set[int], set[int]]:
    keep, skip = set(), set()
    print("  link_type…", flush=True)
    for cols in iter_rows(src, "link_type"):
        if len(cols) < 7:
            continue
        name = cols[6].lower()
        tid = int(cols[0])
        if name in MEMBER_TYPE_NAMES:
            keep.add(tid)
        elif name in SKIP_TYPE_NAMES:
            skip.add(tid)
    print(f"    member={sorted(keep)}  skip={sorted(skip)}", flush=True)
    return keep, skip


def load_artists(src: Path, wanted_mbid: set[str]) -> tuple[dict[str, int], dict[int, str], dict[int, str]]:
    """mbid→id pour le vivier, id→mbid, id→type (person/group)."""
    mbid_to_id: dict[str, int] = {}
    id_to_mbid: dict[int, str] = {}
    id_to_type: dict[int, str] = {}
    print("  artist…", flush=True)
    n = 0
    for cols in iter_rows(src, "artist"):
        n += 1
        if len(cols) < 11:
            continue
        aid = int(cols[0])
        gid = cols[1]
        typ = nul(cols[10])
        id_to_mbid[aid] = gid
        id_to_type[aid] = typ or ""
        if gid in wanted_mbid:
            mbid_to_id[gid] = aid
        if n % 500_000 == 0:
            print(f"    {n/1e6:.1f} M artistes  vivier={len(mbid_to_id)}", flush=True)
    print(f"    {n} artistes, {len(mbid_to_id)} dans le vivier", flush=True)
    return mbid_to_id, id_to_mbid, id_to_type


def load_links(src: Path, keep_types: set[int]) -> dict[int, tuple[int, int | None, int | None]]:
    """link_id → (link_type, begin_year, end_year) pour les types retenus."""
    out: dict[int, tuple[int, int | None, int | None]] = {}
    print("  link…", flush=True)
    n = 0
    for cols in iter_rows(src, "link"):
        n += 1
        if len(cols) < 8:
            continue
        ltype = int(cols[1])
        if ltype not in keep_types:
            continue
        out[int(cols[0])] = (ltype, year(cols[2]), year(cols[5]))
        if n % 2_000_000 == 0:
            print(f"    {n/1e6:.1f} M links  gardés={len(out)}", flush=True)
    print(f"    {len(out)} links utiles / {n}", flush=True)
    return out


def load_memberships(
    src: Path,
    our_ids: set[int],
    links: dict[int, tuple[int, int | None, int | None]],
) -> dict[int, list[dict]]:
    """artist_id personne → [{group_id, start, end}]."""
    by_person: dict[int, list[dict]] = defaultdict(list)
    print("  l_artist_artist…", flush=True)
    n = 0
    hit = 0
    for cols in iter_rows(src, "l_artist_artist"):
        n += 1
        if len(cols) < 4:
            continue
        link_id = int(cols[1])
        if link_id not in links:
            continue
        entity0, entity1 = int(cols[2]), int(cols[3])
        _, start, end = links[link_id]
        # member of band : entity0 = membre, entity1 = groupe
        if entity0 in our_ids:
            by_person[entity0].append({"group_id": entity1, "start": start, "end": end})
            hit += 1
        if n % 2_000_000 == 0:
            print(f"    {n/1e6:.1f} M rels  hits={hit}", flush=True)
    print(f"    {hit} appartenances pour {len(by_person)} personnes", flush=True)
    return by_person


def load_release_counts(src: Path, our_ids: set[int]) -> tuple[dict[int, int], dict[int, int]]:
    """Compte les release-groups (albums) où l'artiste est au crédit."""
    print("  artist_credit_name…", flush=True)
    credit_to_artists: dict[int, list[int]] = defaultdict(list)
    n = 0
    for cols in iter_rows(src, "artist_credit_name"):
        n += 1
        if len(cols) < 3:
            continue
        artist = int(cols[2])
        if artist not in our_ids:
            continue
        credit_to_artists[int(cols[0])].append(artist)
        if n % 5_000_000 == 0:
            print(f"    {n/1e6:.1f} M crédits  utiles={len(credit_to_artists)}", flush=True)
    print(f"    {len(credit_to_artists)} artist-credits du vivier", flush=True)

    print("  release_group…", flush=True)
    counts: dict[int, int] = defaultdict(int)
    albums: dict[int, int] = defaultdict(int)
    n = 0
    wanted_credits = set(credit_to_artists)
    for cols in iter_rows(src, "release_group"):
        n += 1
        if len(cols) < 5:
            continue
        credit = int(cols[3])
        if credit not in wanted_credits:
            continue
        is_album = nul(cols[4]) == ALBUM_TYPE
        for artist in credit_to_artists[credit]:
            counts[artist] += 1
            if is_album:
                albums[artist] += 1
        if n % 1_000_000 == 0:
            print(f"    {n/1e6:.1f} M RG", flush=True)
    print(f"    {n} release-groups scannés", flush=True)
    return counts, albums


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--skip-download", action="store_true")
    args = p.parse_args()

    dest = DUMPS / DUMP_NAME
    if args.skip_download:
        if not dest.exists():
            raise FileNotFoundError(dest)
        print(f"dump local : {dest.stat().st_size / 1e9:.2f} Go", flush=True)
    else:
        print(f"Téléchargement {DUMP_URL}", flush=True)
        download(DUMP_URL, dest)

    mbids = json.loads((OUT / "mbids.json").read_text(encoding="utf-8"))
    wanted = set(mbids.values())
    print(f"{len(wanted)} MBID du vivier", flush=True)

    tables = extract_tables(dest, DUMPS / "mbtables")
    keep_types, _skip = load_link_types(tables)
    mbid_to_id, id_to_mbid, id_to_type = load_artists(tables, wanted)
    our_ids = set(mbid_to_id.values())
    links = load_links(tables, keep_types)
    memberships = load_memberships(tables, our_ids, links)
    rg_total, rg_albums = load_release_counts(tables, our_ids)

    id_to_qid = {mbid_to_id[mbid]: qid for qid, mbid in mbids.items() if mbid in mbid_to_id}
    records = {}
    for qid, mbid in mbids.items():
        aid = mbid_to_id.get(mbid)
        if aid is None:
            records[qid] = {"mbid": mbid, "release_groups": 0, "albums": 0, "groups": []}
            continue
        groups = []
        for rel in memberships.get(aid, []):
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

    out = OUT / "musicbrainz.json"
    out.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    with_rg = sum(1 for r in records.values() if r["release_groups"])
    with_g = sum(1 for r in records.values() if r["groups"])
    dated = sum(
        1 for r in records.values()
        if any(g.get("start") for g in r["groups"])
    )
    print(f"\n{len(records)} fiches")
    print(f"  avec release-groups : {with_rg}")
    print(f"  avec au moins un groupe : {with_g}")
    print(f"  avec une date d'appartenance : {dated}")
    print(f"Écrit : {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
