"""
Validation du scoring de rareté sur un échantillon de cas de référence.

Objectif : vérifier que les formules de docs/03-rarete-scoring.md produisent un
classement crédible AVANT de lancer une extraction massive. On teste l'ordre relatif
et le comportement de l'héritage, pas les paliers — un échantillon de 38 artistes
volontairement célèbres ne permet aucun calage de centiles.

Stratégie d'accès réseau :
  - résolution titre Wikipédia → QID en une seule requête groupée (pageprops) ;
  - entités Wikidata récupérées par lots de 25 via wbgetentities ;
  - pageviews en parallèle, une requête par couple (langue, article) ;
  - MusicBrainz en dernier, séquentiel, 1 req/s comme l'exigent leurs conditions.

Aucune dépendance externe. Les réponses sont cachées sur disque : les relances sont
quasi instantanées.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "data" / "validation.json"

UA = "fantasy-music-validation/0.2 (prototype de jeu de cartes; contact: edouard@localhost)"

# Pondérations de docs/03-rarete-scoring.md — hypothèses à valider.
W_PAGEVIEWS, W_SITELINKS, W_STATEMENTS, W_DISCO = 0.45, 0.25, 0.15, 0.15
LAMBDA = 0.40

# Éditions Wikipédia interrogées pour les pageviews.
#
# L'API REST de Wikimedia renvoie des 429 bien avant la limite annoncée pour un client
# anonyme. On se restreint donc aux douze plus grosses éditions, interrogées une par une
# avec un espacement, ce qui ramène ~1200 requêtes à ~450.
#
# Conséquence à retenir pour la production : à l'échelle de 2 000 artistes, cette API
# n'est pas viable. Il faudra passer par les dumps mensuels de pageviews.
WIKIS = [w.strip() for w in os.environ.get("WIKIS", "en,de,fr,es").split(",") if w.strip()]

# Espacement entre deux requêtes pageviews, en secondes. Mesuré empiriquement : même à
# 1,2 s, le quota se referme après une centaine de requêtes consécutives.
PV_DELAY = 2.0

# Durée d'attente après un 429 : le blocage dure de l'ordre de la minute.
PV_COOLDOWN = 70

# PV_OFFLINE=1 : n'exploiter que le cache, sans aucun appel réseau pour les pageviews.
# Les langues incomplètes sont alors simplement écartées du score.
PV_OFFLINE = os.environ.get("PV_OFFLINE") == "1"


# --------------------------------------------------------------------------- #
# Réseau
# --------------------------------------------------------------------------- #

def _cache_path(key: str) -> Path:
    return CACHE / f"{urllib.parse.quote(key, safe='')}.json"


def fetch_json(url: str, cache_key: str, *, retries: int = 3, allow_404: bool = False):
    path = _cache_path(cache_key)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data), encoding="utf-8")
            return data
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and allow_404:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("null", encoding="utf-8")
                return None
            if exc.code == 429 and attempt < retries - 1:
                print(f"    429 — pause de {PV_COOLDOWN}s", flush=True)
                time.sleep(PV_COOLDOWN)
                continue
            if exc.code in (500, 502, 503, 504) and attempt < retries - 1:
                time.sleep(1.5 * (2 ** attempt))
                continue
            return None
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(1.5 * (2 ** attempt))
    return None


def chunks(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


# --------------------------------------------------------------------------- #
# Wikidata
# --------------------------------------------------------------------------- #

def titles_to_qids(titles: list[str]) -> dict[str, str]:
    """Titres d'articles en.wikipedia → QID, par lots, redirections suivies."""
    out: dict[str, str] = {}
    for batch in chunks(titles, 40):
        joined = "|".join(batch)
        url = (
            "https://en.wikipedia.org/w/api.php?action=query&format=json&redirects=1"
            f"&prop=pageprops&ppprop=wikibase_item&titles={urllib.parse.quote(joined)}"
        )
        data = fetch_json(url, f"pp_{hash(joined) & 0xFFFFFFFF}_{len(batch)}")
        if not data:
            continue
        query = data.get("query", {})
        # Reconstruire la chaîne de normalisation et de redirection.
        alias: dict[str, str] = {}
        for n in query.get("normalized", []):
            alias[n["to"]] = n["from"]
        for r in query.get("redirects", []):
            alias[r["to"]] = alias.get(r["from"], r["from"])
        for page in query.get("pages", {}).values():
            qid = page.get("pageprops", {}).get("wikibase_item")
            if not qid:
                continue
            title = page.get("title", "")
            out[alias.get(title, title)] = qid
    return out


