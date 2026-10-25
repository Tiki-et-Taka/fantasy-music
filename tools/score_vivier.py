"""
Score du vivier : pageviews + sitelinks + entropie + richesse Wikidata
+ discographie MusicBrainz + héritage de groupe (dates et albums).

Usage, après l'ingest pageviews, MusicBrainz et richesse :
  python tools/score_vivier.py
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
import sys
import urllib.parse
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

W_PV, W_SL, W_ENT, W_WD, W_DISCO = 0.40, 0.20, 0.15, 0.10, 0.15
LAMBDA = 0.40
CONTRIB_DEFAULT = 0.6

FAMILY_LABEL = {
    "metal": "metal",
    "punk": "punk",
    "hiphop": "hip-hop",
    "electro": "électro",
    "reggae": "reggae",
    "afro": "afro",
    "latin": "latin",
    "jazz": "jazz",
    "blues": "blues",
    "funk": "funk",
    "rnb": "R&B",
    "country": "country",
    "folk": "folk",
    "world": "world",
    "chanson": "chanson",
    "pop": "pop",
    "rock": "rock",
}


def log1p(x: float) -> float:
    return math.log10(x + 1.0)


def zscores(values: list[float]) -> list[float]:
    if len(values) < 2:
        return [0.0] * len(values)
    mu = statistics.mean(values)
    sd = statistics.pstdev(values)
    if sd == 0:
        return [0.0] * len(values)
    return [(v - mu) / sd for v in values]


def entropy(per_wiki: dict[str, int]) -> float:
    total = sum(per_wiki.values())
    if total <= 0:
        return 0.0
    h = 0.0
    for v in per_wiki.values():
        if v <= 0:
            continue
        p = v / total
        h -= p * math.log2(p)
    return h


def contribution_of(groups: list[dict]) -> tuple[float, str]:
    best = 0.0
    used_dates = False
    used_albums = False
    for g in groups:
        start = g.get("start")
        years_c = 0.0
        if start:
            end = g.get("end") or 2026
            years_c = min(1.0, max(0, int(end) - int(start)) / 5.0)
            used_dates = True
        total = int(g.get("albums_total") or 0)
        played = int(g.get("albums_played") or 0)
        albums_c = 0.0
        if start and total > 0:
            albums_c = min(1.0, played / total)
            used_albums = True
        best = max(best, years_c, albums_c)
    if not used_dates and not used_albums:
        return CONTRIB_DEFAULT, "default"
    if used_dates and used_albums:
        src = "dates+albums"
    elif used_albums:
        src = "albums"
    else:
        src = "dates"
    return best, src


def apply_heritage(rows: list[dict]) -> None:
    """score_final = perso + λ · contrib · max(0, groupe − perso), puis monotonie."""
    by_qid = {r["qid"]: r for r in rows}
    members_of: dict[str, list[str]] = {}
    for r in rows:
        for g in r.get("groups") or []:
            gmbid = g.get("mbid")
            if gmbid:
                members_of.setdefault(gmbid, []).append(r["qid"])

    group_score = {}
    for gmbid, qids in members_of.items():
        group_score[gmbid] = max(by_qid[q]["score_perso"] for q in qids if q in by_qid)

    for r in rows:
        groups = [g for g in (r.get("groups") or []) if g.get("mbid") in group_score]
        groups.sort(key=lambda g: group_score[g["mbid"]], reverse=True)
        contrib, src = contribution_of(groups)
        r["contribution"] = round(contrib, 3)
        r["contrib_source"] = src
        if not groups:
            r["score_final"] = r["score_perso"]
            r["score_groupe"] = None
            continue
        best = group_score[groups[0]["mbid"]]
        second = group_score[groups[1]["mbid"]] if len(groups) > 1 else 0.0
        sg = best + 0.25 * second
        r["score_groupe"] = round(sg, 4)
        r["score_final"] = r["score_perso"] + LAMBDA * contrib * max(0.0, sg - r["score_perso"])

    # Monotonie intra-groupe
    for gmbid, qids in members_of.items():
        members = sorted((by_qid[q] for q in qids if q in by_qid),
                         key=lambda m: m["score_perso"], reverse=True)
        ceiling = None
        for m in members:
            if ceiling is not None and m["score_final"] > ceiling:
                m["score_final"] = ceiling
                m["monotonicity_clamped"] = True
            ceiling = m["score_final"]


_DISAMB = re.compile(r"\s*\([^)]*\)\s*$")


def display_name(qid: str, titles: dict) -> str:
    langs = titles.get(qid) or {}
    raw = langs.get("fr") or langs.get("en") or next(iter(langs.values()), qid)
    name = urllib.parse.unquote(str(raw)).replace("_", " ").strip()
    return _DISAMB.sub("", name).strip()


def write_ranking(slim: list[dict], dest: Path) -> None:
    titles_path = ROOT / "data" / "census" / "qid_titles.json"
    titles = json.loads(titles_path.read_text(encoding="utf-8")) if titles_path.exists() else {}
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow(["rang", "artiste", "famille", "sexe", "instrument", "nationalite"])
        for rec in slim:
            writer.writerow([
                rec["rank"],
                display_name(rec["qid"], titles),
                FAMILY_LABEL.get(rec["family"], rec["family"]),
                rec.get("silhouette") or "",
                rec.get("instrument") or "",
                rec.get("nationality") or "",
            ])


def band_of(rank: int, n: int) -> str:
    p = rank / n
    if p <= 0.03:
        return "icones"
    if p <= 0.15:
        return "connus"
    if p <= 0.50:
        return "scene"
    if p <= 0.80:
        return "deep"
    return "exclu"


def load_pageviews() -> dict:
    """Préfère l'agrégat multi-mois ; sinon le mois le plus récent disponible."""
    agg = ROOT / "data" / "pageviews" / "aggregate.json"
    if agg.exists():
        doc = json.loads(agg.read_text(encoding="utf-8"))
        views = doc.get("sample_views") or {}
        months = doc.get("months") or []
        print(
            f"Pageviews : aggregate.json ({len(months)} mois — {', '.join(months)})",
            flush=True,
        )
        return views
    pv = ROOT / "data" / "pageviews"
    months = sorted(
        p.name for p in pv.iterdir()
        if p.is_dir() and (p / "sample_views.json").exists()
    ) if pv.exists() else []
    if not months:
        raise FileNotFoundError(
            "Aucun pageviews : lance ingest_pageviews_dump.py puis aggregate_pageviews.py"
        )
    month = months[-1]
    print(f"Pageviews : {month}/sample_views.json (pas d'agrégat)", flush=True)
    return json.loads((pv / month / "sample_views.json").read_text(encoding="utf-8"))


