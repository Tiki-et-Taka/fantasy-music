"""
Recensement du vivier éligible — sans dumps de pageviews.

Compte les humains Wikidata avec occupation musicale, identifiant MusicBrainz,
au moins 6 sitelinks Wikibase (proxy de 2+ Wikipédia), et un genre parmi les
17 familles retenues. La bande de notoriété est le centile de sitelinks.

Usage : python tools/census_vivier.py
Relançable : tout est caché dans data/cache/.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CFG = json.loads((ROOT / "tools" / "census_config.json").read_text(encoding="utf-8"))
CACHE = ROOT / "data" / "cache"
OUT = ROOT / "data" / "census"
UA = "fantasy-music-census/0.3 (prototype de jeu de cartes; contact: edouard@localhost)"
SPARQL = "https://query.wikidata.org/sparql"

FLOORS_GENRE = {
    "rock": 200, "pop": 155, "metal": 130, "hiphop": 130, "electro": 110,
    "jazz": 85, "rnb": 75, "chanson": 75, "punk": 65, "folk": 55, "funk": 55,
    "latin": 50, "afro": 50, "country": 40, "reggae": 40, "blues": 35, "world": 35,
}
FLOORS_REGION = {
    "anglophone": 500, "europe": 220, "europe_fr": 180, "latam": 120,
    "afrique": 100, "asie_est": 100, "mena": 80, "est": 80, "asie_sud": 60, "autre": 40,
}
FLOORS_ERA = {"pre1970": 350, "1970s80s": 450, "1990s00s": 450, "2010s": 300}

LABELS = {
    "metal": "Métal", "punk": "Punk & hardcore", "hiphop": "Hip-hop",
    "electro": "Électronique", "reggae": "Reggae & dub", "afro": "Afro",
    "latin": "Latin", "jazz": "Jazz", "blues": "Blues", "funk": "Funk & disco",
    "rnb": "R&B & soul", "country": "Country", "folk": "Folk",
    "world": "Musiques du monde", "chanson": "Chanson & variété",
    "pop": "Pop", "rock": "Rock",
    "anglophone": "Monde anglophone", "europe_fr": "Europe francophone",
    "europe": "Europe hors FR/UK", "latam": "Amérique latine",
    "afrique": "Afrique subsaharienne", "asie_est": "Asie de l'Est",
    "mena": "Maghreb & Moyen-Orient", "est": "Europe de l'Est / ex-URSS",
    "asie_sud": "Asie du Sud & SE", "autre": "Autre",
    "pre1970": "≤ 1969", "1970s80s": "1970–1989", "1990s00s": "1990–2009",
    "2010s": "2010+", "inconnu": "inconnu",
}


def cache_path(key: str) -> Path:
    return CACHE / f"{urllib.parse.quote(key, safe='')}.json"


def fetch_json(url: str, key: str, *, data: bytes | None = None, retries: int = 8):
    path = cache_path(key)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    headers = {"User-Agent": UA, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(payload), encoding="utf-8")
            return payload
        except urllib.error.HTTPError as exc:
            wait = 30 * (attempt + 1) if exc.code == 429 else 6 * (attempt + 1)
            if exc.code in (429, 500, 502, 503) and attempt < retries - 1:
                print(f"  HTTP {exc.code}, pause {wait}s ({key[:48]})", flush=True)
                time.sleep(wait)
                continue
            print(f"  HTTP {exc.code} {key[:64]}", flush=True)
            return None
        except Exception as exc:
            if attempt < retries - 1:
                time.sleep(4 * (attempt + 1))
                continue
            print(f"  erreur {type(exc).__name__} {key[:64]}", flush=True)
            return None
    return None


def qid_of(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def year_of(time_value: str | None) -> int | None:
    if not time_value:
        return None
    s = time_value.lstrip("+")
    if len(s) < 4:
        return None
    try:
        year = int(s[:4])
    except ValueError:
        return None
    if year < 1800 or year > 2030:
        return None
    return year


def sparql_occupation(occ: str) -> list[dict]:
    """Humains P106 + P434 + sitelinks ≥ 6, avec genre / pays / dates."""
    min_sl = CFG["min_wikibase_sitelinks"]
    query = f"""
    SELECT ?item ?sl ?genre ?country ?start ?birth WHERE {{
      ?item wdt:P31 wd:Q5 .
      ?item wdt:P106 wd:{occ} .
      ?item wdt:P434 ?mbid .
      ?item wikibase:sitelinks ?sl .
      FILTER(?sl >= {min_sl})
      OPTIONAL {{ ?item wdt:P136 ?genre }}
      OPTIONAL {{ ?item wdt:P27 ?country }}
      OPTIONAL {{ ?item wdt:P2031 ?start }}
      OPTIONAL {{ ?item wdt:P569 ?birth }}
    }}
    """
    body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
    data = fetch_json(SPARQL, f"sparql_attrs_{occ}", data=body)
    if not data:
        return []
    return data.get("results", {}).get("bindings", [])


def collect_people() -> dict[str, dict]:
    path = OUT / "people_raw.json"
    state_path = OUT / "people_state.json"
    people: dict[str, dict] = {}
    done: set[str] = set()
    OUT.mkdir(parents=True, exist_ok=True)
    if path.exists():
        people = json.loads(path.read_text(encoding="utf-8"))
        print(f"Reprise : {len(people)} personnes déjà collectées", flush=True)
        return people
    if state_path.exists():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        people = state.get("people") or {}
        done = set(state.get("done") or [])
        print(f"Reprise partielle : {len(people)} personnes, {len(done)} occupations", flush=True)

    for occ in CFG["occupations"]:
        if occ in done:
            continue
        print(f"Occupation {occ}…", flush=True)
        rows = sparql_occupation(occ)
        before = len(people)
        for row in rows:
            qid = qid_of(row.get("item", {}).get("value", ""))
            if not qid.startswith("Q"):
                continue
            rec = people.get(qid)
            if rec is None:
                rec = {
                    "qid": qid,
                    "sitelinks": 0,
                    "genres": [],
                    "countries": [],
                    "start": None,
                    "birth": None,
                }
                people[qid] = rec
            sl = int(row.get("sl", {}).get("value") or 0)
            if sl > rec["sitelinks"]:
                rec["sitelinks"] = sl
            g = qid_of(row.get("genre", {}).get("value", ""))
            if g.startswith("Q") and g not in rec["genres"]:
                rec["genres"].append(g)
            c = qid_of(row.get("country", {}).get("value", ""))
            if c.startswith("Q") and c not in rec["countries"]:
                rec["countries"].append(c)
            start = year_of(row.get("start", {}).get("value"))
            if start is not None and (rec["start"] is None or start < rec["start"]):
                rec["start"] = start
            birth = year_of(row.get("birth", {}).get("value"))
            if birth is not None and (rec["birth"] is None or birth < rec["birth"]):
                rec["birth"] = birth
        done.add(occ)
        print(f"  {len(rows)} lignes  → +{len(people) - before}  unique {len(people)}", flush=True)
        state_path.write_text(
            json.dumps({"done": sorted(done), "people": people}, ensure_ascii=False),
            encoding="utf-8",
        )
        time.sleep(2.0)
    path.write_text(json.dumps(people, ensure_ascii=False), encoding="utf-8")
    return people


def claim_ids(entity: dict, prop: str) -> list[str]:
    out = []
    for stmt in entity.get("claims", {}).get(prop, []):
        snak = stmt.get("mainsnak", {})
        if snak.get("snaktype") != "value":
            continue
        val = snak.get("datavalue", {}).get("value")
        if isinstance(val, dict) and "id" in val:
            out.append(val["id"])
    return out


_genre_parents: dict[str, list[str]] = {}
_genre_resolved: dict[str, str | None] = dict(CFG["genre_seed"])


def prefetch_genre_parents(qids: set[str]) -> None:
    """Remonte P279 via SPARQL (VALUES), pas via l'API sitelinks saturée."""
    pending = {q for q in qids if q not in _genre_parents and q not in _genre_resolved}
    for _depth in range(6):
        if not pending:
            break
        batch_ids = sorted(pending)
        pending = set()
        print(f"   lot P279 : {len(batch_ids)} QID", flush=True)
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
            data = fetch_json(SPARQL, f"sparql_p279_{batch[0]}_{batch[-1]}_{len(batch)}", data=body)
            found: dict[str, list[str]] = {q: [] for q in batch}
            for row in (data or {}).get("results", {}).get("bindings", []):
                g = qid_of(row.get("g", {}).get("value", ""))
                p = qid_of(row.get("parent", {}).get("value", ""))
                if g.startswith("Q") and p.startswith("Q") and p not in found.get(g, []):
                    found.setdefault(g, []).append(p)
            for qid, parents in found.items():
                _genre_parents[qid] = parents
                for p in parents:
                    if p not in _genre_parents and p not in _genre_resolved:
                        pending.add(p)
            time.sleep(1.2)