def get_entities(qids: list[str]) -> dict[str, dict]:
    """Entités Wikidata par lots. props limités pour alléger la charge utile."""
    out: dict[str, dict] = {}
    for batch in chunks(qids, 25):
        joined = "|".join(batch)
        url = (
            "https://www.wikidata.org/w/api.php?action=wbgetentities&format=json"
            f"&props=sitelinks|claims&ids={joined}"
        )
        data = fetch_json(url, f"ents_{joined}")
        if data:
            out.update(data.get("entities", {}))
    return out


def claim_values(entity: dict, prop: str) -> list[str]:
    out = []
    for stmt in entity.get("claims", {}).get(prop, []):
        snak = stmt.get("mainsnak", {})
        if snak.get("snaktype") != "value":
            continue
        val = snak.get("datavalue", {}).get("value")
        if isinstance(val, dict) and "id" in val:
            out.append(val["id"])
    return out


def claim_string(entity: dict, prop: str) -> str | None:
    for stmt in entity.get("claims", {}).get(prop, []):
        snak = stmt.get("mainsnak", {})
        if snak.get("snaktype") == "value":
            val = snak.get("datavalue", {}).get("value")
            if isinstance(val, str):
                return val
    return None


def wikipedia_sitelinks(entity: dict) -> dict[str, str]:
    """Sitelinks Wikipédia uniquement (exclut Commons, Wikiquote, Wikisource…)."""
    skip = {"commonswiki", "specieswiki", "metawiki", "mediawikiwiki", "wikidatawiki"}
    out = {}
    for key, link in entity.get("sitelinks", {}).items():
        if key in skip or not key.endswith("wiki"):
            continue
        code = key[:-4]
        if code.isalpha() and len(code) <= 3:
            out[code] = link["title"]
    return out


def membership_dated(entity: dict) -> int:
    """Statements P463 portant au moins un qualificatif de date."""
    n = 0
    for stmt in entity.get("claims", {}).get("P463", []):
        quals = stmt.get("qualifiers", {})
        if "P580" in quals or "P582" in quals:
            n += 1
    return n


def _year(qual_list) -> int | None:
    for q in qual_list or []:
        if q.get("snaktype") != "value":
            continue
        t = q.get("datavalue", {}).get("value", {}).get("time")
        if t and len(t) >= 5:
            try:
                return int(t[1:5])
            except ValueError:
                return None
    return None


def membership_years(entity: dict, band_qid: str) -> float | None:
    """Durée d'appartenance en années, ou None si les dates manquent."""
    for stmt in entity.get("claims", {}).get("P463", []):
        snak = stmt.get("mainsnak", {})
        val = snak.get("datavalue", {}).get("value", {})
        if not isinstance(val, dict) or val.get("id") != band_qid:
            continue
        quals = stmt.get("qualifiers", {})
        start = _year(quals.get("P580"))
        if start is None:
            continue
        end = _year(quals.get("P582")) or date.today().year
        return max(0.0, float(end - start))
    return None


# --------------------------------------------------------------------------- #
# Pageviews
# --------------------------------------------------------------------------- #

