"""Pick next N sérigraphie jobs and emit compact generation specs."""
from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from illustration_prompts import CATALOG  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 40
DEST = ROOT / "out" / "illustrations"
JOBS = json.loads((ROOT / "data/census/illustration_jobs.json").read_text(encoding="utf-8"))
REJ = ROOT / "data/census/illustration_rejects.json"

HEX = re.compile(r"#[0-9A-Fa-f]{6}")
PAL_HEX = {k: HEX.findall(v) for k, v in CATALOG["palettes"].items()}

REFS = {
    "voix": DEST / "serigraphie_A_voix_2_1970s80s_salle_m.png",
    "guitare": DEST / "serigraphie_A_guitare_2_1970s80s_cave_m.png",
    "batterie": DEST / "serigraphie_A_batterie_1_1960s_cave_m.png",
    "basse": DEST / "serigraphie_A_basse_7_1990s00s_cave_m.png",
    "claviers": DEST / "serigraphie_A_claviers_2_1970s80s_cave_m.png",
    "vents": DEST / "serigraphie_A_vents_5_1970s80s_salle_f.png",
    "machines": DEST / "serigraphie_A_machines_1_1990s00s_salle_m.png",
    "cordes": DEST / "serigraphie_B_cordes_1_1970s80s_salle_m.png",
}
FALLBACK = DEST / "serigraphie_A_guitare_2_1970s80s_cave_m.png"

INST_EXTRA = {
    "voix": "ONE microphone only. Empty hands except the mic. No guitar, no bass, no strap, no second mic in the void.",
    "guitare": "ONE electric guitar only. From behind: LEFT arm in front of the torso, left HAND on the fretboard, left elbow hidden. RIGHT arm hangs along the ribs, elbow TUCKED near the hip, never a sharp 90-degree elbow sticking out. Adult body proportions. If an amp is in frame: blank unmarked cabinet, no logo, no Fender, no Marshall, no letters.",
    "basse": "FOUR-STRING Precision bass, headstock cropped so tuners are not countable, or 2+2 clover. Never a guitar. Never three pegs. From behind: LEFT elbow hidden, RIGHT elbow TUCKED along the ribs, never a sharp 90-degree elbow sticking out.",
    "batterie": "Seated on a throne IN the kit, never standing. Jacket with coarse halftone. TWO sticks: right hitting, left on the snare. Floor tom on THREE LEGS on the floor. Kick, crash on a stand, charleston/hi-hat ALWAYS visible by the left foot (two stacked cymbals on a stand). Cymbals beside the head, never covering the face or mouth. Never V-arms, never cymbal-as-hat. Never a kit without charleston.",
    "claviers": "Keyboard, piano or organ clearly in frame. BOTH hands on the keys, empty palms. Never holding a hat, cup, box or object. No guitar.",
    "vents": "Alto saxophone. LEFT hand on upper keys near the neck. RIGHT hand in the MIDDLE of the body on the pearl keys, well ABOVE the bow. Bell empty below, never a hand on the bell or bow.",
    "machines": "DJ at the mixer in three-quarter BACK: real head, nape and ear, mixer in front of the torso. Never a blank erased face. Never hair poking out of a hood. Never a mask. Table with legs. Never a full rear view with the table as a barrier. Nothing floating. No guitar, no bass, no strap.",
    "cordes": "Violin, viola or cello. Bow in frame. No guitar.",
}

COSTUME = {
    "pre1960": "1950s dark tailored suit, narrow lapels, no streetwear, no hoodie, no baseball cap",
    "1960s": "mid-1960s slim mod suit or sheath, narrow lapels, no hoodie, no baseball cap",
    "1970s80s": "1970s–80s stage clothes, leather, volume, coarse halftone",
    "1990s00s": "1990s–2000s baggy streetwear, nylon",
    "2010s": "2010s sharp stage clothes, technical fabric",
}

BODY = {
    "f": "adult woman, adult proportions, adult height, never a child, never a preteen",
    "m": "adult man, adult proportions, never a child",
    "x": "androgynous adult, adult proportions, never a child",
}

FLAG = {
    "latin": "Coral as ONE rectangle, yellow as a CIRCLE, never Spain stripes.",
    "blues": "Smoke blue as a rectangle, brass as a CIRCLE, never stacked Ukraine flag bands.",
}


