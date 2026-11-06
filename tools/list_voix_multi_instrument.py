"""Liste des artistes taggés voix qui ont aussi un autre instrument (Wikidata)."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from attach_illustration import (  # noqa: E402
    CFG,
    OCC_INSTR,
    resolve_instrument,
)

VIVIER = ROOT / "docs" / "vivier-ranking.csv"
RAW = ROOT / "data" / "census" / "illustration_raw.json"
OCC = ROOT / "data" / "census" / "occupations.json"
OUT = ROOT / "docs" / "voix-multi-instrument-candidats.csv"

FAM_ORDER = ["basse", "batterie", "guitare", "claviers", "machines", "vents", "cordes"]


def main() -> int:
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    occupations = json.loads(OCC.read_text(encoding="utf-8")) if OCC.exists() else {}

    # qid by name+rank from scores or build from ranking + allowlist?
    # vivier CSV has no qid — join via scores.json name+rank or illustration.json
    scores = json.loads((ROOT / "data" / "census" / "scores.json").read_text(encoding="utf-8"))
    by_rank = {int(r["rank"]): r for r in scores if r.get("rank") is not None}

    rows_out = []
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

            fams_from_instr: list[str] = []
            for iq in instr_qids:
                fam = resolve_instrument(iq)
                if fam and fam not in fams_from_instr:
                    fams_from_instr.append(fam)

            fams_from_occ: list[str] = []
            for occ in occs:
                fam = OCC_INSTR.get(occ)
                if fam and fam not in fams_from_occ:
                    fams_from_occ.append(fam)

            other = [f for f in FAM_ORDER if f in fams_from_instr or f in fams_from_occ]
            # require signal beyond voix
            if not other:
                continue
            # must have some voix signal OR already tagged voix (always true) —
            # include even if WD only lists guitar (singer-songwriter)
            rows_out.append({
                "rang": rang,
                "qid": qid,
                "artiste": row.get("artiste") or "",
                "famille": row.get("famille") or "",
                "instrument_actuel": "voix",
                "autres_via_P1303": "|".join(f for f in FAM_ORDER if f in fams_from_instr),
                "autres_via_occupation": "|".join(f for f in FAM_ORDER if f in fams_from_occ),
                "propositions": "|".join(other),
                "n_propositions": len(other),
                "arbitre": "",  # colonne vide pour toi
            })

    rows_out.sort(key=lambda r: r["rang"])
    with OUT.open("w", encoding="utf-8-sig", newline="") as fh:
        fields = [
            "rang", "qid", "artiste", "famille", "instrument_actuel",
            "autres_via_P1303", "autres_via_occupation", "propositions",
            "n_propositions", "arbitre",
        ]
        w = csv.DictWriter(fh, fieldnames=fields, delimiter=";")
        w.writeheader()
        w.writerows(rows_out)

    # résumé
    from collections import Counter
    prop_c = Counter()
    for r in rows_out:
        for p in r["propositions"].split("|"):
            if p:
                prop_c[p] += 1
    print(f"Candidats voix + autre: {len(rows_out)}")
    print(f"Écrit: {OUT.relative_to(ROOT)}")
    print("Répartition propositions:")
    for k, v in prop_c.most_common():
        print(f"  {k:12} {v}")
    print("\nTop 25 (rang):")
    for r in rows_out[:25]:
        print(f"  {r['rang']:>5}  {r['artiste']:<28}  → {r['propositions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