def _month_range(months: int = 24) -> tuple[str, str]:
    today = date.today()
    end_y, end_m = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    total = end_y * 12 + (end_m - 1) - (months - 1)
    start_y, start_m = divmod(total, 12)
    start_m += 1
    return f"{start_y}{start_m:02d}0100", f"{end_y}{end_m:02d}2800"


START, END = _month_range(24)


def pageviews_median(code: str, title: str) -> float | None:
    """Médiane mensuelle, ou None si la donnée n'a pas pu être obtenue.

    Renvoyer None plutôt que 0 est essentiel : un échec réseau silencieusement
    converti en zéro fausse le score des artistes les plus consultés, qui sont
    justement ceux que la limitation de débit frappe le plus.
    """
    key = f"pv_{code}_{title}"
    if PV_OFFLINE and not _cache_path(key).exists():
        return None
    enc = urllib.parse.quote(title.replace(" ", "_"), safe="")
    url = (
        "https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
        f"{code}.wikipedia/all-access/user/{enc}/monthly/{START}/{END}"
    )
    data = fetch_json(url, key, retries=4, allow_404=True)
    if data is None:
        path = _cache_path(f"pv_{code}_{title}")
        return 0.0 if path.exists() else None  # "null" en cache = 404 avéré = 0 vue
    views = [it.get("views", 0) for it in data.get("items", [])]
    return float(statistics.median(views)) if views else 0.0


def fetch_all_pageviews(records: list[dict]) -> list[str]:
    """Remplit record['pageviews'], séquentiellement et en douceur.

    Renvoie la liste des langues effectivement retenues dans le score.
    """
    jobs: list[tuple[dict, str, str]] = []
    for rec in records:
        rec["pageviews"] = 0.0
        rec["pv_missing"] = 0
        for code, title in rec["links"].items():
            if code in WIKIS:
                jobs.append((rec, code, title))

    def run(batch: list, delay: float) -> list:
        failed = []
        for i, (rec, code, title) in enumerate(batch, 1):
            cached = _cache_path(f"pv_{code}_{title}").exists()
            val = pageviews_median(code, title)
            if val is None:
                failed.append((rec, code, title))
            else:
                rec["pageviews"] += val
            if not cached:
                time.sleep(delay)
            if i % 50 == 0:
                print(f"    {i}/{len(batch)}", flush=True)
        return failed

    failed = run(jobs, PV_DELAY)
    attempt = 0
    while failed and not PV_OFFLINE and attempt < 2:
        attempt += 1
        print(f"    reprise {attempt} : {len(failed)} requetes restantes", flush=True)
        time.sleep(PV_COOLDOWN)
        failed = run(failed, PV_DELAY * 2)

    for rec, _c, _t in failed:
        rec["pv_missing"] += 1

    # Une langue partiellement collectée fausse la comparaison : un artiste privé de
    # 'en' serait massivement sous-évalué. On ne conserve donc que les langues dont la
    # couverture est complète sur tout l'échantillon, et on recalcule les sommes.
    broken = {code for _rec, code, _t in failed}
    usable = [w for w in WIKIS if w not in broken]
    if broken:
        print(f"    langues ecartees pour couverture incomplete : {', '.join(sorted(broken))}")
        for rec in records:
            rec["pageviews"] = 0.0
            for code, title in rec["links"].items():
                if code in usable:
                    val = pageviews_median(code, title)
                    rec["pageviews"] += val or 0.0
    print(f"    langues retenues dans le score : {', '.join(usable) or 'AUCUNE'}")
    return usable


# --------------------------------------------------------------------------- #
# MusicBrainz — 1 req/s imposée par leurs conditions d'usage
# --------------------------------------------------------------------------- #

def mb_release_group_count(mbid: str | None, pacer: list[float]) -> int:
    if not mbid:
        return 0
    key = f"mb_{mbid}"
    if _cache_path(key).exists():
        data = json.loads(_cache_path(key).read_text(encoding="utf-8"))
    else:
        wait = 1.1 - (time.time() - pacer[0])
        if wait > 0:
            time.sleep(wait)
        pacer[0] = time.time()
        data = fetch_json(
            f"https://musicbrainz.org/ws/2/release-group?artist={mbid}&limit=1&fmt=json",
            key, allow_404=True,
        )
    return int(data.get("release-group-count", 0)) if data else 0


