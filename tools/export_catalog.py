"""
Exporte la Série 1 vers le schéma catalogue (docs/09-schema-donnees.md).

Sources :
  data/census/serie1.json
  data/census/qid_titles.json
  data/census/mbids.json
  data/census/musicbrainz.json
  data/dumps/mbtables/artist  (noms de groupes, optionnel)

Sortie :
  data/census/catalog_s1.json
  data/census/catalog_s1.sqlite  (--sqlite)

Usage :
  python tools/export_catalog.py
  python tools/export_catalog.py --sqlite
  python tools/export_catalog.py --validate
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from attach_group_names import load_names, pick_principal  # noqa: E402
from score_vivier import display_name  # noqa: E402

CENSUS = ROOT / "data" / "census"
SCHEMA_JSON = ROOT / "data" / "schema" / "catalog.schema.json"
SCHEMA_SQL = ROOT / "data" / "schema" / "catalog.sql"
OUT_JSON = CENSUS / "catalog_s1.json"
OUT_SQLITE = CENSUS / "catalog_s1.sqlite"

SERIES_ID = "s1"
RARITIES = {"commune", "argent", "or", "platine", "diamant"}
STYLES = {"serigraphie", "contrejour", "encre"}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def parse_plate(plaque: str, rec: dict) -> dict | None:
    parts = (plaque or "").split("|")
    if len(parts) < 6:
        return None
    style, instrument, pose_s, costume, venue, sil = parts[:6]
    try:
        pose = int(rec.get("pose") or pose_s)
    except (TypeError, ValueError):
        return None
    style = (rec.get("style") or style or "").strip()
    if style not in STYLES or sil not in ("f", "m", "x"):
        return None
    if not (1 <= pose <= 7):
        return None
    stem = plaque.replace("|", "_")
    # Exécution A/B selon rareté : diamant → souvent B ; le path exact peut varier.
    # On pointe le stem logique ; le runtime résout le fichier.
    return {
        "id": plaque,
        "style": style,
        "instrument": (rec.get("instrument") or instrument).strip(),
        "pose": pose,
        "costume": (rec.get("costume") or costume).strip(),
        "venue": (rec.get("venue") or venue).strip(),
        "sil": sil,
        "path": f"out/illustrations/{stem}",
    }


def build_catalog() -> dict:
    serie1 = load_json(CENSUS / "serie1.json")
    titles = load_json(CENSUS / "qid_titles.json") if (CENSUS / "qid_titles.json").exists() else {}
    mbids = load_json(CENSUS / "mbids.json") if (CENSUS / "mbids.json").exists() else {}
    mb = load_json(CENSUS / "musicbrainz.json") if (CENSUS / "musicbrainz.json").exists() else {}

    artists: dict[str, dict] = {}
    plates: dict[str, dict] = {}
    cards: list[dict] = []
    groups: dict[str, dict] = {}
    memberships: list[dict] = []
    primary_group: dict[str, str | None] = {}
    wanted_group_mbids: set[str] = set()

    for rec in serie1:
        qid = rec["qid"]
        mb_row = mb.get(qid) or {}
        artist_mbid = mb_row.get("mbid") or mbids.get(qid)
        sex = rec.get("silhouette") or None
        if sex not in ("f", "m", "x"):
            sex = None
        artists[qid] = {
            "qid": qid,
            "mbid": artist_mbid or None,
            "name": display_name(qid, titles),
            "sex": sex,
            "instrument": rec.get("instrument") or None,
        }

        plaque = rec.get("plaque") or ""
        plate = parse_plate(plaque, rec)
        if plate is None:
            raise SystemExit(f"Plaque invalide pour {qid}: {plaque!r}")
        plates[plate["id"]] = plate

        g_list = list(mb_row.get("groups") or [])
        primary = pick_principal(g_list)
        primary_group[qid] = primary
        if primary:
            wanted_group_mbids.add(primary)

        seen_g: set[str] = set()
        for g in g_list:
            gmbid = g.get("mbid")
            if not gmbid or gmbid in seen_g:
                continue
            seen_g.add(gmbid)
            wanted_group_mbids.add(gmbid)
            start = g.get("start")
            end = g.get("end")
            memberships.append({
                "artist_qid": qid,
                "group_mbid": gmbid,
                "start": f"{int(start):04d}-01-01" if start else None,
                "end": f"{int(end):04d}-12-31" if end else None,
                "is_primary": gmbid == primary,
            })

        rarity = rec["rarete"]
        if rarity not in RARITIES:
            raise SystemExit(f"Rareté inconnue {rarity!r} pour {qid}")

        cards.append({
            "id": f"{SERIES_ID}:{qid}",
            "series_id": SERIES_ID,
            "artist_qid": qid,
            "rank_in_series": int(rec["rank_serie"]),
            "rank_vivier": int(rec["rank_vivier"]) if rec.get("rank_vivier") else None,
            "rarity_initial": rarity,
            "rarity_current": rarity,
            "family": rec["family"],
            "band": rec["band"],
            "region": rec.get("region"),
            "era": rec.get("era"),
            "motif": rec.get("draft_reason"),
            "plate_id": plate["id"],
            "group_mbid": primary,
            "in_booster_pool": True,
        })

    names = load_names(wanted_group_mbids)
    for gmbid in sorted(wanted_group_mbids):
        groups[gmbid] = {
            "mbid": gmbid,
            "name": names.get(gmbid) or gmbid,
            "qid": None,
        }

    # Drop memberships / card.group_mbid whose group has no row (always have rows now).
    catalog = {
        "version": 1,
        "series": [{
            "id": SERIES_ID,
            "name": "Série 1",
            "size": len(cards),
            "released_at": None,
            "status": "draft",
        }],
        "artists": [artists[q] for q in sorted(artists)],
        "groups": [groups[m] for m in sorted(groups)],
        "memberships": memberships,
        "plates": [plates[p] for p in sorted(plates)],
        "cards": sorted(cards, key=lambda c: c["rank_in_series"]),
        "rarity_events": [],
    }
    return catalog


def write_sqlite(catalog: dict, dest: Path) -> None:
    if dest.exists():
        dest.unlink()
    dest.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(dest)
    con.executescript(SCHEMA_SQL.read_text(encoding="utf-8"))
    cur = con.cursor()

    for s in catalog["series"]:
        cur.execute(
            "INSERT INTO series(id, name, size, released_at, status) VALUES (?,?,?,?,?)",
            (s["id"], s["name"], s["size"], s["released_at"], s["status"]),
        )
    for a in catalog["artists"]:
        cur.execute(
            "INSERT INTO artist(qid, mbid, name, sex, instrument) VALUES (?,?,?,?,?)",
            (a["qid"], a["mbid"], a["name"], a["sex"], a["instrument"]),
        )
    for g in catalog["groups"]:
        cur.execute(
            'INSERT INTO "group"(mbid, name, qid) VALUES (?,?,?)',
            (g["mbid"], g["name"], g["qid"]),
        )
    for p in catalog["plates"]:
        cur.execute(
            "INSERT INTO plate(id, style, instrument, pose, costume, venue, sil, path) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (p["id"], p["style"], p["instrument"], p["pose"], p["costume"],
             p["venue"], p["sil"], p["path"]),
        )
    for m in catalog["memberships"]:
        cur.execute(
            "INSERT INTO membership(artist_qid, group_mbid, start, \"end\", is_primary) "
            "VALUES (?,?,?,?,?)",
            (m["artist_qid"], m["group_mbid"], m["start"], m["end"],
             1 if m["is_primary"] else 0),
        )
    for c in catalog["cards"]:
        cur.execute(
            "INSERT INTO card(id, series_id, artist_qid, rank_in_series, rank_vivier, "
            "rarity_initial, rarity_current, family, band, region, era, motif, "
            "plate_id, group_mbid, in_booster_pool) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                c["id"], c["series_id"], c["artist_qid"], c["rank_in_series"],
                c["rank_vivier"], c["rarity_initial"], c["rarity_current"],
                c["family"], c["band"], c["region"], c["era"], c["motif"],
                c["plate_id"], c["group_mbid"],
                1 if c["in_booster_pool"] else 0,
            ),
        )
    for e in catalog["rarity_events"]:
        cur.execute(
            "INSERT INTO rarity_event(card_id, from_rarity, to_rarity, "
            "series_boundary, effective_at, reason) VALUES (?,?,?,?,?,?)",
            (e["card_id"], e["from_rarity"], e["to_rarity"],
             e["series_boundary"], e["effective_at"], e["reason"]),
        )
    con.commit()
    con.close()


def validate_catalog(catalog: dict) -> list[str]:
    errors: list[str] = []
    if catalog.get("version") != 1:
        errors.append("version != 1")
    cards = catalog["cards"]
    if len(cards) != catalog["series"][0]["size"]:
        errors.append("series.size != len(cards)")
    artist_ids = {a["qid"] for a in catalog["artists"]}
    plate_ids = {p["id"] for p in catalog["plates"]}
    group_ids = {g["mbid"] for g in catalog["groups"]}
    ranks = set()
    for c in cards:
        if c["artist_qid"] not in artist_ids:
            errors.append(f"card {c['id']}: artist manquant")
        if c["plate_id"] not in plate_ids:
            errors.append(f"card {c['id']}: plate manquante")
        if c["group_mbid"] and c["group_mbid"] not in group_ids:
            errors.append(f"card {c['id']}: group_mbid inconnu")
        if c["rarity_initial"] not in RARITIES or c["rarity_current"] not in RARITIES:
            errors.append(f"card {c['id']}: rareté invalide")
        if c["rank_in_series"] in ranks:
            errors.append(f"rank dupliqué {c['rank_in_series']}")
        ranks.add(c["rank_in_series"])
        if not c["id"].endswith(":" + c["artist_qid"]):
            errors.append(f"card id mal formé {c['id']}")
    for m in catalog["memberships"]:
        if m["artist_qid"] not in artist_ids:
            errors.append(f"membership artist {m['artist_qid']}")
        if m["group_mbid"] not in group_ids:
            errors.append(f"membership group {m['group_mbid']}")
    for p in catalog["plates"]:
        if p["style"] not in STYLES:
            errors.append(f"plate style {p['style']}")

    # JSON Schema si jsonschema est dispo
    if SCHEMA_JSON.exists():
        try:
            import jsonschema  # type: ignore
            schema = load_json(SCHEMA_JSON)
            jsonschema.validate(catalog, schema)
        except ImportError:
            pass
        except Exception as exc:  # noqa: BLE001
            errors.append(f"jsonschema: {exc}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sqlite", action="store_true", help=f"Écrit aussi {OUT_SQLITE}")
    ap.add_argument("--validate", action="store_true", help="Valide après export")
    ap.add_argument("-o", "--output", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    if not (CENSUS / "serie1.json").exists():
        print("Manque data/census/serie1.json — lance d'abord draft_serie1.py", file=sys.stderr)
        return 1

    catalog = build_catalog()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Écrit {args.output.relative_to(ROOT)} — "
        f"{len(catalog['cards'])} cartes, "
        f"{len(catalog['artists'])} artistes, "
        f"{len(catalog['plates'])} plaques, "
        f"{len(catalog['groups'])} groupes, "
        f"{len(catalog['memberships'])} appartenances"
    )

    if args.sqlite:
        write_sqlite(catalog, OUT_SQLITE)
        print(f"Écrit {OUT_SQLITE.relative_to(ROOT)}")

    errs = validate_catalog(catalog)
    if errs:
        print("Validation ÉCHEC :", file=sys.stderr)
        for e in errs[:30]:
            print(f"  - {e}", file=sys.stderr)
        if len(errs) > 30:
            print(f"  … +{len(errs) - 30}", file=sys.stderr)
        return 1
    print("Validation OK" + (" (jsonschema)" if args.validate else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