def color_bits(pal: str) -> str:
    hexs = PAL_HEX.get(pal) or []
    extra = FLAG.get(pal, "")
    if len(hexs) >= 2:
        return f"Figure in navy. {hexs[0]} rectangle, {hexs[1]} circle. {extra}".strip()
    return f"Figure in navy. Palette as one rectangle plus a circle. {extra}".strip()


def pose_line(instrument: str, pose_n: int) -> str:
    poses = CATALOG["poses"].get(instrument) or CATALOG["poses"]["voix"]
    return poses[max(0, min(6, pose_n - 1))]


SKIN_SWAP = {
    "deep brown": "warm peach skin on nape, ear and hands, clothes stay navy",
    "medium brown": "olive mediterranean skin on nape, ear and hands, clothes stay navy",
}

GUITAR_BODY = {
    "pre1960": "Hollow-body archtop with f-holes, or a slab Telecaster with two pickups. NEVER a Stratocaster: no contoured double-cutaway, no three single-coil pickups, no large Strat headstock.",
}


def skin_line(skin: str) -> str:
    s = skin or "warm peach skin on nape, ear and hands, clothes stay navy"
    for needle, repl in SKIN_SWAP.items():
        if needle in s:
            s = repl
            break
    return s + ". Not a dark West-African complexion. Copy print craft, not skin."


def description(j: dict) -> str:
    sil = BODY.get(j["silhouette"], BODY["m"])
    exec_txt = "tighter crop, finer halftone" if j.get("exec") == "B" else "wide shot, coarse halftone"
    parts = [
        f"Screenprint gig-poster, {sil}. {exec_txt}.",
        pose_line(j["instrument"], j["pose"]) + ".",
        (j.get("head") or "") + ".",
        skin_line(j.get("skin") or ""),
        INST_EXTRA.get(j["instrument"], ""),
        GUITAR_BODY.get(j["costume"], "") if j["instrument"] == "guitare" else "",
        COSTUME.get(j["costume"], ""),
        color_bits(j["palette"]),
        "Face hidden by turning away or brim, head exists, not a blank erased mask.",
        "Quiet cream paper, no sunburst, no photographed interior.",
        "Trading-card 3:4, no text, no logo, not a photo.",
    ]
    return " ".join(p.strip() for p in parts if p.strip())


def main() -> None:
    existing = {p.stem for p in DEST.glob("*.png")}
    rej = json.loads(REJ.read_text(encoding="utf-8")) if REJ.exists() else {}
    marked = 0
    for j in JOBS:
        if j["id"] in existing and rej.get(j["id"]) != "reject" and rej.get(j["id"]) != "ok":
            rej[j["id"]] = "ok"
            marked += 1
    REJ.write_text(json.dumps(rej, ensure_ascii=False, indent=2), encoding="utf-8")

    seri = [j for j in JOBS if j["style"] == "serigraphie"]
    done = [j for j in seri if j["id"] in existing]
    todo = [j for j in seri if j["id"] not in existing]
    print(f"marked_ok {marked}  done {len(done)}/{len(seri)}  todo {len(todo)}")

    by_inst: dict[str, list] = defaultdict(list)
    for j in todo:
        by_inst[j["instrument"]].append(j)
    order = ["voix", "guitare", "batterie", "basse", "claviers", "vents", "machines", "cordes"]
    picked: list[dict] = []
    idx = {k: 0 for k in order}
    while len(picked) < N:
        progressed = False
        for inst in order:
            if len(picked) >= N:
                break
            lst = by_inst.get(inst) or []
            i = idx[inst]
            if i < len(lst):
                picked.append(lst[i])
                idx[inst] = i + 1
                progressed = True
        if not progressed:
            break

    specs = []
    for j in picked:
        ref = REFS.get(j["instrument"], FALLBACK)
        if not ref.exists():
            ref = FALLBACK
        specs.append({
            "id": j["id"],
            "instrument": j["instrument"],
            "palette": j["palette"],
            "costume": j["costume"],
            "silhouette": j["silhouette"],
            "pose": j["pose"],
            "ref": str(ref).replace("\\", "/"),
            "description": description(j),
        })
    out = DEST / "_queue_next.json"
    out.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
    for s in specs:
        print(s["id"])
    print(f"queued {len(specs)} -> {out}")


if __name__ == "__main__":
    main()
