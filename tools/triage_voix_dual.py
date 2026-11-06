"""
Arbitrage auto : artistes taggés voix → voix seul, ou voix + instrument(s) secondaire(s).

Règle produit :
- connu unilatéralement pour le chant → reste voix ;
- utilise souvent un autre instrument → garde voix + secondaire(s) (éligibilité Fantasy).

Signaux : occupations Wikidata (fort) + P1303 (confirmé / filtré si bruyant).
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from attach_illustration import OCC_INSTR, resolve_instrument  # noqa: E402

VIVIER = ROOT / "docs" / "vivier-ranking.csv"
RAW = ROOT / "data" / "census" / "illustration_raw.json"
OCC = ROOT / "data" / "census" / "occupations.json"
SCORES = ROOT / "data" / "census" / "scores.json"
OUT_CSV = ROOT / "docs" / "voix-instrument-arbitrage.csv"
OUT_DETAIL = ROOT / "docs" / "voix-instrument-arbitrage-detail.csv"
OUT_JSON = ROOT / "data" / "census" / "instrument_extra.json"

FAM_ORDER = ["basse", "batterie", "guitare", "claviers", "machines", "vents", "cordes"]

# Familles où un P1303 « guitare/claviers/machines » est crédible sans occupation miroir.
GUITAR_GENRES = {
    "rock", "metal", "punk", "folk", "country", "blues", "funk", "pop", "chanson", "rnb",
}
KEYS_GENRES = {"jazz", "rnb", "blues", "funk", "chanson", "pop", "gospel"}
MACHINE_GENRES = {"hiphop", "electro", "pop", "rnb"}

# Occupations instrumentales « dures » (pas auteur/compositeur seul).
OCC_HARD = {
    k: v for k, v in OCC_INSTR.items() if v and v != "voix"
}


def families_from_p1303(instr_qids: list[str]) -> list[str]:
    out: list[str] = []
    for iq in instr_qids:
        fam = resolve_instrument(iq)
        if fam and fam != "voix" and fam not in out:
            out.append(fam)
    return out


def families_from_occ(occs: list[str]) -> list[str]:
    out: list[str] = []
    for occ in occs:
        fam = OCC_HARD.get(occ)
        if fam and fam not in out:
            out.append(fam)
    return out


def triage(family: str, p1303: list[str], occ_fams: list[str]) -> tuple[str, list[str]]:
    """Retourne (decision, secondaires) avec decision in voix_seul | voix_plus."""
    fam_norm = norm_family_label(family)

    secondary: list[str] = []

    # 1) Occupation instrumentale = signal fort
    for fam in FAM_ORDER:
        if fam in occ_fams and fam not in secondary:
            secondary.append(fam)

    # 2) P1303 : si trop d'instruments listés sans occupation, c'est du bruit (ex. MJ)
    noisy = len(p1303) >= 3 and not occ_fams

    # Pop / hip-hop / chanson : P1303 « auteur » (guitare/claviers) OK ;
    # batterie/basse/vents listés en plus = souvent du bruit → ignorer sans occupation.
    soft_genre = fam_norm in {"pop", "hiphop", "chanson"}
    songwriter_kit = set(p1303) <= {"guitare", "claviers"} and bool(p1303)

    if not noisy:
        for fam in p1303:
            if fam in secondary:
                continue
            if fam == "guitare" and fam_norm in GUITAR_GENRES:
                if soft_genre and "guitare" not in occ_fams and not songwriter_kit:
                    continue
                secondary.append(fam)
            elif fam == "claviers" and fam_norm in KEYS_GENRES:
                if soft_genre and "claviers" not in occ_fams and not songwriter_kit:
                    continue
                secondary.append(fam)
            elif fam == "machines" and fam_norm in MACHINE_GENRES:
                # Hip-hop / électro : machines crédible même sans occupation « DJ » renseignée.
                if fam_norm == "pop" and "machines" not in occ_fams:
                    continue
                secondary.append(fam)
            elif fam in ("basse", "batterie", "vents", "cordes") and fam in occ_fams:
                secondary.append(fam)

    # 3) P1303 bruyant : uniquement ce que l'occupation confirme (déjà en 1)
    # rien de plus

    # Ordre stable, max 3 secondaires
    ordered = [f for f in FAM_ORDER if f in secondary][:3]
    if not ordered:
        return "voix_seul", []
    return "voix_plus", ordered


def norm_family_label(label: str) -> str:
    x = (label or "").strip().lower()
    x = (
        x.replace("é", "e")
        .replace("è", "e")
        .replace("&", "")
        .replace(" ", "")
        .replace("-", "")
    )
    repl = {
        "hiphop": "hiphop",
        "electro": "electro",
        "rb": "rnb",
        "rnb": "rnb",
    }
    return repl.get(x, x)


def main() -> int:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    occupations = json.loads(OCC.read_text(encoding="utf-8")) if OCC.exists() else {}
    scores = json.loads(SCORES.read_text(encoding="utf-8"))
    by_rank = {int(r["rank"]): r for r in scores if r.get("rank") is not None}

    rows_out = []
    extras: dict[str, list[str]] = {}
    decisions = Counter()

    with VIVIER.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh, delimiter=";"):
            if (row.get("instrument") or "").strip() != "voix":
                continue
            try:
                rang = int(row["rang"])
            except (TypeError, ValueError):
                continue
            rec = by_rank.get(rang)
            if not rec:
                continue
            qid = rec["qid"]
            instr_qids = (raw.get(qid) or {}).get("instruments") or []
            occs = occupations.get(qid) or []
            p1303 = families_from_p1303(instr_qids)
            occ_fams = families_from_occ(occs)
            if not p1303 and not occ_fams:
                continue
            decision, secondary = triage(
                norm_family_label(row.get("famille") or rec.get("family") or ""),
                p1303,
                occ_fams,
            )
            decisions[decision] += 1
            rows_out.append({
                "rang": rang,
                "qid": qid,
                "artiste": row.get("artiste") or "",
                "famille": row.get("famille") or "",
                "instrument_primary": "voix",
                "p1303": "|".join(p1303),
                "occ_instrument": "|".join(occ_fams),
                "decision": decision,
                "secondaires": "|".join(secondary),
            })
            if decision == "voix_plus" and secondary:
                extras[qid] = secondary

    rows_out.sort(key=lambda r: r["rang"])
    plus = [r for r in rows_out if r["decision"] == "voix_plus" and r["secondaires"]]

    # Fichier lisible : nom + secondaire(s) uniquement
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["artiste", "instrument_secondaire"])
        for r in plus:
            w.writerow([r["artiste"], r["secondaires"].replace("|", ", ")])

    # Détail technique (debug / rejeu)
    with OUT_DETAIL.open("w", encoding="utf-8-sig", newline="") as fh:
        fields = [
            "rang", "qid", "artiste", "famille", "instrument_primary",
            "p1303", "occ_instrument", "decision", "secondaires",
        ]
        w = csv.DictWriter(fh, fieldnames=fields, delimiter=";")
        w.writeheader()
        w.writerows(rows_out)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps({"version": 1, "primary": "voix", "extra": extras}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    sec_c = Counter()
    for secs in extras.values():
        for s in secs:
            sec_c[s] += 1

    print(f"Candidats examinés (voix + signal WD) : {len(rows_out)}")
    print(f"  voix_seul : {decisions['voix_seul']}")
    print(f"  voix_plus : {decisions['voix_plus']}")
    print("Secondaires accordés :")
    for k, v in sec_c.most_common():
        print(f"  {k:12} {v}")
    print(f"Écrit : {OUT_CSV.relative_to(ROOT)}  ({len(plus)} artistes voix+)")
    print(f"Écrit : {OUT_DETAIL.relative_to(ROOT)}")
    print(f"Écrit : {OUT_JSON.relative_to(ROOT)}")
    print("\nAperçu :")
    for r in plus[:12]:
        print(f"  {r['artiste']:<28}  {r['secondaires'].replace('|', ', ')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
