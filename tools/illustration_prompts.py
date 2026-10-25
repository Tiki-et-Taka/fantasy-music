"""Construit les jobs d'illustration : une entrée par plaque distincte, pas par carte."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CATALOG = json.loads((ROOT / "tools" / "illustration_catalog.json").read_text(encoding="utf-8"))
DRAFT = ROOT / "docs" / "serie-1-draft.csv"
OUT = ROOT / "data" / "census" / "illustration_jobs.json"


PALETTE_KEYS = list(CATALOG["palettes"].keys())
HEADS = CATALOG["heads"]


def pick_palette(jid: str) -> tuple[str, str]:
    idx = int(hashlib.md5(jid.encode("utf-8")).hexdigest(), 16) % len(PALETTE_KEYS)
    key = PALETTE_KEYS[idx]
    return key, CATALOG["palettes"][key]


def pick_head(jid: str, costume: str = "", silhouette: str = "") -> str:
    pool = (
        (CATALOG.get("heads_for_silhouette") or {}).get(silhouette)
        or (CATALOG.get("heads_for_costume") or {}).get(costume)
        or HEADS
    )
    idx = int(hashlib.md5(f"{jid}|head".encode("utf-8")).hexdigest(), 16) % len(pool)
    return pool[idx]


def pick_skin(jid: str) -> str:
    pool = CATALOG.get("skins") or [""]
    idx = int(hashlib.md5(f"{jid}|skin".encode("utf-8")).hexdigest(), 16) % len(pool)
    return pool[idx]


def venue_line(venue: str, costume: str, style: str = "") -> str:
    costume_over = (CATALOG.get("venue_for_costume") or {}).get(costume) or {}
    era = costume_over.get(venue)
    graphic = ((CATALOG.get("venue_for_style") or {}).get(style) or {}).get(venue)
    if graphic and era:
        return f"{graphic} {era}"
    return graphic or era or CATALOG["venue"][venue]


def color_line(style: str, palette: str) -> str:
    if style == "serigraphie":
        return (
            f"Figure and instrument in one dark ink (navy or charcoal), never in a bright hue. "
            f"Palette hues used only as flat background fields: {palette}. "
            "Never a national flag: no blue-over-yellow bands, no red-and-yellow stripes. "
            "One rectangle plus a circle, or blocks at right angles, not two parallel stripes."
        )
    if style == "contrejour":
        return (
            f"Near-black cut-out figure. Halo, haze and rim light tinted with {palette}. "
            "The field can stay mid-value dusk, not crushed black."
        )
    return (
        f"Ink and splatters on visible pale paper: {palette}. "
        "Keep the paper readable. Do not default to crimson or to a black void."
    )


def build_prompt(style: str, exec_id: str, instrument: str, pose_n: int,
                 costume: str, venue: str, silhouette: str, palette: str,
                 head: str, skin: str = "") -> str:
    poses = CATALOG["poses"].get(instrument) or CATALOG["poses"]["voix"]
    pose = poses[max(0, min(6, pose_n - 1))]
    exec_txt = CATALOG["execs"][style][exec_id]
    lock = CATALOG["style_lock"][style]
    inst_lock = (CATALOG.get("instrument_lock") or {}).get(instrument, "")
    parts = [
        lock + ".",
        exec_txt + ".",
        color_line(style, palette) + ".",
        "Figurative concert illustration of a performing musician, not a portrait, not a photograph.",
        "Face hidden, no facial features, no identifiable likeness.",
        CATALOG["silhouette"][silhouette] + ".",
        head + ".",
    ]
    if skin:
        parts.append(skin.rstrip(".") + ".")
        parts.append("Copy the screenprint craft of any reference, not its skin tone.")
    parts += [
        "Do not copy a long wet hair curtain over the face.",
        pose + ".",
        "The instrument is clearly visible and is the focus of the pose.",
    ]
    if inst_lock:
        parts.append(inst_lock.rstrip(".") + ".")
    parts += [
        CATALOG["costume"][costume] + ".",
        venue_line(venue, costume, style) + ".",
        CATALOG["flux_tail"],
    ]
    return " ".join(parts)


def job_id(style: str, exec_id: str, instrument: str, pose_n: int,
           costume: str, venue: str, silhouette: str) -> str:
    return f"{style}_{exec_id}_{instrument}_{pose_n}_{costume}_{venue}_{silhouette}"


def load_draft() -> list[dict]:
    with DRAFT.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh, delimiter=";"))


def make_job(
    style: str, exec_id: str, instrument: str, pose_n: int,
    costume: str, venue: str, silhouette: str, rarete: str = "diamant",
    exemples: list[str] | None = None,
) -> dict:
    jid = job_id(style, exec_id, instrument, pose_n, costume, venue, silhouette)
    pal_name, pal = pick_palette(jid)
    head = pick_head(jid, costume, silhouette)
    skin = pick_skin(jid)
    names = exemples or []
    return {
        "id": jid,
        "plaque": f"{style}|{instrument}|{pose_n}|{costume}|{venue}|{silhouette}",
        "style": style,
        "exec": exec_id,
        "instrument": instrument,
        "pose": pose_n,
        "costume": costume,
        "venue": venue,
        "silhouette": silhouette,
        "palette": pal_name,
        "palette_label": CATALOG.get("palette_labels", {}).get(pal_name, pal_name),
        "head": head,
        "skin": skin,
        "rarete": rarete,
        "prompt": build_prompt(
            style, exec_id, instrument, pose_n, costume, venue, silhouette, pal, head, skin
        ),
        "cards": max(1, len(names)),
        "exemples": names[:3],
    }


def fill_mythic_encre() -> int:
    sys.path.insert(0, str(ROOT / "tools"))
    from attach_illustration import (  # noqa: E402
        CFG,
        EXEC_OF,
        VENUE_OF,
        VENUE_ORDER,
        costume_of,
        head_ok_for_silhouette,
        illustration_stem,
        load_stock,
        plaque_resolved_stem,
        pose_of,
    )

    serie_path = ROOT / "data" / "census" / "serie1.json"
    titles_path = ROOT / "data" / "census" / "qid_titles.json"
    if not serie_path.exists():
        print("serie1.json manquant")
        return 1
    serie = json.loads(serie_path.read_text(encoding="utf-8"))
    titles = json.loads(titles_path.read_text(encoding="utf-8")) if titles_path.exists() else {}
    overrides = CFG.get("artist_plaque_override") or {}
    mythics = [r for r in serie if r.get("rarete") == "diamant"]
    mythics.sort(key=lambda r: (
        0 if r.get("qid") in overrides else 1,
        r.get("rank_serie") or 0,
    ))
    stock = load_stock()
    exec_id = EXEC_OF.get("diamant", "B")
    venues_ok = ["stade", "festival", "salle"]
    taken: set[str] = set()
    new_jobs: list[dict] = []
    assigned = 0
    missing_slots = 0

    def head_ok(ex: str, instr: str, pose: int, costume: str, venue: str, sil: str) -> bool:
        stem = illustration_stem("encre", ex, instr, pose, costume, venue, sil)
        return head_ok_for_silhouette(stem, costume, sil)

    def slot_key(instr: str, pose: int, costume: str, venue: str, sil: str) -> str | None:
        resolved = plaque_resolved_stem("encre", exec_id, instr, pose, costume, venue, sil)
        if resolved:
            return resolved
        if head_ok(exec_id, instr, pose, costume, venue, sil):
            return illustration_stem("encre", exec_id, instr, pose, costume, venue, sil)
        other = "A" if exec_id == "B" else "B"
        if head_ok(other, instr, pose, costume, venue, sil):
            return illustration_stem("encre", other, instr, pose, costume, venue, sil)
        return None

    def iter_slots(instr: str, costume: str, venue0: str, sil: str, start_pose: int):
        venues = [venue0] + [v for v in venues_ok if v != venue0]
        poses = [start_pose] + [p for p in range(1, 8) if p != start_pose]
        for venue in venues:
            for pose in poses:
                yield pose, venue

    for rec in mythics:
        qid = rec.get("qid") or ""
        name = (titles.get(qid) or {}).get("fr") or (titles.get(qid) or {}).get("en") or qid
        if isinstance(titles.get(qid), str):
            name = titles[qid]
        sil = rec.get("silhouette") or "x"
        instr = rec.get("instrument") or "voix"
        costume = costume_of(rec.get("era_peak") or rec.get("era"), rec.get("peak_year"))
        venue0 = VENUE_OF.get(rec.get("band") or "", "stade")
        start_pose = pose_of(qid)
        forced = overrides.get(qid) or ""
        parts = str(forced).split("|")
        if len(parts) == 6 and parts[0] == "encre":
            instr, costume, venue0, sil = parts[1], parts[3], parts[4], parts[5]
            try:
                start_pose = int(parts[2])
            except ValueError:
                pass
        found = False
        for pose, venue in iter_slots(instr, costume, venue0, sil, start_pose):
            key = slot_key(instr, pose, costume, venue, sil)
            if key is None or key in taken:
                continue
            taken.add(key)
            assigned += 1
            found = True
            resolved = plaque_resolved_stem("encre", exec_id, instr, pose, costume, venue, sil)
            if resolved:
                break
            new_jobs.append(make_job(
                "encre", exec_id, instr, pose, costume, venue, sil,
                rarete="diamant", exemples=[name],
            ))
            missing_slots += 1
            break
        if not found:
            print(f"  pas de slot encre pour {name} ({instr} {costume} {sil})")

    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else []
    by_id = {j["id"]: j for j in existing}
    for job in new_jobs:
        by_id[job["id"]] = job
    jobs = sorted(by_id.values(), key=lambda j: j["id"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"Mythiques : {len(mythics)}  encres déjà là : {assigned - missing_slots}  "
        f"à générer : {len(new_jobs)}"
    )
    for job in new_jobs:
        print(f"  + {job['id']}  {job['exemples'][0] if job['exemples'] else ''}")
    print(f"Jobs totaux : {len(jobs)} → {OUT.relative_to(ROOT)}")
    return 0 if assigned == len(mythics) else 1


def main() -> int:
    if "--fill-mythics" in sys.argv:
        return fill_mythic_encre()
    rows = load_draft()
    buckets: dict[str, dict] = {}
    cards_of: dict[str, list[str]] = defaultdict(list)
    for rec in rows:
        plaque = rec.get("plaque") or ""
        parts = plaque.split("|")
        if len(parts) != 6:
            continue
        style, instrument, pose_s, costume, venue, silhouette = parts
        pose_n = int(pose_s)
        exec_id = CATALOG["exec_of_rarete"].get(rec.get("rarete") or "", "A")
        jid = job_id(style, exec_id, instrument, pose_n, costume, venue, silhouette)
        cards_of[jid].append(rec["artiste"])
        if jid in buckets:
            continue
        buckets[jid] = make_job(
            style, exec_id, instrument, pose_n, costume, venue, silhouette,
            rarete=rec.get("rarete") or "",
            exemples=[rec["artiste"]],
        )

    jobs = sorted(buckets.values(), key=lambda j: (-len(cards_of[j["id"]]), j["id"]))
    for job in jobs:
        job["cards"] = len(cards_of[job["id"]])
        job["exemples"] = cards_of[job["id"]][:3]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")

    styles = Counter(j["style"] for j in jobs)
    print(f"{len(rows)} cartes → {len(jobs)} plaques à générer → {OUT.relative_to(ROOT)}")
    print("Styles : " + ", ".join(f"{k}={v}" for k, v in styles.most_common()))
    reused = sum(1 for j in jobs if j["cards"] > 1)
    print(f"Plaques partagées par plusieurs cartes : {reused}")
    print(f"Max de cartes sur une plaque : {jobs[0]['cards']} ({', '.join(jobs[0]['exemples'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
