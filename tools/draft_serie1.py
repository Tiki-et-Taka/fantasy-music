"""
Draft de la Série 1 : 2 000 sièges, 80 / 400 / 900 / 600.

Pour chaque bande, on assied d'abord la liste verte, puis on comble les
cases déficitaires (genre / région / époque) par le mieux classé de la
bande, cases les plus rares d'abord, puis on remplit les sièges libres.

Usage : python tools/draft_serie1.py
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from census_vivier import LABELS  # noqa: E402
from score_vivier import FAMILY_LABEL, display_name  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BANDS = ("icones", "connus", "scene", "deep")
QUOTAS = {"icones": 80, "connus": 400, "scene": 900, "deep": 600}
TARGET = 2000  # le mélange publié somme à 1 980 ; 20 sièges rattrapent les cases courtes

# Quotas Fantasy Game (docs/12-fantasy-game.md) — planchers / plafond instrument.
# Chargés depuis census_config.json si présents, sinon cibles par défaut.
def _load_fantasy_instrument_quotas() -> tuple[dict[str, int], int]:
    cfg_path = ROOT / "tools" / "census_config.json"
    floors = {
        "basse": 160, "batterie": 160, "guitare": 280, "claviers": 80,
        "machines": 70, "vents": 60, "cordes": 40,
    }
    voix_cap = 900
    try:
        raw = json.loads(cfg_path.read_text(encoding="utf-8"))
        block = raw.get("fantasy_instrument_quotas") or {}
        if isinstance(block.get("floors"), dict):
            floors = {k: int(v) for k, v in block["floors"].items()}
        if block.get("voix_cap") is not None:
            voix_cap = int(block["voix_cap"])
    except (OSError, ValueError, TypeError):
        pass
    return floors, voix_cap


INSTRUMENT_FLOOR, VOIX_CAP = _load_fantasy_instrument_quotas()

GENRE_BAND = {
    "rock":    {"icones": 8, "connus": 40, "scene": 90, "deep": 62},
    "pop":     {"icones": 6, "connus": 31, "scene": 70, "deep": 48},
    "metal":   {"icones": 5, "connus": 26, "scene": 59, "deep": 40},
    "hiphop":  {"icones": 5, "connus": 26, "scene": 59, "deep": 40},
    "electro": {"icones": 4, "connus": 22, "scene": 50, "deep": 34},
    "jazz":    {"icones": 3, "connus": 17, "scene": 38, "deep": 27},
    "rnb":     {"icones": 3, "connus": 15, "scene": 34, "deep": 23},
    "chanson": {"icones": 3, "connus": 15, "scene": 34, "deep": 23},
    "punk":    {"icones": 3, "connus": 13, "scene": 29, "deep": 20},
    "folk":    {"icones": 2, "connus": 11, "scene": 25, "deep": 17},
    "funk":    {"icones": 2, "connus": 11, "scene": 25, "deep": 17},
    "latin":   {"icones": 2, "connus": 10, "scene": 22, "deep": 16},
    "afro":    {"icones": 2, "connus": 10, "scene": 22, "deep": 16},
    "country": {"icones": 2, "connus": 8, "scene": 18, "deep": 12},
    "reggae":  {"icones": 2, "connus": 8, "scene": 18, "deep": 12},
    "blues":   {"icones": 1, "connus": 7, "scene": 16, "deep": 11},
    "world":   {"icones": 1, "connus": 7, "scene": 16, "deep": 11},
}

ERA_BAND = {
    "pre1970":  {"icones": 14, "connus": 70, "scene": 157, "deep": 109},
    "1970s80s": {"icones": 18, "connus": 90, "scene": 202, "deep": 140},
    "1990s00s": {"icones": 18, "connus": 90, "scene": 202, "deep": 140},
    "2010s":    {"icones": 12, "connus": 60, "scene": 135, "deep": 93},
}

REGION_TOTAL = {
    "anglophone": 500, "europe": 220, "europe_fr": 180, "latam": 120,
    "afrique": 100, "asie_est": 100, "mena": 80, "est": 80,
    "asie_sud": 60, "autre": 40,
}

RARETE = [
    (48, "diamant"),
    (158, "platine"),
    (418, "or"),
    (978, "argent"),
]


def split_like_set(n: int) -> dict[str, int]:
    icones = round(n * 0.04)
    connus = round(n * 0.20)
    scene = round(n * 0.45)
    deep = n - icones - connus - scene
    return {"icones": icones, "connus": connus, "scene": scene, "deep": deep}


REGION_BAND = {key: split_like_set(n) for key, n in REGION_TOTAL.items()}


def rarete_of(rank: int) -> str:
    for cut, name in RARETE:
        if rank <= cut:
            return name
    return "commune"


def load_lists() -> tuple[list[str], set[str], dict[str, str]]:
    raw = json.loads((ROOT / "tools" / "draft_lists.json").read_text(encoding="utf-8"))
    green, seen = [], set()
    for item in raw["green"]:
        qid = item["qid"]
        if qid in seen:
            continue
        seen.add(qid)
        green.append(qid)
    red = {item["qid"] for item in raw["red"]}
    why = {item["qid"]: item.get("why") or "veto" for item in raw["red"]}
    return green, red, why


def instrument_band_floors(band: str) -> dict[str, int]:
    """Répartit les planchers instrument sur les 4 bandes (même proportion que QUOTAS)."""
    out = {}
    for instr, total in INSTRUMENT_FLOOR.items():
        parts = split_like_set(total)
        out[instr] = parts[band]
    return out


def cell_floors(band: str) -> list[tuple[str, str, int]]:
    cells = []
    for fam, by_band in GENRE_BAND.items():
        cells.append(("family", fam, by_band[band]))
    for region, by_band in REGION_BAND.items():
        cells.append(("region", region, by_band[band]))
    for era, by_band in ERA_BAND.items():
        cells.append(("era", era, by_band[band]))
    for instr, floor in instrument_band_floors(band).items():
        cells.append(("instrument", instr, floor))
    return cells


def voix_band_cap(band: str) -> int:
    return split_like_set(VOIX_CAP)[band]


def draft_band(pool: list[dict], band: str, quota: int,
               green: list[str], taken: set[str]) -> tuple[list[dict], list[dict]]:
    by_qid = {r["qid"]: r for r in pool}
    seated: list[dict] = []
    counts = {
        "family": Counter(),
        "region": Counter(),
        "era": Counter(),
        "instrument": Counter(),
    }
    core = max(1, quota // 2)
    vcap = voix_band_cap(band)

    def seat(rec: dict, reason: str) -> None:
        taken.add(rec["qid"])
        seated.append({**rec, "draft_reason": reason, "draft_band": band})
        counts["family"][rec["family"]] += 1
        counts["region"][rec.get("region")] += 1
        counts["era"][rec.get("era")] += 1
        instr = (rec.get("instrument") or "").strip() or "?"
        counts["instrument"][instr] += 1

    def over_voix(rec: dict) -> bool:
        return (rec.get("instrument") or "") == "voix" and counts["instrument"]["voix"] >= vcap

    for rec in sorted(pool, key=lambda r: r["rank"]):
        if len(seated) >= min(core, quota) or rec["qid"] in taken:
            continue
        if over_voix(rec):
            continue
        seat(rec, "cœur de bande")

    # Planchers instrument avant les autres cases : sinon les cellules rares
    # (région, époque) saturent le quota et la basse / batterie restent à terre.
    for instr, floor in instrument_band_floors(band).items():
        need = floor - counts["instrument"][instr]
        if need <= 0:
            continue
        cands = [r for r in sorted(pool, key=lambda r: r["rank"])
                 if r["qid"] not in taken and (r.get("instrument") or "") == instr]
        for rec in cands:
            if need <= 0 or len(seated) >= quota:
                break
            seat(rec, "plancher instrument")
            need -= 1

    for qid in green:
        rec = by_qid.get(qid)
        if rec is None or qid in taken or len(seated) >= quota:
            continue
        # Liste verte : on respecte le plafond voix sauf si plus de siège non-voix.
        if over_voix(rec):
            continue
        seat(rec, "liste verte")

    available = [r for r in sorted(pool, key=lambda r: r["rank"]) if r["qid"] not in taken]
    while len(seated) < quota:
        deficits = []
        for axis, label, floor in cell_floors(band):
            need = floor - counts[axis][label]
            if need <= 0:
                continue
            cands = [r for r in available if r.get(axis) == label]
            if axis != "instrument":
                cands = [r for r in cands if not over_voix(r)]
            if cands:
                deficits.append((len(cands), -need, cands[0]["rank"], cands[0]))
        if not deficits:
            break
        deficits.sort()
        pick = deficits[0][3]
        seat(pick, "plancher")
        available = [r for r in available if r["qid"] != pick["qid"]]

    # Sièges libres : éviter de dépasser le plafond voix si des alternatives existent.
    for prefer_non_voix in (True, False):
        for rec in list(available):
            if len(seated) >= quota:
                break
            if rec["qid"] in taken:
                continue
            if prefer_non_voix and over_voix(rec):
                continue
            if not prefer_non_voix and over_voix(rec) and any(
                not over_voix(r) for r in available if r["qid"] not in taken
            ):
                continue
            seat(rec, "siège libre")
            available = [r for r in available if r["qid"] != rec["qid"]]

    gaps = []
    for axis, label, floor in cell_floors(band):
        have = counts[axis][label]
        if have < floor:
            gaps.append({"band": band, "axis": axis, "label": label,
                         "need": floor - have, "have": have, "floor": floor})
    if counts["instrument"]["voix"] > vcap:
        gaps.append({
            "band": band, "axis": "instrument", "label": "voix",
            "need": 0, "have": counts["instrument"]["voix"], "floor": vcap,
            "note": "plafond voix dépassé",
        })
    return seated, gaps


def main() -> int:
    census = ROOT / "data" / "census"
    scores = json.loads((census / "scores.json").read_text(encoding="utf-8"))
    titles = json.loads((census / "qid_titles.json").read_text(encoding="utf-8"))
    green, red, red_why = load_lists()

    skipped_red = [r for r in scores if r["qid"] in red]
    pool = [r for r in scores if r["qid"] not in red]
    by_band: dict[str, list[dict]] = defaultdict(list)
    for rec in pool:
        by_band[rec.get("band") or "exclu"].append(rec)

    taken: set[str] = set()
    drafted: list[dict] = []
    all_gaps: list[dict] = []

    # Liste verte tombée dans le dernier quintile : on la rattrape en deep.
    green_exclu = [qid for qid in green
                   if any(r["qid"] == qid for r in by_band.get("exclu", []))]
    if green_exclu:
        by_band["deep"].extend(r for r in by_band["exclu"] if r["qid"] in set(green_exclu))

    for band in BANDS:
        seated, gaps = draft_band(by_band.get(band, []), band, QUOTAS[band], green, taken)
        drafted.extend(seated)
        all_gaps.extend(gaps)
        print(f"{band:<8} {len(seated):>4}/{QUOTAS[band]}  "
              f"cœur={sum(1 for r in seated if r['draft_reason']=='cœur de bande')}  "
              f"verte={sum(1 for r in seated if r['draft_reason']=='liste verte')}  "
              f"plancher={sum(1 for r in seated if r['draft_reason'].startswith('plancher'))}  "
              f"libre={sum(1 for r in seated if r['draft_reason']=='siège libre')}",
              flush=True)

    leftovers = [r for band in ("scene", "deep", "connus")
                 for r in by_band.get(band, [])
                 if r["qid"] not in taken]
    leftovers.sort(key=lambda r: r["rank"])
    while len(drafted) < TARGET and leftovers:
        have_g = Counter(r["family"] for r in drafted)
        have_r = Counter(r.get("region") for r in drafted)
        have_e = Counter(r.get("era") for r in drafted)
        have_i = Counter((r.get("instrument") or "?") for r in drafted)
        short = []
        for fam, by_b in GENRE_BAND.items():
            need = sum(by_b.values()) - have_g[fam]
            if need > 0:
                short.append(("family", fam, need))
        for key, need_n in REGION_TOTAL.items():
            need = need_n - have_r[key]
            if need > 0:
                short.append(("region", key, need))
        for key, by_b in ERA_BAND.items():
            need = sum(by_b.values()) - have_e[key]
            if need > 0:
                short.append(("era", key, need))
        for instr, floor in INSTRUMENT_FLOOR.items():
            need = floor - have_i[instr]
            if need > 0:
                short.append(("instrument", instr, need))
        pick = None
        reason = "siège libre"
        if short:
            short.sort(key=lambda x: -x[2])
            for axis, label, _need in short:
                hit = next(
                    (
                        r for r in leftovers
                        if r.get(axis) == label
                        and not (
                            have_i["voix"] >= VOIX_CAP
                            and (r.get("instrument") or "") == "voix"
                        )
                    ),
                    None,
                )
                if hit:
                    pick = hit
                    reason = f"rattrapage {axis}:{label}"
                    break
        if pick is None:
            # Évite d'ajouter encore de la voix si le plafond global est atteint.
            if have_i["voix"] >= VOIX_CAP:
                pick = next(
                    (r for r in leftovers if (r.get("instrument") or "") != "voix"),
                    leftovers[0],
                )
            else:
                pick = leftovers[0]
        leftovers = [r for r in leftovers if r["qid"] != pick["qid"]]
        taken.add(pick["qid"])
        drafted.append({**pick, "draft_reason": reason,
                        "draft_band": pick.get("band") or "scene"})

    drafted.sort(key=lambda r: r["rank"])
    for i, rec in enumerate(drafted, 1):
        rec["rank_serie"] = i
        rec["rarete"] = rarete_of(i)

    missing_green = []
    drafted_q = {r["qid"] for r in drafted}
    for qid in green:
        if qid not in drafted_q:
            hit = next((r for r in scores if r["qid"] == qid), None)
            missing_green.append((qid, None if hit is None else hit.get("band")))

    csv_path = ROOT / "docs" / "serie-1-draft.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(["rang_serie", "rarete", "artiste", "groupe", "famille",
                         "bande", "region", "epoque", "sexe", "instrument",
                         "plaque", "rang_vivier", "motif"])
        for rec in drafted:
            writer.writerow([
                rec["rank_serie"],
                rec["rarete"],
                display_name(rec["qid"], titles),
                rec.get("groupe") or "",
                FAMILY_LABEL.get(rec["family"], rec["family"]),
                rec["draft_band"],
                LABELS.get(rec.get("region"), rec.get("region") or ""),
                LABELS.get(rec.get("era"), rec.get("era") or ""),
                rec.get("silhouette") or "",
                rec.get("instrument") or "",
                rec.get("plaque") or "",
                rec["rank"],
                rec["draft_reason"],
            ])

    slim = []
    for rec in drafted:
        slim.append({
            "qid": rec["qid"],
            "rank_serie": rec["rank_serie"],
            "rank_vivier": rec["rank"],
            "rarete": rec["rarete"],
            "family": rec["family"],
            "region": rec.get("region"),
            "era": rec.get("era"),
            "band": rec["draft_band"],
            "score_final": rec.get("score_final"),
            "draft_reason": rec["draft_reason"],
            "silhouette": rec.get("silhouette") or "",
            "instrument": rec.get("instrument") or "",
            "plaque": rec.get("plaque") or "",
        })
    (census / "serie1.json").write_text(json.dumps(slim, ensure_ascii=False), encoding="utf-8")

    print(f"\nSérie 1 : {len(drafted)} cartes")
    print("Raretés : " + ", ".join(
        f"{k}={v}" for k, v in Counter(r["rarete"] for r in drafted).items()
    ))
    print("Bandes  : " + ", ".join(
        f"{k}={sum(1 for r in drafted if r['draft_band']==k)}" for k in BANDS
    ))

    print("\nPlanchers genre")
    have_g = Counter(r["family"] for r in drafted)
    for fam, by_band in GENRE_BAND.items():
        need = sum(by_band.values())
        got = have_g[fam]
        flag = "OK" if got >= need else f"MANQUE {need-got}"
        print(f"  {LABELS[fam]:<22} {got:>4} / {need:<4} {flag}")

    print("\nPlanchers région")
    have_r = Counter(r.get("region") for r in drafted)
    for key, need in REGION_TOTAL.items():
        got = have_r[key]
        flag = "OK" if got >= need else f"MANQUE {need-got}"
        print(f"  {LABELS[key]:<28} {got:>4} / {need:<4} {flag}")

    print("\nPlanchers époque")
    have_e = Counter(r.get("era") for r in drafted)
    for key, by_band in ERA_BAND.items():
        need = sum(by_band.values())
        got = have_e[key]
        flag = "OK" if got >= need else f"MANQUE {need-got}"
        print(f"  {LABELS[key]:<22} {got:>4} / {need:<4} {flag}")

    print("\nQuotas instrument (Fantasy)")
    have_i = Counter((r.get("instrument") or "?") for r in drafted)
    for instr, floor in INSTRUMENT_FLOOR.items():
        got = have_i[instr]
        flag = "OK" if got >= floor else f"MANQUE {floor - got}"
        print(f"  {instr:<12} {got:>4} / {floor:<4} {flag}")
    voix_n = have_i["voix"]
    vflag = "OK" if voix_n <= VOIX_CAP else f"PLAFOND +{voix_n - VOIX_CAP}"
    print(f"  {'voix':<12} {voix_n:>4} / ≤{VOIX_CAP:<3} {vflag}")

    if all_gaps:
        print("\nCases impossibles (plancher baissé)")
        for g in all_gaps:
            print(f"  {g['band']:<8} {g['axis']}:{g['label']}  "
                  f"{g['have']}/{g['floor']}  manque {g['need']}")
    else:
        print("\nToutes les cases par bande sont tenables.")

    print("\nListe verte absente :" if missing_green else "\nListe verte : tout le monde est assis.")
    for qid, band in missing_green:
        print(f"  {qid}  ({band or 'hors vivier'})")

    if skipped_red:
        print("Liste rouge écartée :")
        for rec in skipped_red:
            print(f"  {display_name(rec['qid'], titles)}  ({red_why.get(rec['qid'])})")

    print("\nMythiques")
    for rec in drafted[:8]:
        print(f"  {rec['rank_serie']}  {display_name(rec['qid'], titles):28}  "
              f"{FAMILY_LABEL.get(rec['family'], rec['family']):<8}  "
              f"{rec['draft_band']}")

    print(f"\nÉcrit : {csv_path.relative_to(ROOT)}")
    print(f"Écrit : data/census/serie1.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