def genre_parents(qid: str) -> list[str]:
    if qid in _genre_parents:
        return _genre_parents[qid]
    data = fetch_json(
        f"https://www.wikidata.org/w/api.php?action=wbgetentities&format=json&props=claims&ids={qid}",
        f"genre_{qid}",
    )
    ent = (data or {}).get("entities", {}).get(qid, {})
    parents = claim_ids(ent, "P279")
    _genre_parents[qid] = parents
    time.sleep(0.4)
    return parents


def resolve_genre_qid(qid: str, depth: int = 0) -> str | None:
    if qid in _genre_resolved:
        return _genre_resolved[qid]
    if depth >= 6:
        _genre_resolved[qid] = None
        return None
    for parent in genre_parents(qid):
        fam = resolve_genre_qid(parent, depth + 1)
        if fam:
            _genre_resolved[qid] = fam
            return fam
    _genre_resolved[qid] = None
    return None


def _priority(family: str) -> int:
    prio = CFG["family_priority"]
    return prio.index(family) if family in prio else 99


def best_family(genre_qids: list[str]) -> str | None:
    """Vote majoritaire. La priorité ne départage que les égalités.

    Pop et rock restent des parapluies : ils gagnent s'ils ont vraiment
    plus de tags que le reste, plus seulement parce qu'ils sont présents.
    """
    found = []
    for g in genre_qids:
        fam = resolve_genre_qid(g)
        if fam:
            found.append(fam)
    if not found:
        return None
    counts = Counter(found)
    excluded = set(CFG["excluded_families"])
    playable = Counter({f: n for f, n in counts.items() if f not in excluded})
    excluded_n = max((n for f, n in counts.items() if f in excluded), default=0)
    playable_n = max(playable.values(), default=0)
    if excluded_n > playable_n or not playable:
        return None
    best_n = max(playable.values())
    tied = [f for f, n in playable.items() if n == best_n]
    return min(tied, key=_priority)


