"""
Applique / complète l'arbitrage voix → 1 instrument secondaire.

- Conserve la zone déjà arbitrée (jusqu'à Carla Bruni incluse).
- Retraite le reste : un seul secondaire, critère strict aligné sur les choix humains
  (évidence occupation Wikidata + P1303 focalisé ; bruit multi-instruments écarté).
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from attach_illustration import CFG, OCC_INSTR, resolve_instrument  # noqa: E402

ARB = ROOT / "docs" / "voix-instrument-arbitrage.csv"
DETAIL = ROOT / "docs" / "voix-instrument-arbitrage-detail.csv"
RAW = ROOT / "data" / "census" / "illustration_raw.json"
OCC = ROOT / "data" / "census" / "occupations.json"
SCORES = ROOT / "data" / "census" / "scores.json"
EXTRA = ROOT / "data" / "census" / "instrument_extra.json"

CUTOFF_NAME = "Carla Bruni"

OCC_HARD = {k: v for k, v in OCC_INSTR.items() if v and v != "voix"}
# Secondaires retenus par l'humain jusqu'ici — pas de batterie/vents « bruit ».
ALLOWED_SEC = {"guitare", "claviers", "machines"}
CELEB = set(CFG.get("celebrity_occupations") or [])

# Ordre de préférence « souvent vu en train de jouer » (hors genre).
PLAY_PRIORITY = ["guitare", "claviers", "machines", "basse", "batterie", "vents", "cordes"]
HIPHOP_PRIORITY = ["machines", "claviers", "guitare", "basse", "batterie", "vents", "cordes"]
JAZZ_PRIORITY = ["claviers", "guitare", "vents", "basse", "batterie", "machines", "cordes"]

STRONG_PLAY_GENRES = {
    "rock", "metal", "punk", "folk", "country", "blues", "funk", "jazz", "rnb",
}


def norm_family(label: str) -> str:
    x = (label or "").strip().lower()
    x = (
        x.replace("é", "e")
        .replace("è", "e")
        .replace("&", "")
        .replace(" ", "")
        .replace("-", "")
    )
    if x in {"rb", "rnb"}:
        return "rnb"
    if x == "hiphop":
        return "hiphop"
    if x.startswith("electro"):
        return "electro"
    return x


def p1303_fams(instr_qids: list[str]) -> list[str]:
    out: list[str] = []
    for iq in instr_qids:
        fam = resolve_instrument(iq)
        if fam and fam != "voix" and fam not in out:
            out.append(fam)
    return out


def occ_fams(occs: list[str]) -> list[str]:
    out: list[str] = []
    for o in occs:
        fam = OCC_HARD.get(o)
        if fam and fam not in out:
            out.append(fam)
    return out


def pick_one(family: str, p1303: list[str], occ: list[str], all_occ: list[str]) -> str | None:
    """Un seul secondaire parmi guitare|claviers|machines, ou None."""
    fam = norm_family(family)
    soft = fam in {"pop", "hiphop", "chanson"}
    celeb = any(o in CELEB for o in all_occ)
    noisy = len(p1303) >= 3

    def prefer(cands: list[str]) -> str | None:
        cands = [x for x in cands if x in ALLOWED_SEC]
        if not cands:
            return None
        if fam in {"hiphop", "electro"}:
            prio = HIPHOP_PRIORITY
        elif fam in {"jazz", "rnb", "blues"}:
            prio = JAZZ_PRIORITY
        else:
            prio = PLAY_PRIORITY
        for x in prio:
            if x in cands:
                return x
        return cands[0]

    # Occupation dure, sauf célébrité soft (acteur taggé pianiste à tort, ex. Branigan)
    if occ and not (soft and celeb):
        hit = prefer(occ)
        if hit:
            return hit

    if noisy:
        return None

    if fam in {"hiphop", "electro"} and "machines" in p1303:
        return "machines"

    # Pop/chanson sans occupation : mono claviers OK (pianiste pop type Barlow) ;
    # mono guitare trop bruyant sur WD (Astley, Cabello…) → abstention.
    if soft and fam != "hiphop":
        if celeb:
            return None
        if p1303 == ["claviers"]:
            return "claviers"
        return None

    if fam == "hiphop":
        return None

    if fam in STRONG_PLAY_GENRES:
        if len(p1303) == 1 and p1303[0] in {"guitare", "claviers"}:
            return p1303[0]
        if len(p1303) == 2 and set(p1303) <= {"guitare", "claviers"}:
            return prefer(p1303)
        return None

    return None


def first_secondary(cell: str) -> str:
    parts = [p.strip() for p in (cell or "").replace("|", ",").split(",") if p.strip()]
    return parts[0] if parts else ""


def main() -> int:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    occupations = json.loads(OCC.read_text(encoding="utf-8")) if OCC.exists() else {}
    scores = json.loads(SCORES.read_text(encoding="utf-8"))
    by_rank = {int(r["rank"]): r for r in scores if r.get("rank") is not None}
    detail_rows = list(
        csv.DictReader(DETAIL.open(encoding="utf-8-sig", newline=""), delimiter=";")
    )
    detail_by_name = {r["artiste"]: r for r in detail_rows}

    cur = list(csv.DictReader(ARB.open(encoding="utf-8-sig", newline=""), delimiter=";"))
    cut = next((i for i, r in enumerate(cur) if (r.get("artiste") or "") == CUTOFF_NAME), None)
    if cut is None:
        print(f"Cutoff « {CUTOFF_NAME} » introuvable", file=sys.stderr)
        return 1

    kept: list[tuple[str, str]] = []
    for r in cur[: cut + 1]:
        name = (r.get("artiste") or "").strip()
        sec = first_secondary(r.get("instrument_secondaire") or "")
        if name and sec:
            kept.append((name, sec))

    # Reconstruire la queue après cutoff depuis le détail voix_plus (pas depuis l'ancien CSV bruyant)
    cut_rank = int(detail_by_name[CUTOFF_NAME]["rang"])
    added: list[tuple[str, str]] = []
    dropped = 0
    for d in sorted(detail_rows, key=lambda r: int(r["rang"])):
        if d.get("decision") != "voix_plus":
            continue
        if int(d["rang"]) <= cut_rank:
            continue
        name = d["artiste"]
        if name in {n for n, _ in kept}:
            continue
        qid = d["qid"]
        all_occ = occupations.get(qid) or []
        p1303 = p1303_fams((raw.get(qid) or {}).get("instruments") or [])
        occ = occ_fams(all_occ)
        family = d.get("famille") or ""
        sec = pick_one(family, p1303, occ, all_occ)
        if not sec:
            dropped += 1
            continue
        added.append((name, sec))

    out_rows = kept + added
    with ARB.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["artiste", "instrument_secondaire"])
        for name, sec in out_rows:
            w.writerow([name, sec])

    # Sync instrument_extra.json via rank/qid from detail
    extras: dict[str, list[str]] = {}
    name_to_qid = {r["artiste"]: r["qid"] for r in detail_rows}
    # also map from scores titles if needed
    for name, sec in out_rows:
        qid = name_to_qid.get(name)
        if not qid:
            continue
        extras[qid] = [sec]

    EXTRA.write_text(
        json.dumps({"version": 1, "primary": "voix", "extra": extras}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    dist = Counter(sec for _, sec in out_rows)
    print(f"Zone humaine (≤ {CUTOFF_NAME}) : {len(kept)}")
    print(f"Reste accepté : {len(added)}  (rejetés {dropped})")
    print(f"Total fichier : {len(out_rows)}")
    print("Répartition :")
    for k, v in dist.most_common():
        print(f"  {k:12} {v}")
    print("\nAperçu suite immédiate après cutoff :")
    for name, sec in added[:20]:
        print(f"  {name:<32} {sec}")
    print(f"\nÉcrit {ARB.relative_to(ROOT)}")
    print(f"Écrit {EXTRA.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
