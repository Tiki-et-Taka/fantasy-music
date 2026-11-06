"""
Admission coattail — bassistes / batteurs de groupes prestigieux.

Problème : le vivier exige des sitelinks Wiki perso élevés. Les rhythm sections
de groupes cultes ont souvent une fiche pauvre alors que le chanteur est fort.

Remède : pour chaque groupe MusicBrainz ancré par un membre déjà « icônes/connus »
(ou sitelinks élevés), admettre les autres membres basse/batterie même sous le
seuil sitelinks standard, s'ils ont un MBID Wikidata et un minimum de présence.

Usage :
  python tools/coattail_rhythm.py
  python tools/coattail_rhythm.py --dry-run
  python tools/coattail_rhythm.py --merge   # réécrit eligible.json

Ensuite : fetch_mbids (nouveaux QID) → score_vivier → attach_illustration (ranking).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from attach_illustration import (  # noqa: E402
    OCC_INSTR,
    prefetch_parents,
    resolve_instrument,
)
from census_vivier import (  # noqa: E402
    CFG,
    SPARQL,
    UA,
    best_family,
    era_of,
    prefetch_genre_parents,
    region_of,
)
from ingest_musicbrainz_dump import (  # noqa: E402
    iter_rows,
    load_link_types,
    load_links,
    year,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CENSUS = ROOT / "data" / "census"
TABLES = ROOT / "data" / "dumps" / "mbtables"
CACHE = ROOT / "data" / "cache" / "coattail"

OCC_HARD = {k: v for k, v in (OCC_INSTR or {}).items() if v and v != "voix"}


def coat_cfg() -> dict:
    return dict(CFG.get("coattail_rhythm") or {})


def fetch_sparql(query: str, key: str) -> list[dict]:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{key}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    req = urllib.request.Request(
        SPARQL,
        data=body,
        headers={
            "User-Agent": UA,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            rows = data.get("results", {}).get("bindings", [])
            path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            return rows
        except Exception as exc:
            wait = 8 * (attempt + 1)
            print(f"  SPARQL {type(exc).__name__}, pause {wait}s ({key})", flush=True)
            time.sleep(wait)
    return []


def qid_of(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def prestige_groups(
    eligible: list[dict],
    mb: dict,
    *,
    anchor_bands: set[str],
    min_anchor_sitelinks: int,
) -> dict[str, dict]:
    """gmbid → {anchor_qid, anchor_sl, family_mode, member_qids}."""
    by_group: dict[str, list[tuple[str, int, str, str]]] = defaultdict(list)
    for rec in eligible:
        qid = rec["qid"]
        info = mb.get(qid) or {}
        for g in info.get("groups") or []:
            gmbid = g.get("mbid")
            if not gmbid:
                continue
            by_group[gmbid].append((
                qid,
                int(rec.get("sitelinks") or 0),
                rec.get("band") or "",
                rec.get("family") or "",
            ))

    out: dict[str, dict] = {}
    for gmbid, members in by_group.items():
        members.sort(key=lambda t: t[1], reverse=True)
        top_qid, top_sl, top_band, _ = members[0]
        if top_band not in anchor_bands and top_sl < min_anchor_sitelinks:
            continue
        fams = Counter(f for *_, f in members if f)
        family = fams.most_common(1)[0][0] if fams else "rock"
        out[gmbid] = {
            "anchor_qid": top_qid,
            "anchor_sitelinks": top_sl,
            "anchor_band": top_band,
            "family": family,
            "known_qids": {q for q, *_ in members},
        }
    return out


def load_artist_indexes(wanted_group_mbids: set[str]) -> tuple[dict[str, int], dict[int, str]]:
    """Charge id↔mbid ; mbid_to_id seulement pour les groupes prestige (rapide)."""
    mbid_to_id: dict[str, int] = {}
    id_to_mbid: dict[int, str] = {}
    print("  Scan artist (index MBID)…", flush=True)
    n = 0
    for cols in iter_rows(TABLES, "artist"):
        n += 1
        if len(cols) < 2:
            continue
        aid = int(cols[0])
        gid = cols[1]
        id_to_mbid[aid] = gid
        if gid in wanted_group_mbids:
            mbid_to_id[gid] = aid
        if n % 1_000_000 == 0:
            print(f"    {n/1e6:.1f} M  groupes={len(mbid_to_id)}", flush=True)
    print(f"    {n} artistes, {len(mbid_to_id)} groupes prestige indexés", flush=True)
    return mbid_to_id, id_to_mbid


def members_of_groups(
    group_ids: set[int],
    links: dict,
) -> dict[int, list[tuple[int, int | None, int | None]]]:
    """group_id → [(member_id, start, end), ...]."""
    out: dict[int, list[tuple[int, int | None, int | None]]] = defaultdict(list)
    print("  Scan l_artist_artist (membres des groupes prestige)…", flush=True)
    n = hit = 0
    for cols in iter_rows(TABLES, "l_artist_artist"):
        n += 1
        if len(cols) < 4:
            continue
        link_id = int(cols[1])
        if link_id not in links:
            continue
        entity0, entity1 = int(cols[2]), int(cols[3])
        _, start, end = links[link_id]
        if entity1 in group_ids:
            out[entity1].append((entity0, start, end))
            hit += 1
        if n % 2_000_000 == 0:
            print(f"    {n/1e6:.1f} M rels  hits={hit}", flush=True)
    print(f"    {hit} memberships sur {len(out)} groupes", flush=True)
    return out


def resolve_mbids_to_wikidata(mbids: list[str]) -> dict[str, dict]:
    """mbid → {qid, sitelinks, genres, countries, start, birth, instruments, occupations}."""
    out: dict[str, dict] = {}
    batch = 80
    for i in range(0, len(mbids), batch):
        chunk = mbids[i : i + batch]
        values = " ".join(f'"{m}"' for m in chunk)
        query = f"""
        SELECT ?mbid ?item ?sl ?genre ?country ?start ?birth ?instr ?occ WHERE {{
          VALUES ?mbid {{ {values} }}
          ?item wdt:P434 ?mbid .
          ?item wdt:P31 wd:Q5 .
          OPTIONAL {{ ?item wikibase:sitelinks ?sl }}
          OPTIONAL {{ ?item wdt:P136 ?genre }}
          OPTIONAL {{ ?item wdt:P27 ?country }}
          OPTIONAL {{ ?item wdt:P2031 ?start }}
          OPTIONAL {{ ?item wdt:P569 ?birth }}
          OPTIONAL {{ ?item wdt:P1303 ?instr }}
          OPTIONAL {{ ?item wdt:P106 ?occ }}
        }}
        """
        key = f"mbid_batch_{i // batch:04d}"
        rows = fetch_sparql(query, key)
        for row in rows:
            mbid = row.get("mbid", {}).get("value") or ""
            qid = qid_of(row.get("item", {}).get("value", ""))
            if not mbid or not qid.startswith("Q"):
                continue
            rec = out.get(mbid)
            if rec is None:
                rec = {
                    "qid": qid,
                    "mbid": mbid,
                    "sitelinks": 0,
                    "genres": [],
                    "countries": [],
                    "start": None,
                    "birth": None,
                    "instruments": [],
                    "occupations": [],
                }
                out[mbid] = rec
            sl = int(row.get("sl", {}).get("value") or 0)
            if sl > rec["sitelinks"]:
                rec["sitelinks"] = sl
            for key_bind, bucket in (("genre", "genres"), ("country", "countries"),
                                     ("instr", "instruments"), ("occ", "occupations")):
                uri = row.get(key_bind, {}).get("value", "")
                q = qid_of(uri) if uri else ""
                if q.startswith("Q") and q not in rec[bucket]:
                    rec[bucket].append(q)
            for key_bind, field in (("start", "start"), ("birth", "birth")):
                raw = row.get(key_bind, {}).get("value")
                if not raw:
                    continue
                try:
                    y = int(str(raw).lstrip("+")[:4])
                except ValueError:
                    continue
                if 1800 <= y <= 2030 and (rec[field] is None or y < rec[field]):
                    rec[field] = y
        print(f"  Wikidata MBIDs {i + len(chunk)}/{len(mbids)} → {len(out)} résolus", flush=True)
        time.sleep(1.0)
    return out


def instrument_family(instr_qids: list[str], occ_qids: list[str]) -> str | None:
    for occ in occ_qids:
        fam = OCC_HARD.get(occ)
        if fam in ("basse", "batterie"):
            return fam
    prefetch_parents(set(instr_qids))
    resolved = []
    for iq in instr_qids:
        fam = resolve_instrument(iq)
        if fam and fam not in resolved:
            resolved.append(fam)
    for fam in ("basse", "batterie"):
        if fam in resolved:
            return fam
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="n'écrit pas eligible.json")
    ap.add_argument("--merge", action="store_true", help="fusionne dans eligible.json")
    ap.add_argument("--skip-sparql", action="store_true", help="réutilise le cache SPARQL seulement")
    args = ap.parse_args()
    cfg = coat_cfg()
    if not cfg.get("enabled", True):
        print("coattail_rhythm désactivé dans census_config.json")
        return 0

    instruments = set(cfg.get("instruments") or ["basse", "batterie"])
    anchor_bands = set(cfg.get("anchor_bands") or ["icones", "connus"])
    min_anchor_sl = int(cfg.get("min_anchor_sitelinks") or 40)
    min_member_sl = int(cfg.get("min_member_sitelinks") or 1)
    min_years = int(cfg.get("min_years") or 1)
    excluded = set(CFG.get("artist_exclude") or [])

    eligible = json.loads((CENSUS / "eligible.json").read_text(encoding="utf-8"))
    mb = json.loads((CENSUS / "musicbrainz.json").read_text(encoding="utf-8"))
    already = {r["qid"] for r in eligible}

    prestige = prestige_groups(
        eligible, mb,
        anchor_bands=anchor_bands,
        min_anchor_sitelinks=min_anchor_sl,
    )
    print(f"Groupes prestige : {len(prestige)}", flush=True)
    if not prestige:
        print("Aucun groupe prestige — rien à faire")
        return 0

    if not TABLES.exists():
        print(f"Tables MB absentes : {TABLES} — lance ingest_musicbrainz_dump.py --skip-download", file=sys.stderr)
        return 1

    keep_types, _ = load_link_types(TABLES)
    links = load_links(TABLES, keep_types)
    mbid_to_gid, id_to_mbid = load_artist_indexes(set(prestige))
    group_ids = {mbid_to_gid[m] for m in prestige if m in mbid_to_gid}
    print(f"Groupes trouvés dans le dump : {len(group_ids)}/{len(prestige)}", flush=True)

    memberships = members_of_groups(group_ids, links)

    # Candidats MBID absents du vivier
    known_mbids = set()
    for qid in already:
        info = mb.get(qid) or {}
        if info.get("mbid"):
            known_mbids.add(info["mbid"])
    # also mbids.json
    mbids_path = CENSUS / "mbids.json"
    if mbids_path.exists():
        known_mbids.update(json.loads(mbids_path.read_text(encoding="utf-8")).values())

    candidate_mbids: dict[str, dict] = {}
    for gmbid, meta in prestige.items():
        gid = mbid_to_gid.get(gmbid)
        if gid is None:
            continue
        for member_id, start, end in memberships.get(gid, []):
            mmbid = id_to_mbid.get(member_id)
            if not mmbid or mmbid in known_mbids:
                continue
            years = 0
            if start:
                years = max(0, (end or 2026) - start)
            if years < min_years and start is not None:
                continue
            # sans date : on laisse passer (contribution par albums plus tard)
            prev = candidate_mbids.get(mmbid)
            if prev is None or years > prev["years"]:
                candidate_mbids[mmbid] = {
                    "mbid": mmbid,
                    "group_mbid": gmbid,
                    "years": years,
                    "start": start,
                    "end": end,
                    "family": meta["family"],
                    "anchor_qid": meta["anchor_qid"],
                }

    print(f"Candidats MB (hors vivier) : {len(candidate_mbids)}", flush=True)
    if not candidate_mbids:
        print("Aucun candidat")
        return 0

    cache_path = CACHE / "resolved_mbids.json"
    if args.skip_sparql and cache_path.exists():
        resolved = json.loads(cache_path.read_text(encoding="utf-8"))
        print(f"Cache SPARQL : {len(resolved)} MBIDs", flush=True)
    else:
        resolved = resolve_mbids_to_wikidata(sorted(candidate_mbids))
        CACHE.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(resolved, ensure_ascii=False), encoding="utf-8")

    # Genres → familles
    all_genres = {g for rec in resolved.values() for g in rec.get("genres") or []}
    prefetch_genre_parents(all_genres)

    admitted: list[dict] = []
    rejected = Counter()
    for mbid, cand in candidate_mbids.items():
        wd = resolved.get(mbid)
        if not wd:
            rejected["pas de wikidata"] += 1
            continue
        qid = wd["qid"]
        if qid in already or qid in excluded:
            rejected["deja / veto"] += 1
            continue
        if int(wd.get("sitelinks") or 0) < min_member_sl:
            rejected["sitelinks trop bas"] += 1
            continue
        fam_instr = instrument_family(wd.get("instruments") or [], wd.get("occupations") or [])
        if fam_instr not in instruments:
            rejected["pas basse/batterie"] += 1
            continue
        family = best_family(wd.get("genres") or []) or cand["family"]
        if family is None:
            rejected["genre exclu"] += 1
            continue
        admitted.append({
            "qid": qid,
            "sitelinks": int(wd.get("sitelinks") or 0),
            "family": family,
            "region": region_of(wd.get("countries") or []),
            "countries": list(wd.get("countries") or []),
            "era": era_of(wd.get("start"), wd.get("birth")),
            "admission": "coattail_rhythm",
            "coattail_instrument": fam_instr,
            "coattail_group_mbid": cand["group_mbid"],
            "coattail_anchor_qid": cand["anchor_qid"],
            "mbid": mbid,
        })

    # Dédup QID (garder le plus de sitelinks)
    by_qid: dict[str, dict] = {}
    for rec in admitted:
        prev = by_qid.get(rec["qid"])
        if prev is None or rec["sitelinks"] > prev["sitelinks"]:
            by_qid[rec["qid"]] = rec
    admitted = sorted(by_qid.values(), key=lambda r: -r["sitelinks"])

    instr_c = Counter(r["coattail_instrument"] for r in admitted)
    print(f"\nAdmis coattail : {len(admitted)}")
    for k, v in instr_c.most_common():
        print(f"  {k:12} {v}")
    print("Rejets :", dict(rejected))

    out_path = CENSUS / "coattail_rhythm.json"
    payload = {
        "version": 1,
        "config": cfg,
        "prestige_groups": len(prestige),
        "admitted": admitted,
        "rejected": dict(rejected),
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Écrit : {out_path.relative_to(ROOT)}")

    if args.dry_run or not args.merge:
        print("Astuce : relance avec --merge pour fusionner dans eligible.json")
        return 0

    # Merge eligible (idempotent)
    existing_q = {r["qid"] for r in eligible}
    added = 0
    for rec in admitted:
        if rec["qid"] in existing_q:
            continue
        eligible.append({
            "qid": rec["qid"],
            "sitelinks": rec["sitelinks"],
            "family": rec["family"],
            "region": rec["region"],
            "countries": rec.get("countries") or [],
            "era": rec["era"],
            "admission": "coattail_rhythm",
            "coattail_instrument": rec["coattail_instrument"],
            "coattail_group_mbid": rec["coattail_group_mbid"],
        })
        existing_q.add(rec["qid"])
        added += 1

    if added:
        eligible.sort(key=lambda r: int(r.get("sitelinks") or 0), reverse=True)
        n = len(eligible) or 1
        for i, r in enumerate(eligible):
            p = (i + 1) / n
            if p <= 0.03:
                r["band"] = "icones"
            elif p <= 0.15:
                r["band"] = "connus"
            elif p <= 0.50:
                r["band"] = "scene"
            elif p <= 0.80:
                r["band"] = "deep"
            else:
                r["band"] = "exclu"
        (CENSUS / "eligible.json").write_text(
            json.dumps(eligible, ensure_ascii=False, indent=2), encoding="utf-8",
        )
    print(f"eligible.json : +{added}  total={len(eligible)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
