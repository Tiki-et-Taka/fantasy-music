"""Mappe sexe + instrument, puis accroche la plaque aux cartes Série 1 / ranking."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
import urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from census_vivier import CFG, SPARQL, fetch_json, qid_of  # noqa: E402
from score_vivier import FAMILY_LABEL, display_name  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CENSUS = ROOT / "data" / "census"
SEX_MAP = CFG["sex_map"]
INSTR_SEED = dict(CFG["instrument_seed"])
INSTR_PRIO = CFG["instrument_priority"]
OCC_PRIO = ["batterie", "basse", "machines", "vents", "cordes", "guitare", "claviers", "voix"]
OCC_INSTR = CFG.get("occupation_instrument") or {}
MAJORITY_PRIO = ["basse", "guitare", "batterie", "vents", "cordes", "machines", "claviers", "voix"]
VOCAL_FAMILIES = frozenset({"pop", "chanson", "rnb", "hiphop", "funk"})
GUITAR_FAMILIES = frozenset({
    "rock", "metal", "blues", "country", "folk", "reggae", "punk", "latin", "world", "afro",
})
POSE_COUNT = 7
ILLU_CATALOG = json.loads((ROOT / "tools" / "illustration_catalog.json").read_text(encoding="utf-8"))
EXEC_OF = ILLU_CATALOG["exec_of_rarete"]
HEADS_ALL = ILLU_CATALOG["heads"]
HEADS_COSTUME = ILLU_CATALOG.get("heads_for_costume") or {}
STOCK_DIR = ROOT / "out" / "illustrations"
REJECTS_PATH = CENSUS / "illustration_rejects.json"
VENUE_ORDER = ["stade", "festival", "salle", "cave", "club"]
COSTUME_ORDER = ["pre1960", "1960s", "1970s80s", "1990s00s", "2010s"]
FEMININE_HEAD = ("bun", "beehive", "knot at the back")
MASCULINE_HEAD = ("buzz cut", "short fade", "undercut", "shaved sides", "baseball cap")
_stock: set[str] | None = None
_rejects: set[str] | None = None
_stock_stats: Counter[str] = Counter()

ERA_COSTUME = {
    "pre1970": "1960s",
    "1970s80s": "1970s80s",
    "1990s00s": "1990s00s",
    "2010s": "2010s",
}
VENUE_OF = {
    "icones": "stade",
    "connus": "festival",
    "scene": "salle",
    "deep": "cave",
}
STYLE_OF = {
    "commune": "serigraphie",
    "argent": "serigraphie",
    "or": "contrejour",
    "platine": "contrejour",
    "diamant": "encre",
}

_parents: dict[str, list[str]] = {}
_resolved: dict[str, str | None] = dict(INSTR_SEED)


def prefetch_parents(qids: set[str]) -> None:
    pending = {q for q in qids if q not in _parents and q not in _resolved}
    for _depth in range(6):
        if not pending:
            break
        batch_ids = sorted(pending)
        pending = set()
        print(f"   lot P279 instruments : {len(batch_ids)} QID", flush=True)
        for i in range(0, len(batch_ids), 150):
            batch = batch_ids[i:i + 150]
            values = " ".join(f"wd:{q}" for q in batch)
            query = f"""
            SELECT ?g ?parent WHERE {{
              VALUES ?g {{ {values} }}
              OPTIONAL {{ ?g wdt:P279 ?parent }}
            }}
            """
            body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
            data = fetch_json(SPARQL, f"sparql_p279_instr_{batch[0]}_{batch[-1]}_{len(batch)}", data=body)
            found: dict[str, list[str]] = {q: [] for q in batch}
            for row in (data or {}).get("results", {}).get("bindings", []):
                g = qid_of(row.get("g", {}).get("value", ""))
                p = qid_of(row.get("parent", {}).get("value", ""))
                if g.startswith("Q") and p.startswith("Q") and p not in found.get(g, []):
                    found.setdefault(g, []).append(p)
            for qid, parents in found.items():
                _parents[qid] = parents
                for p in parents:
                    if p not in _parents and p not in _resolved:
                        pending.add(p)
            time.sleep(1.2)


def resolve_instrument(qid: str, depth: int = 0) -> str | None:
    if qid in _resolved:
        return _resolved[qid]
    if depth > 8:
        _resolved[qid] = None
        return None
    for parent in _parents.get(qid, []):
        hit = resolve_instrument(parent, depth + 1)
        if hit:
            _resolved[qid] = hit
            return hit
    _resolved[qid] = None
    return None


def silhouette_of(sex_qids: list[str]) -> str:
    for qid in sex_qids:
        if qid in SEX_MAP:
            return SEX_MAP[qid]
    return ""


def pick_family(families: list[str], order: list[str] | None = None) -> str:
    rank = {name: i for i, name in enumerate(order or INSTR_PRIO)}
    families = [f for f in families if f]
    families.sort(key=lambda f: rank.get(f, 99))
    return families[0] if families else ""


def majority_instrument(families: list[str]) -> str:
    extra = [f for f in families if f and f != "voix"]
    if not extra:
        return ""
    counts = Counter(extra)
    best = max(counts.values())
    candidates = [f for f, n in counts.items() if n == best]
    rank = {name: i for i, name in enumerate(MAJORITY_PRIO)}
    candidates.sort(key=lambda f: rank.get(f, 99))
    return candidates[0]


def instrument_of(
    instr_qids: list[str],
    occupations: list[str] | None = None,
    qid: str | None = None,
    family: str | None = None,
    previous: str | None = None,
) -> str:
    forced = (CFG.get("artist_instrument_override") or {}).get(qid or "")
    if forced:
        return forced

    occ_fams: list[str] = []
    for occ in occupations or []:
        fam = OCC_INSTR.get(occ)
        if fam and fam not in occ_fams:
            occ_fams.append(fam)

    resolved: list[str] = []
    unique: list[str] = []
    for instr_qid in instr_qids:
        fam = resolve_instrument(instr_qid)
        if not fam:
            continue
        resolved.append(fam)
        if fam not in unique:
            unique.append(fam)

    singer = "voix" in occ_fams or "voix" in unique
    family = family or ""
    previous = previous or ""

    if "basse" in occ_fams:
        return "basse"

    if family == "electro":
        if "machines" in occ_fams:
            return "machines"
        if not singer and (not resolved or set(resolved) <= {"voix", "claviers", "guitare"}):
            return "machines"

    if family in VOCAL_FAMILIES:
        return "voix"

    if singer:
        if family == "electro":
            return "voix"
        if family == "jazz":
            return majority_instrument(resolved) or (
                previous if previous in MAJORITY_PRIO else "voix"
            )
        if family in GUITAR_FAMILIES:
            if "guitare" in occ_fams or "guitare" in unique:
                return "guitare"
            hit = majority_instrument(resolved)
            if hit:
                return hit
            if previous in MAJORITY_PRIO and previous != "voix":
                return previous
            return "voix"
        return "voix"

    hit = majority_instrument(resolved)
    if hit:
        return hit
    if family == "electro":
        return "machines"
    if previous:
        return previous
    role = [f for f in occ_fams if f != "voix"]
    if role:
        return pick_family(role, OCC_PRIO)
    return "voix"


def pose_of(qid: str) -> int:
    forced = (CFG.get("artist_pose_override") or {}).get(qid)
    if forced:
        return int(forced)
    return (int(qid[1:]) % POSE_COUNT) + 1


def costume_of(era: str | None, peak_year: int | None = None) -> str:
    if era == "pre1970" and peak_year is not None and peak_year < 1960:
        return "pre1960"
    return ERA_COSTUME.get(era or "", "1990s00s")


def load_stock() -> set[str]:
    global _stock
    if _stock is None:
        if STOCK_DIR.exists():
            _stock = {p.stem for p in STOCK_DIR.glob("*.png") if p.is_file()}
        else:
            _stock = set()
    return _stock


def load_rejects() -> set[str]:
    global _rejects
    if _rejects is None:
        _rejects = set()
        if REJECTS_PATH.exists():
            try:
                data = json.loads(REJECTS_PATH.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                data = {}
            _rejects = {k for k, v in data.items() if v == "reject"}
    return _rejects


def illustration_stem(
    style: str, exec_id: str, instr: str, pose: int,
    costume: str, venue: str, sil: str,
) -> str:
    return f"{style}_{exec_id}_{instr}_{pose}_{costume}_{venue}_{sil}"


def generated_head(jid: str, costume: str) -> str:
    pool = HEADS_COSTUME.get(costume) or HEADS_ALL
    idx = int(hashlib.md5(f"{jid}|head".encode("utf-8")).hexdigest(), 16) % len(pool)
    return pool[idx]


def head_ok_for_silhouette(jid: str, costume: str, sil: str) -> bool:
    head = generated_head(jid, costume).lower()
    if sil == "m":
        return not any(marker in head for marker in FEMININE_HEAD)
    if sil == "f":
        return not any(marker in head for marker in MASCULINE_HEAD)
    return True


def plaque_stems(
    style: str, exec_id: str, instr: str, pose: int,
    costume: str, venue: str, sil: str,
) -> list[str]:
    other = "B" if exec_id == "A" else "A"
    return [
        illustration_stem(style, exec_id, instr, pose, costume, venue, sil),
        illustration_stem(style, other, instr, pose, costume, venue, sil),
    ]


def plaque_resolved_stem(
    style: str, exec_id: str, instr: str, pose: int,
    costume: str, venue: str, sil: str,
) -> str | None:
    stock = load_stock()
    rejects = load_rejects()
    stems = plaque_stems(style, exec_id, instr, pose, costume, venue, sil)
    if not stock:
        return stems[0]
    for stem in stems:
        if stem in rejects:
            continue
        # Fichier déjà généré : on le prend (le filtre tête ne doit pas
        # invalider un PNG mythique qu'on vient de produire).
        if stem in stock:
            return stem
    return None


def plaque_usable(
    style: str, exec_id: str, instr: str, pose: int,
    costume: str, venue: str, sil: str,
    taken: set[str] | None = None,
) -> bool:
    stem = plaque_resolved_stem(style, exec_id, instr, pose, costume, venue, sil)
    if stem is None:
        return False
    if taken and stem in taken:
        return False
    return True


def parse_stock_stem(stem: str) -> tuple[str, str, str, int, str, str, str] | None:
    bits = stem.split("_")
    if len(bits) < 7:
        return None
    try:
        pose = int(bits[3])
    except ValueError:
        return None
    return bits[0], bits[1], bits[2], pose, "_".join(bits[4:-2]), bits[-2], bits[-1]


def iter_stock_plaques(
    style: str | None = None,
    instr: str | None = None,
    sil: str | None = None,
):
    seen: set[tuple] = set()
    for stem in sorted(load_stock()):
        parsed = parse_stock_stem(stem)
        if parsed is None:
            continue
        st, _ex, ins, pose, costume, venue, silhouette = parsed
        if style and st != style:
            continue
        if instr and ins != instr:
            continue
        if sil and silhouette != sil:
            continue
        key = (st, ins, pose, costume, venue, silhouette)
        if key in seen:
            continue
        seen.add(key)
        yield key


def _rotate(seq: list[str] | range, first) -> list:
    items = list(seq)
    if first in items:
        return [first] + [x for x in items if x != first]
    return [first] + items


def costumes_near(first: str) -> list[str]:
    if first not in COSTUME_ORDER:
        return _rotate(COSTUME_ORDER, first)
    i = COSTUME_ORDER.index(first)
    others = [c for c in COSTUME_ORDER if c != first]
    others.sort(key=lambda c: abs(COSTUME_ORDER.index(c) - i))
    return [first] + others


def fit_illustration(
    rec: dict, taken: set[str] | None = None,
) -> tuple[str, str, int, str, str, str]:
    sil = rec.get("silhouette") or "x"
    instr = rec.get("instrument") or "voix"
    costume = rec.get("costume") or costume_of(
        rec.get("era_peak") or rec.get("era"), rec.get("peak_year")
    )
    venue = rec.get("venue") or VENUE_OF.get(rec.get("band") or rec.get("draft_band") or "", "salle")
    style = rec.get("style") or STYLE_OF.get(rec.get("rarete") or "", "serigraphie")
    pose = int(rec.get("pose") or pose_of(rec["qid"]))
    exec_id = EXEC_OF.get(rec.get("rarete") or "", "A")

    def ok(st, ins, p, c, v, s) -> bool:
        return plaque_usable(st, exec_id, ins, p, c, v, s, taken=taken)

    forced = (CFG.get("artist_plaque_override") or {}).get(rec.get("qid") or "")
    if forced:
        parts = str(forced).split("|")
        if len(parts) == 6:
            try:
                f_pose = int(parts[2])
            except ValueError:
                f_pose = pose
            f_style, f_instr, f_costume, f_venue, f_sil = (
                parts[0], parts[1], parts[3], parts[4], parts[5]
            )
            if f_style == style and ok(
                f_style, f_instr, f_pose, f_costume, f_venue, f_sil
            ):
                return f_style, f_instr, f_pose, f_costume, f_venue, f_sil

    if ok(style, instr, pose, costume, venue, sil):
        return style, instr, pose, costume, venue, sil

    poses = _rotate(range(1, POSE_COUNT + 1), pose)
    venues = _rotate(VENUE_ORDER, venue)
    costumes = costumes_near(costume)

    for p in poses:
        if ok(style, instr, p, costume, venue, sil):
            _stock_stats["pose"] += 1
            return style, instr, p, costume, venue, sil
    for v in venues:
        for p in poses:
            if ok(style, instr, p, costume, v, sil):
                _stock_stats["venue"] += 1
                return style, instr, p, costume, v, sil
    for c in costumes:
        if c == costume:
            continue
        for v in venues:
            for p in poses:
                if ok(style, instr, p, c, v, sil):
                    _stock_stats["costume"] += 1
                    return style, instr, p, c, v, sil

    if sil == "x":
        for c in costumes:
            for v in venues:
                for p in poses:
                    if ok(style, instr, p, c, v, "m"):
                        _stock_stats["sil"] += 1
                        return style, instr, p, c, v, "m"

    for st, ins, p, c, v, s in iter_stock_plaques(style=style, instr=instr, sil=sil):
        if ok(st, ins, p, c, v, s):
            _stock_stats["stock"] += 1
            return st, ins, p, c, v, s

    if taken:
        _stock_stats["shared"] += 1
        return style, instr, pose, costume, venue, sil

    _stock_stats["unresolved"] += 1
    return style, instr, pose, costume, venue, sil


def resolved_plaque_stem(rec: dict) -> str | None:
    parts = (rec.get("plaque") or "").split("|")
    if len(parts) != 6:
        return None
    return plaque_resolved_stem(
        parts[0],
        EXEC_OF.get(rec.get("rarete") or "", "A"),
        parts[1],
        int(parts[2]),
        parts[3],
        parts[4],
        parts[5],
    )


def plaque_of(rec: dict, taken: set[str] | None = None) -> str:
    style, instr, pose, costume, venue, sil = fit_illustration(rec, taken=taken)
    rec["style"] = style
    rec["pose"] = pose
    rec["costume"] = costume
    rec["venue"] = venue
    return f"{style}|{instr}|{pose}|{costume}|{venue}|{sil}"


def main() -> int:
    global _stock_stats, _rejects
    _stock_stats = Counter()
    _rejects = None
    remap_only = "--remap" in sys.argv
    raw_path = CENSUS / "illustration_raw.json"
    if not raw_path.exists():
        print("illustration_raw.json manquant — lancer fetch_illustration_attrs.py")
        return 1
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    occ_path = CENSUS / "occupations.json"
    occupations = json.loads(occ_path.read_text(encoding="utf-8")) if occ_path.exists() else {}
    scores_path = CENSUS / "scores.json"
    scores = json.loads(scores_path.read_text(encoding="utf-8"))
    family_of = {rec["qid"]: rec.get("family") or "" for rec in scores}
    prev_path = CENSUS / "illustration.json"
    previous_of = {}
    if prev_path.exists():
        previous_of = {
            q: (v.get("instrument") or "")
            for q, v in json.loads(prev_path.read_text(encoding="utf-8")).items()
        }
    if not remap_only:
        all_instr = {q for rec in raw.values() for q in rec.get("instruments") or []}
        prefetch_parents(all_instr)

    mapped: dict[str, dict] = {}
    changed = 0
    for qid, rec in raw.items():
        sil = silhouette_of(rec.get("sex") or [])
        previous = previous_of.get(qid) or ""
        instr = instrument_of(
            rec.get("instruments") or [],
            occupations.get(qid) or [],
            qid=qid,
            family=family_of.get(qid),
            previous=previous,
        ) or "voix"
        if previous and instr != previous:
            changed += 1
        mapped[qid] = {
            "sex_qids": rec.get("sex") or [],
            "instrument_qids": rec.get("instruments") or [],
            "silhouette": sil,
            "instrument": instr,
            "instrument_source": instr,
        }
    (CENSUS / "illustration.json").write_text(
        json.dumps(mapped, ensure_ascii=False), encoding="utf-8"
    )

    peak_path = CENSUS / "peak_era.json"
    peaks = json.loads(peak_path.read_text(encoding="utf-8")) if peak_path.exists() else {}

    for rec in scores:
        info = mapped.get(rec["qid"], {})
        peak = peaks.get(rec["qid"]) or {}
        rec["silhouette"] = info.get("silhouette") or ""
        rec["instrument"] = info.get("instrument") or "voix"
        rec["era_start"] = peak.get("era_start") or rec.get("era")
        rec["era_peak"] = peak.get("era_peak") or rec.get("era")
        rec["peak_year"] = peak.get("peak_year")
    scores_path.write_text(json.dumps(scores, ensure_ascii=False), encoding="utf-8")

    titles_path = CENSUS / "qid_titles.json"
    titles = json.loads(titles_path.read_text(encoding="utf-8")) if titles_path.exists() else {}
    ranking_path = ROOT / "docs" / "vivier-ranking.csv"
    with ranking_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(["rang", "artiste", "famille", "sexe", "instrument", "nationalite"])
        for rec in scores:
            writer.writerow([
                rec["rank"],
                display_name(rec["qid"], titles),
                FAMILY_LABEL.get(rec["family"], rec["family"]),
                rec.get("silhouette") or "",
                rec.get("instrument") or "",
                rec.get("nationality") or "",
            ])

    serie_path = CENSUS / "serie1.json"
    if serie_path.exists():
        serie = json.loads(serie_path.read_text(encoding="utf-8"))
        serie.sort(key=lambda r: r.get("rank_serie") or 0)
        for rec in serie:
            info = mapped.get(rec["qid"], {})
            peak = peaks.get(rec["qid"]) or {}
            rec["silhouette"] = info.get("silhouette") or rec.get("silhouette") or ""
            rec["instrument"] = instrument_of(
                (raw.get(rec["qid"]) or {}).get("instruments") or [],
                occupations.get(rec["qid"]) or [],
                qid=rec["qid"],
                family=rec.get("family"),
                previous=rec.get("instrument"),
            ) or "voix"
            rec["era_start"] = peak.get("era_start") or rec.get("era")
            rec["era_peak"] = peak.get("era_peak") or rec.get("era")
            rec["peak_year"] = peak.get("peak_year")
            rec["pose"] = pose_of(rec["qid"])
            rec["costume"] = costume_of(rec.get("era_peak"), rec.get("peak_year"))
            rec["venue"] = VENUE_OF.get(rec.get("band") or "", "salle")
            rec["style"] = STYLE_OF.get(rec.get("rarete") or "", "serigraphie")
            rec["plaque"] = plaque_of(rec)
        overrides = CFG.get("artist_plaque_override") or {}
        by_stem: dict[str, list[dict]] = {}
        for rec in serie:
            if rec.get("rarete") != "diamant":
                continue
            stem = resolved_plaque_stem(rec)
            if not stem:
                continue
            by_stem.setdefault(stem, []).append(rec)
        taken_mythic: set[str] = set()
        losers: list[dict] = []
        for stem, group in by_stem.items():
            group.sort(key=lambda r: (
                0 if r.get("qid") in overrides else 1,
                r.get("rank_serie") or 0,
            ))
            taken_mythic.add(stem)
            losers.extend(group[1:])
        for rec in losers:
            rec["plaque"] = plaque_of(rec, taken=taken_mythic)
            stem = resolved_plaque_stem(rec)
            if stem:
                taken_mythic.add(stem)
        diamonds = [r for r in serie if r.get("rarete") == "diamant"]
        diamond_stems = {resolved_plaque_stem(r) for r in diamonds}
        diamond_stems.discard(None)
        off_style = sum(
            1 for r in diamonds
            if (r.get("plaque") or "").split("|")[0] != STYLE_OF.get("diamant")
        )
        print(
            f"Diamants : {len(diamonds)} cartes, {len(diamond_stems)} encres "
            f"distinctes, {len(losers)} recadrées, hors-style={off_style}"
        )
        serie_path.write_text(json.dumps(serie, ensure_ascii=False), encoding="utf-8")

        csv_path = ROOT / "docs" / "serie-1-draft.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
            writer = csv.writer(fh, delimiter=";")
            writer.writerow([
                "rang_serie", "rarete", "artiste", "groupe", "famille", "bande",
                "region", "epoque", "sexe", "instrument", "plaque",
                "rang_vivier", "motif",
            ])
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
            for rec in serie:
                writer.writerow([
                    rec["rank_serie"],
                    rec["rarete"],
                    display_name(rec["qid"], titles),
                    rec.get("groupe") or "",
                    FAMILY_LABEL.get(rec["family"], rec["family"]),
                    rec.get("band") or "",
                    labels.get(rec.get("region"), rec.get("region") or ""),
                    labels.get(rec.get("era_peak") or rec.get("era"), rec.get("era_peak") or rec.get("era") or ""),
                    rec.get("silhouette") or "",
                    rec.get("instrument") or "",
                    rec.get("plaque") or "",
                    rec.get("rank_vivier"),
                    rec.get("draft_reason") or "",
                ])

    sex_c = Counter(v.get("silhouette") or "?" for v in mapped.values())
    instr_c = Counter(v.get("instrument_source") or "?" for v in mapped.values())
    print(f"{len(mapped)} fiches → {CENSUS.relative_to(ROOT) / 'illustration.json'}")
    if previous_of:
        print(f"Instruments corrigés : {changed}")
    if _stock_stats:
        print(
            "Plaques recadrées sur le stock : "
            + ", ".join(f"{k}={v}" for k, v in _stock_stats.most_common())
        )
    print("Sexe : " + ", ".join(f"{k}={v}" for k, v in sex_c.most_common()))
    print("Instrument : " + ", ".join(f"{k}={v}" for k, v in instr_c.most_common()))
    unknown_instr = Counter()
    for rec in raw.values():
        if not rec.get("instruments"):
            unknown_instr["(vide)"] += 1
            continue
        if not any(resolve_instrument(q) for q in rec["instruments"]):
            for q in rec["instruments"]:
                unknown_instr[q] += 1
    if unknown_instr:
        print("Instruments non mappés (top) :")
        for qid, n in unknown_instr.most_common(15):
            print(f"  {qid}  {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