_region_of = {}
for region, countries in CFG["regions"].items():
    for c in countries:
        _region_of[c] = region


def region_of(p27: list[str]) -> str:
    for c in p27:
        if c in _region_of:
            return _region_of[c]
    return "autre" if p27 else "inconnu"


def fetch_country_labels(country_qids: list[str]) -> dict[str, str]:
    """Libellés FR (sinon EN) des nationalités P27 — cache data/census/country_labels.json."""
    path = OUT / "country_labels.json"
    saved: dict[str, str] = {}
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
    todo = [q for q in sorted(set(country_qids)) if q.startswith("Q") and q not in saved]
    if not todo:
        return saved
    print(f"   nationalités : {len(todo)} pays à labelliser…", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    api = "https://www.wikidata.org/w/api.php"
    for i in range(0, len(todo), 50):
        batch = todo[i:i + 50]
        qs = urllib.parse.urlencode({
            "action": "wbgetentities",
            "ids": "|".join(batch),
            "props": "labels",
            "languages": "fr|en",
            "format": "json",
        })
        data = fetch_json(f"{api}?{qs}", f"country_labels_{batch[0]}_{len(batch)}", retries=6)
        for qid, ent in ((data or {}).get("entities") or {}).items():
            if ent.get("missing") is not None:
                continue
            labels = ent.get("labels") or {}
            lab = (labels.get("fr") or labels.get("en") or {}).get("value")
            if lab:
                saved[qid] = lab
        print(f"    pays {min(i + 50, len(todo))}/{len(todo)}", flush=True)
        time.sleep(0.4)
        path.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    path.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding="utf-8")
    return saved