# --------------------------------------------------------------------------- #
# Scoring
# --------------------------------------------------------------------------- #

def enforce_band_monotonicity(artists: list[dict]) -> list[tuple]:
    """Garantit que l'héritage n'inverse jamais l'ordre interne à un groupe.

    Le terme max(0, écart) ne préserve l'ordre que si la contribution est identique
    pour tous les membres. Dès qu'elle varie — et elle varie, ne serait-ce qu'à cause
    des dates d'appartenance manquantes — un membre moins connu peut dépasser un membre
    plus connu. On contraint donc score_final à être non croissant dans l'ordre de
    score_perso, groupe par groupe.
    """
    bands: dict[str, list[dict]] = {}
    for a in artists:
        if a["band_label"]:
            bands.setdefault(a["band_label"], []).append(a)

    corrected = []
    for label, members in bands.items():
        members.sort(key=lambda m: m["score_perso"], reverse=True)
        ceiling = None
        for m in members:
            if ceiling is not None and m["score_final"] > ceiling:
                corrected.append((m["name"], label, m["score_final"], ceiling))
                m["score_final"] = ceiling
                m["monotonicity_clamped"] = True
            ceiling = m["score_final"]
    return corrected


def zscores(values: list[float]) -> list[float]:
    logs = [math.log10(1 + max(0.0, v)) for v in values]
    mean = statistics.fmean(logs)
    sd = statistics.pstdev(logs) or 1.0
    return [(x - mean) / sd for x in logs]


def composite(records: list[dict]) -> None:
    zp = zscores([r["pageviews"] for r in records])
    zs = zscores([r["sitelinks"] for r in records])
    zt = zscores([r["statements"] for r in records])
    zd = zscores([r["releases"] for r in records])
    for i, r in enumerate(records):
        r["score_perso"] = (
            W_PAGEVIEWS * zp[i] + W_SITELINKS * zs[i] + W_STATEMENTS * zt[i] + W_DISCO * zd[i]
        )


# --------------------------------------------------------------------------- #
# Programme principal
# --------------------------------------------------------------------------- #

