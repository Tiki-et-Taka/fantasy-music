"""
Nom de groupe principal (MusicBrainz) + noms d'artistes sans désambiguïsation
Wikipédia, réinjectés dans serie1.json et docs/serie-1-draft.csv.

Usage : python tools/attach_group_names.py
"""

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from score_vivier import FAMILY_LABEL, display_name  # noqa: E402

CFG = json.loads((ROOT / "tools" / "census_config.json").read_text(encoding="utf-8"))
CENSUS = ROOT / "data" / "census"
ARTIST_TABLE = ROOT / "data" / "dumps" / "mbtables" / "artist"
GROUP_TYPES = {"2", "5", "6"}
_DISAMB = re.compile(r"\s*\([^)]*\)\s*$")
_THE = re.compile(r"^the\s+", re.I)


def clean_label(name: str) -> str:
    return _DISAMB.sub("", (name or "").strip()).strip()


def is_self_named(group: str, artist: str) -> bool:
    g = _THE.sub("", (group or "").lower())
    a = (artist or "").lower().strip()
    return bool(a) and g.startswith(a)


def tenure(g: dict) -> tuple[int, bool]:
    start, end = g.get("start"), g.get("end")
    if not start:
        return 0, False
    last = end or 2026
    years = max(1, last - start)
    return years, True


def eligible(g: dict) -> bool:
    typ = str(g.get("type") or "")
    if typ and typ not in GROUP_TYPES:
        return False
    played = int(g.get("albums_played") or 0)
    total = int(g.get("albums_total") or 0)
    years, dated = tenure(g)
    if played == 0 and total == 0:
        return False
    if dated:
        return years >= 5 or played >= 8
    return total >= 50


def pick_principal(groups: list[dict]) -> str | None:
    best_mbid = None
    best_key = (-1, -1, -1)
    seen: set[str] = set()
    for g in groups:
        mbid = g.get("mbid")
        if not mbid or mbid in seen or not eligible(g):
            continue
        seen.add(mbid)
        played = int(g.get("albums_played") or 0)
        total = int(g.get("albums_total") or 0)
        years, dated = tenure(g)
        key = (played, years, total if not dated else 0)
        if key > best_key:
            best_key = key
            best_mbid = mbid
    return best_mbid


def load_names(mbids: set[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    if not mbids or not ARTIST_TABLE.exists():
        return out
    wanted = set(mbids)
    with ARTIST_TABLE.open("r", encoding="utf-8", errors="replace", newline="") as fh:
        for line in fh:
            cols = line.split("\t")
            if len(cols) < 3:
                continue
            gid = cols[1]
            if gid not in wanted:
                continue
            out[gid] = cols[2]
            wanted.remove(gid)
            if not wanted:
                break
    return out


def write_csv(serie: list[dict], titles: dict) -> None:
    labels = {
        **FAMILY_LABEL,
        "anglophone": "anglophone",
        "europe_fr": "Europe francophone",
        "europe": "reste de l'Europe",
        "latam": "Amérique latine",
        "afrique": "Afrique",
        "asie_est": "Asie de l'Est",
        "mena": "MENA",
        "est": "Europe de l'Est / CEI",
        "asie_sud": "Asie du Sud / SE",
        "autre": "autre",
        "pre1970": "avant 1970",
        "1970s80s": "1970–89",
        "1990s00s": "1990–2009",
        "2010s": "2010+",
    }
    path = ROOT / "docs" / "serie-1-draft.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow([
            "rang_serie", "rarete", "artiste", "groupe", "famille", "bande",
            "region", "epoque", "sexe", "instrument", "plaque",
            "rang_vivier", "motif",
        ])
        for rec in serie:
            writer.writerow([
                rec["rank_serie"],
                rec["rarete"],
                display_name(rec["qid"], titles),
                rec.get("groupe") or "",
                FAMILY_LABEL.get(rec["family"], rec["family"]),
                rec.get("band") or "",
                labels.get(rec.get("region"), rec.get("region") or ""),
                labels.get(
                    rec.get("era_peak") or rec.get("era"),
                    rec.get("era_peak") or rec.get("era") or "",
                ),
                rec.get("silhouette") or "",
                rec.get("instrument") or "",
                rec.get("plaque") or "",
                rec.get("rank_vivier"),
                rec.get("draft_reason") or "",
            ])
    print(f"CSV → {path.relative_to(ROOT)}")


def main() -> int:
    serie = json.loads((CENSUS / "serie1.json").read_text(encoding="utf-8"))
    mb = json.loads((CENSUS / "musicbrainz.json").read_text(encoding="utf-8"))
    titles = json.loads((CENSUS / "qid_titles.json").read_text(encoding="utf-8"))

    wanted: set[str] = set()
    picks: dict[str, str | None] = {}
    for rec in serie:
        groups = (mb.get(rec["qid"]) or {}).get("groups") or []
        mbid = pick_principal(groups)
        picks[rec["qid"]] = mbid
        if mbid:
            wanted.add(mbid)

    print(f"Groupes MusicBrainz à nommer : {len(wanted)}", flush=True)
    names = load_names(wanted)
    print(f"Noms trouvés : {len(names)}", flush=True)

    with_group = 0
    self_named = 0
    missing_name = 0
    editorial = 0
    forced_of = CFG.get("artist_group_override") or {}
    for rec in serie:
        artist = display_name(rec["qid"], titles)
        rec["artiste"] = artist
        forced = forced_of.get(rec["qid"])
        if forced:
            rec["groupe"] = forced
            editorial += 1
            with_group += 1
            continue
        mbid = picks.get(rec["qid"])
        label = clean_label(names.get(mbid or "", ""))
        if mbid and not label:
            missing_name += 1
            rec["groupe"] = ""
        elif label and is_self_named(label, artist):
            self_named += 1
            rec["groupe"] = ""
        else:
            rec["groupe"] = label
            if label:
                with_group += 1

    (CENSUS / "serie1.json").write_text(
        json.dumps(serie, ensure_ascii=False), encoding="utf-8"
    )
    write_csv(serie, titles)

    print(f"Série 1 : {with_group} avec groupe, "
          f"{len(serie) - with_group} Artiste solo "
          f"(dont {self_named} auto-nommés, {missing_name} sans nom MB, "
          f"{editorial} override éditorial)")
    check = {
        "Michael Jackson", "John Lennon", "Shakira", "Bob Dylan",
        "Paul McCartney", "Céline Dion", "Eminem", "Madonna",
        "Bono", "Rob Bourdon", "Miles Davis", "Barbara Pravi",
        "Prince", "Elvis Presley", "Freddie Mercury", "Bob Marley",
        "Damiano David", "Dave Grohl", "Jimi Hendrix", "Eric Clapton",
    }
    print("Repères :")
    for rec in serie:
        if rec["artiste"] in check:
            print(f"  {rec['artiste']} → {rec.get('groupe') or 'Artiste solo'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