def nationality_of(countries: list[str], labels: dict[str, str] | None = None) -> str:
    """Nationalité affichable : libellés P27 joints par « / »."""
    if not countries:
        return ""
    labels = labels if labels is not None else (
        json.loads((OUT / "country_labels.json").read_text(encoding="utf-8"))
        if (OUT / "country_labels.json").exists() else {}
    )
    names = []
    for qid in countries:
        name = labels.get(qid)
        if name and name not in names:
            names.append(name)
    return " / ".join(names)


def era_of(start: int | None, birth: int | None) -> str:
    y = start
    if y is None and birth is not None:
        y = birth + 18
    if y is None:
        return "inconnu"
    if y <= 1969:
        return "pre1970"
    if y <= 1989:
        return "1970s80s"
    if y <= 2009:
        return "1990s00s"
    return "2010s"


def fetch_occupations(qids: list[str]) -> dict[str, list[str]]:
    path = OUT / "occupations.json"
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if len(saved) >= len(qids) * 0.9:
            return saved
    out: dict[str, list[str]] = {}
    print(f"   occupations pour {len(qids)} fiches…", flush=True)
    for i in range(0, len(qids), 150):
        batch = qids[i:i + 150]
        values = " ".join(f"wd:{q}" for q in batch)
        query = f"""
        SELECT ?item ?occ WHERE {{
          VALUES ?item {{ {values} }}
          ?item wdt:P106 ?occ .
        }}
        """
        body = urllib.parse.urlencode({"query": query, "format": "json"}).encode()
        data = fetch_json(SPARQL, f"sparql_occids_{batch[0]}_{batch[-1]}_{len(batch)}", data=body)
        for row in (data or {}).get("results", {}).get("bindings", []):
            qid = qid_of(row.get("item", {}).get("value", ""))
            occ = qid_of(row.get("occ", {}).get("value", ""))
            if qid.startswith("Q") and occ.startswith("Q"):
                out.setdefault(qid, [])
                if occ not in out[qid]:
                    out[qid].append(occ)
        if i and i % 1500 == 0:
            print(f"    occ {i}/{len(qids)}", flush=True)
        time.sleep(1.2)
    path.write_text(json.dumps(out), encoding="utf-8")
    return out


def is_celebrity_leak(occupations: list[str], genre_qids: list[str], family: str) -> bool:
    """Acteur / mannequin resté dans le vivier grâce à un album pop/rock.

    On garde si la famille n'est pas un parapluie, ou s'il a un métier
    musical fort (auteur, rappeur, guitariste…). Zendaya sort, Lady Gaga reste.
    """
    celeb = set(CFG.get("celebrity_occupations") or [])
    if not any(o in celeb for o in occupations):
        return False
    if family not in CFG.get("umbrella_families", ("pop", "rock")):
        return False
    strong = set(CFG.get("strong_music_occupations") or [])
    if any(o in strong for o in occupations):
        return False
    return True


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


def check_floors(counter: Counter, floors: dict, title: str) -> None:
    print(f"\n{title}")
    print(f"  {'cle':<28} {'n':>6} {'plancher':>9} {'ecart':>8}")
    ok = True
    for key, floor in floors.items():
        n = counter.get(key, 0)
        gap = n - floor
        flag = "OK" if gap >= 0 else "MANQUE"
        if gap < 0:
            ok = False
        print(f"  {LABELS.get(key, key):<28} {n:>6} {floor:>9} {gap:>+8}  {flag}")
    extra = [k for k in counter if k not in floors]
    for k in extra:
        print(f"  {LABELS.get(k, k):<28} {counter[k]:>6} {'—':>9} {'':>8}")
    print("  → planchers tenables" if ok else "  → certains planchers sont intenables")