def main() -> int:
    spec = json.loads((ROOT / "tools" / "reference_set.json").read_text(encoding="utf-8"))
    bands_spec: dict[str, str] = spec["bands"]

    print(f"Fenêtre pageviews : {START[:6]} -> {END[:6]}   ({len(WIKIS)} editions interrogees)\n")

    all_titles = [a["wiki"] for a in spec["artists"]] + list(bands_spec.values())
    print(f"Resolution de {len(all_titles)} titres Wikipedia vers des QID…")
    qids = titles_to_qids(all_titles)
    missing = [t for t in all_titles if t not in qids]
    if missing:
        print(f"  NON RESOLUS : {', '.join(missing)}")

    print(f"  {len(qids)}/{len(all_titles)} resolus. Recuperation des entites Wikidata…")
    entities = get_entities(sorted(set(qids.values())))
    print(f"  {len(entities)} entites recuperees.")

    def build(title: str, label: str, band: str | None) -> dict | None:
        qid = qids.get(title)
        ent = entities.get(qid) if qid else None
        if not ent:
            return None
        links = wikipedia_sitelinks(ent)
        return {
            "name": label, "qid": qid, "wiki": title, "band_label": band,
            "links": links, "sitelinks": len(links),
            "statements": sum(len(v) for v in ent.get("claims", {}).values()),
            "mbid": claim_string(ent, "P434"),
            "genres": claim_values(ent, "P136"),
            "instruments": claim_values(ent, "P1303"),
            "member_of": claim_values(ent, "P463"),
            "has_period": bool(ent.get("claims", {}).get("P2031")),
            "membership_dated": membership_dated(ent),
            "_entity": ent,
        }

    artists = [r for r in (build(a["wiki"], a["wiki"], a["band"]) for a in spec["artists"]) if r]
    bands = [r for r in (build(t, lbl, None) for lbl, t in bands_spec.items()) if r]
    pool = artists + bands

    total_jobs = sum(len([c for c in r["links"] if c in WIKIS]) for r in pool)
    print(f"\nCollecte des pageviews sur {total_jobs} couples (langue, article)…")
    usable_wikis = fetch_all_pageviews(pool)

    print("\nCollecte MusicBrainz (1 req/s)…")
    pacer = [0.0]
    for r in pool:
        r["releases"] = mb_release_group_count(r["mbid"], pacer)

    composite(pool)
    band_by_label = {b["name"]: b for b in bands}

    # Héritage. La branche « albums » de la contribution exige les crédits MusicBrainz
    # et n'est pas implémentée ici : on n'utilise que la branche temporelle
    # min(1, années / 5). Quand les dates manquent, on applique CONTRIB_DEFAUT et on
    # compte le cas, parce que c'est précisément le champ le moins bien renseigné.
    CONTRIB_DEFAUT = 0.6
    fallbacks = 0
    for a in artists:
        band = band_by_label.get(a["band_label"]) if a["band_label"] else None
        a["score_groupe"] = band["score_perso"] if band else None
        if band is None:
            a["contribution"] = None
            a["contrib_source"] = "solo"
            a["gain"] = 0.0
        else:
            years = membership_years(a["_entity"], band["qid"])
            if years is None:
                a["contribution"] = CONTRIB_DEFAUT
                a["contrib_source"] = "defaut"
                fallbacks += 1
            else:
                a["contribution"] = min(1.0, years / 5.0)
                a["contrib_source"] = f"{years:.0f} ans"
            a["gain"] = LAMBDA * a["contribution"] * max(0.0, band["score_perso"] - a["score_perso"])
        a["score_final"] = a["score_perso"] + a["gain"]

    print(f"\nContribution : {fallbacks} artistes sur {len(artists)} sans dates "
          f"d'appartenance, valeur par defaut {CONTRIB_DEFAUT} appliquee.")

    inversions = enforce_band_monotonicity(artists)
    if inversions:
        print(f"Monotonie intra-groupe : {len(inversions)} inversion(s) corrigee(s)")
        for name, band, before, after in inversions:
            print(f"  {name} ({band}) {before:+.2f} -> {after:+.2f}")
    else:
        print("Monotonie intra-groupe : aucune inversion a corriger")

    artists.sort(key=lambda a: a["score_final"], reverse=True)
    for i, a in enumerate(artists, 1):
        a["rank"] = i

    print("\n" + "=" * 100)
    print(f"{'#':>3}  {'Artiste':<26} {'Groupe':<20} {'pageviews':>9} {'lg':>3} "
          f"{'perso':>7} {'contrib':>9} {'gain':>6} {'final':>7}")
    print("=" * 100)
    for a in artists:
        print(f"{a['rank']:>3}  {a['name'][:26]:<26} {(a['band_label'] or 'solo')[:20]:<20} "
              f"{int(a['pageviews']):>9} {a['sitelinks']:>3} "
              f"{a['score_perso']:+7.2f} {a['contrib_source']:>9} "
              f"{a['gain']:>6.2f} {a['score_final']:+7.2f}")

    print("\n" + "-" * 100)
    print("SCORES DES GROUPES (référence de l'héritage)")
    print("-" * 100)
    for b in sorted(bands, key=lambda b: b["score_perso"], reverse=True):
        print(f"     {b['name']:<26} pageviews={int(b['pageviews']):>9} langues={b['sitelinks']:>3} "
              f"score={b['score_perso']:+.2f}")

    n = len(artists)
    print("\n" + "-" * 100)
    print("COUVERTURE DES CHAMPS (dira si les 7 couches de composition sont alimentables)")
    print("-" * 100)
    cov = {
        "genre P136": sum(1 for a in artists if a["genres"]),
        "instrument P1303": sum(1 for a in artists if a["instruments"]),
        "debut d'activite P2031": sum(1 for a in artists if a["has_period"]),
        "identifiant MusicBrainz P434": sum(1 for a in artists if a["mbid"]),
        "appartenance P463": sum(1 for a in artists if a["member_of"]),
        "dates d'appartenance P580/P582": sum(1 for a in artists if a["membership_dated"]),
    }
    for label, k in cov.items():
        print(f"  {label:<34} {k:>3}/{n}  {100 * k / n:5.1f}%  {'#' * round(26 * k / n)}")

    by_name = {a["name"]: a for a in artists}
    print("\n" + "-" * 100)
    print("CAS DE REFERENCE")
    print("-" * 100)
    results = []
    for assertion in spec["assertions"]:
        ok, detail = evaluate(assertion, by_name, artists)
        results.append({**assertion, "passed": ok, "detail": detail})
        print(f"  [{'OK   ' if ok else 'ECHEC'}] {assertion['id']:<18} {detail}")
        print(f"            {assertion['why']}")

    passed = sum(1 for r in results if r["passed"])
    print(f"\n  {passed}/{len(results)} cas de reference valides.")

    for r in pool:
        r.pop("links", None)
        r.pop("_entity", None)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "window": {"start": START, "end": END, "wikis_requested": WIKIS,
                   "wikis_used": usable_wikis},
        "weights": {"pageviews": W_PAGEVIEWS, "sitelinks": W_SITELINKS,
                    "statements": W_STATEMENTS, "disco": W_DISCO, "lambda": LAMBDA},
        "artists": artists, "bands": bands, "coverage": cov, "assertions": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nResultat complet : {OUT.relative_to(ROOT)}")
    return 0