def main() -> int:
    census = ROOT / "data" / "census"
    eligible = json.loads((census / "eligible.json").read_text(encoding="utf-8"))
    titles = json.loads((census / "qid_titles.json").read_text(encoding="utf-8"))
    views = load_pageviews()
    mb_path = census / "musicbrainz.json"
    mb = json.loads(mb_path.read_text(encoding="utf-8")) if mb_path.exists() else {}
    if not mb:
        print("ATTENTION : data/census/musicbrainz.json absent — disco et héritage à 0", flush=True)
    rich_path = census / "wikidata_richness.json"
    rich = json.loads(rich_path.read_text(encoding="utf-8")) if rich_path.exists() else {}
    if not rich:
        print("ATTENTION : data/census/wikidata_richness.json absent — richesse à 0", flush=True)

    by_wiki: dict[str, list[int]] = {}
    rows = []
    excluded = set(json.loads((ROOT / "tools" / "census_config.json").read_text(encoding="utf-8")).get("artist_exclude") or [])
    for rec in eligible:
        if rec["qid"] in excluded:
            continue
        qid = rec["qid"]
        per_wiki: dict[str, int] = {}
        for lang, title in titles.get(qid, {}).items():
            domain = f"{lang}.wikipedia"
            hits = int((views.get(domain) or {}).get(title) or 0)
            if hits:
                per_wiki[domain] = hits
            by_wiki.setdefault(domain, []).append(hits)
        info = mb.get(qid) or {}
        wd = rich.get(qid) or {}
        rows.append({
            **rec,
            "views": per_wiki,
            "view_total": sum(per_wiki.values()),
            "entropy": entropy(per_wiki),
            "release_groups": int(info.get("release_groups") or 0),
            "albums": int(info.get("albums") or 0),
            "richesse": int(wd.get("richesse") or 0),
            "statements": int(wd.get("statements") or 0),
            "groups": info.get("groups") or [],
        })

    musical_v = {w: sum(vals) for w, vals in by_wiki.items()}
    medians: dict[str, float] = {}
    top1_cut: dict[str, int] = {}
    for w, vals in by_wiki.items():
        positive = [v for v in vals if v > 0]
        medians[w] = statistics.median(positive) if positive else 1.0
        if medians[w] < 1:
            medians[w] = 1.0
        ranked = sorted(vals, reverse=True)
        cut = max(1, math.ceil(0.01 * len(ranked)))
        top1_cut[w] = ranked[cut - 1] if ranked else 0

    for rec in rows:
        part = 0.0
        top1 = []
        for wiki, hits in rec["views"].items():
            med = medians.get(wiki) or 1.0
            vw = musical_v.get(wiki) or 0.0
            part += math.sqrt(vw) * (hits / med)
            if hits > 0 and hits >= top1_cut.get(wiki, 0):
                top1.append(wiki)
        rec["part_pageviews"] = part
        rec["market_floor"] = bool(top1)
        rec["top1_wikis"] = top1

    z_pv = zscores([log1p(r["part_pageviews"]) for r in rows])
    z_sl = zscores([log1p(r["sitelinks"]) for r in rows])
    z_en = zscores([r["entropy"] for r in rows])
    z_wd = zscores([log1p(r["richesse"]) for r in rows])
    z_dc = zscores([log1p(r["release_groups"]) for r in rows])
    for rec, a, b, c, d, e in zip(rows, z_pv, z_sl, z_en, z_wd, z_dc):
        rec["score_perso"] = (
            W_PV * a + W_SL * b + W_ENT * max(0.0, c) + W_WD * d + W_DISCO * e
        )

    apply_heritage(rows)
    rows.sort(key=lambda r: r.get("score_final", r["score_perso"]), reverse=True)
    n = len(rows) or 1
    moved = Counter()
    for i, rec in enumerate(rows):
        rec["rank"] = i + 1
        new_band = band_of(i + 1, n)
        if new_band != rec.get("band"):
            moved[f"{rec.get('band')}→{new_band}"] += 1
        rec["band_sitelinks"] = rec.get("band")
        rec["band"] = new_band

    bands = Counter(r["band"] for r in rows)
    illu_path = ROOT / "data" / "census" / "illustration.json"
    illu = json.loads(illu_path.read_text(encoding="utf-8")) if illu_path.exists() else {}
    slim = []
    for rec in rows:
        info = illu.get(rec["qid"]) or {}
        slim.append({
            "qid": rec["qid"],
            "rank": rec["rank"],
            "score_perso": round(rec["score_perso"], 4),
            "score_final": round(rec.get("score_final", rec["score_perso"]), 4),
            "part_pageviews": round(rec["part_pageviews"], 4),
            "sitelinks": rec["sitelinks"],
            "entropy": round(rec["entropy"], 3),
            "richesse": rec["richesse"],
            "release_groups": rec["release_groups"],
            "contribution": rec.get("contribution"),
            "contrib_source": rec.get("contrib_source"),
            "view_total": rec["view_total"],
            "family": rec["family"],
            "region": rec["region"],
            "countries": list(rec.get("countries") or []),
            "nationality": rec.get("nationality") or "",
            "era": rec["era"],
            "band": rec["band"],
            "band_sitelinks": rec["band_sitelinks"],
            "market_floor": rec["market_floor"],
            "silhouette": info.get("silhouette") or "",
            "instrument": info.get("instrument") or "",
        })

    out = ROOT / "data" / "census" / "scores.json"
    out.write_text(json.dumps(slim, ensure_ascii=False), encoding="utf-8")
    ranking = ROOT / "docs" / "vivier-ranking.csv"
    write_ranking(slim, ranking)

    print(f"Vivier scoré : {len(slim)}")
    print("Bandes : " + ", ".join(f"{k}={bands[k]}" for k in
                                  ("icones", "connus", "scene", "deep", "exclu")))
    print(f"Plancher de marché (top 1 % d'une édition) : "
          f"{sum(1 for r in slim if r['market_floor'])}")
    print(f"Richesse Wikidata > 0 : {sum(1 for r in slim if r['richesse'])}")
    print("Contribution :")
    for k, v in Counter(r.get("contrib_source") for r in slim).most_common():
        print(f"  {k}: {v}")
    print("Mouvements vs proxy sitelinks :")
    for k, v in moved.most_common():
        print(f"  {k}: {v}")
    print("\nTop 15")
    for rec in slim[:15]:
        print(f"  {rec['rank']:4}  {rec['qid']:12}  {rec['score_final']:+.3f}  "
              f"{rec['family']:<8} {rec['band']:<8} sl={rec['sitelinks']}  "
              f"wd={rec['richesse']} rg={rec['release_groups']}")
    print(f"\nÉcrit : {out.relative_to(ROOT)}")
    print(f"Classement : {ranking.relative_to(ROOT)}")
    return 0


def export_ranking_from_scores() -> int:
    slim = json.loads((ROOT / "data" / "census" / "scores.json").read_text(encoding="utf-8"))
    ranking = ROOT / "docs" / "vivier-ranking.csv"
    write_ranking(slim, ranking)
    print(f"Classement : {ranking.relative_to(ROOT)}  ({len(slim)} artistes)")
    return 0


if __name__ == "__main__":
    if "--ranking-only" in sys.argv:
        sys.exit(export_ranking_from_scores())
    sys.exit(main())