def main() -> int:
    print("1/3 Collecte SPARQL (occupation, sitelinks ≥ 6, attributs)…")
    people = collect_people()
    print(f"   {len(people)} personnes uniques\n")

    print("2/3 Résolution des genres (P279) et filtrage…")
    rows = []
    rejected = Counter()
    unique_genres = {g for rec in people.values() for g in rec["genres"]}
    print(f"   {len(unique_genres)} genres distincts à résoudre", flush=True)
    prefetch_genre_parents(unique_genres)
    candidates = []
    excluded = set(CFG.get("artist_exclude") or [])
    for rec in people.values():
        if rec["qid"] in excluded:
            rejected["veto editorial"] += 1
            continue
        if not rec["genres"]:
            rejected["genre absent"] += 1
            continue
        fam = CFG.get("artist_family_override", {}).get(rec["qid"]) or best_family(rec["genres"])
        if fam is None:
            rejected["genre exclu ou hors familles"] += 1
            continue
        candidates.append((rec, fam))
    umbrellas = set(CFG.get("umbrella_families") or ("pop", "rock"))
    occs = fetch_occupations([rec["qid"] for rec, fam in candidates if fam in umbrellas])
    for rec, fam in candidates:
        if is_celebrity_leak(occs.get(rec["qid"], []), rec["genres"], fam):
            rejected["celebrite non musicien"] += 1
            continue
        rows.append({
            "qid": rec["qid"],
            "sitelinks": rec["sitelinks"],
            "family": fam,
            "region": region_of(rec["countries"]),
            "countries": list(rec.get("countries") or []),
            "era": era_of(rec["start"], rec["birth"]),
        })
    print(f"   {len(rows)} éligibles   rejets : {dict(rejected)}")

    rows.sort(key=lambda r: r["sitelinks"], reverse=True)
    n = len(rows) or 1
    for i, r in enumerate(rows):
        r["band"] = band_of(i + 1, n)

    bands = Counter(r["band"] for r in rows)
    genres = Counter(r["family"] for r in rows)
    regions = Counter(r["region"] for r in rows)
    eras = Counter(r["era"] for r in rows)

    print("\n3/3 Rapport")
    print(f"Vivier éligible : {len(rows)}")
    print("Bandes (proxy sitelinks) : "
          + ", ".join(f"{k}={bands[k]}" for k in ("icones", "connus", "scene", "deep", "exclu")))

    check_floors(genres, FLOORS_GENRE, "GENRES vs planchers Série 1")
    check_floors(regions, FLOORS_REGION, "REGIONS vs planchers Série 1")
    check_floors(eras, FLOORS_ERA, "EPOQUES vs planchers Série 1")

    print("\nCases serrées (éligibles dans la bande deep, vs 30 % du plancher genre)")
    deep = Counter(r["family"] for r in rows if r["band"] == "deep")
    for fam, floor in FLOORS_GENRE.items():
        need = max(1, round(floor * 0.30))
        have = deep.get(fam, 0)
        flag = "OK" if have >= need else "MANQUE"
        print(f"  {LABELS[fam]:<28} deep={have:>5}  besoin≈{need:<4} {flag}")

    OUT.mkdir(parents=True, exist_ok=True)
    country_qids = [c for r in rows for c in (r.get("countries") or [])]
    labels = fetch_country_labels(country_qids)
    for r in rows:
        r["nationality"] = nationality_of(r.get("countries") or [], labels)
    (OUT / "eligible.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    summary = {
        "eligible": len(rows),
        "rejected": dict(rejected),
        "bands": dict(bands),
        "genres": dict(genres),
        "regions": dict(regions),
        "eras": dict(eras),
        "countries_labeled": len(labels),
        "sitelink_proxy": "wikibase:sitelinks >= 6 (pas le décompte Wikipédia strict)",
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"\nÉcrit : {OUT.relative_to(ROOT)}/summary.json  et eligible.json")
    print(f"Nationalités : {sum(1 for r in rows if r.get('nationality'))}/{len(rows)} "
          f"({len(labels)} pays labellisés)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