def evaluate(a: dict, by_name: dict, artists: list) -> tuple[bool, str]:
    kind = a["type"]
    x = by_name.get(a["a"])
    if x is None:
        return False, f"{a['a']} absent de l'echantillon"

    if kind in ("gt", "ge", "lt"):
        y = by_name.get(a["b"])
        if y is None:
            return False, f"{a['b']} absent de l'echantillon"
        op = {"gt": ">", "ge": ">=", "lt": "<"}[kind]
        ok = {"gt": x["score_final"] > y["score_final"],
              "ge": x["score_final"] >= y["score_final"],
              "lt": x["score_final"] < y["score_final"]}[kind]
        return ok, f"{a['a']} ({x['score_final']:+.2f}) {op} {a['b']} ({y['score_final']:+.2f})"

    if kind == "lifted":
        return x["gain"] > 0.01, f"{a['a']} perso {x['score_perso']:+.2f} -> final {x['score_final']:+.2f} (gain {x['gain']:.2f})"

    if kind == "top_of_band":
        peers = [p for p in artists if p["band_label"] == a["band"]]
        best = max(peers, key=lambda p: p["score_final"]) if peers else None
        return (best is not None and best["name"] == a["a"],
                f"tete de {a['band']} = {best['name'] if best else '—'} ({len(peers)} membres)")

    total = len(artists)
    if kind == "rank_top_pct":
        limit = math.ceil(total * a["pct"] / 100)
        return x["rank"] <= limit, f"{a['a']} rang {x['rank']}/{total} (seuil <= {limit})"

    if kind == "rank_bottom_pct":
        limit = total - math.ceil(total * a["pct"] / 100)
        return x["rank"] > limit, f"{a['a']} rang {x['rank']}/{total} (seuil > {limit})"

    return False, f"type d'assertion inconnu : {kind}"


if __name__ == "__main__":
    sys.exit(main())
