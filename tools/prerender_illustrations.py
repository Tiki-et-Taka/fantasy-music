"""
Pré-rend les plaques PNG en WebP (et AVIF si pillow-heif est installé).

Source : out/illustrations/*.png
Cible  : out/illustrations/webp/*.webp
         out/illustrations/avif/*.avif  (--avif)

Usage :
  python tools/prerender_illustrations.py
  python tools/prerender_illustrations.py --limit 20
  python tools/prerender_illustrations.py --avif --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "out" / "illustrations"
WEBP = SRC / "webp"
AVIF = SRC / "avif"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def convert_one(src: Path, dest: Path, fmt: str, quality: int, force: bool) -> str:
    if dest.exists() and not force:
        if dest.stat().st_mtime >= src.stat().st_mtime:
            return "skip"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")
        save_kw: dict = {"quality": quality}
        if fmt == "WEBP":
            save_kw["method"] = 6
        im.save(dest, format=fmt, **save_kw)
    return "ok"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--avif", action="store_true", help="Aussi AVIF (nécessite pillow-heif)")
    args = ap.parse_args()

    pngs = sorted(SRC.glob("*.png"))
    if args.limit:
        pngs = pngs[: args.limit]
    if not pngs:
        print(f"Aucun PNG dans {SRC.relative_to(ROOT)}")
        return 0

    avif_ok = False
    if args.avif:
        try:
            import pillow_heif  # type: ignore

            pillow_heif.register_avif_opener()
            avif_ok = True
        except ImportError:
            print("pillow-heif absent — AVIF ignoré (pip install pillow-heif)", flush=True)

    stats = {"webp_ok": 0, "webp_skip": 0, "avif_ok": 0, "avif_skip": 0, "err": 0}
    for i, src in enumerate(pngs, 1):
        try:
            st = convert_one(src, WEBP / f"{src.stem}.webp", "WEBP", args.quality, args.force)
            stats["webp_ok" if st == "ok" else "webp_skip"] += 1
            if avif_ok:
                st2 = convert_one(src, AVIF / f"{src.stem}.avif", "AVIF", args.quality, args.force)
                stats["avif_ok" if st2 == "ok" else "avif_skip"] += 1
        except Exception as exc:  # noqa: BLE001
            stats["err"] += 1
            print(f"  ERR {src.name}: {exc}", flush=True)
        if i % 100 == 0 or i == len(pngs):
            print(f"  {i}/{len(pngs)} …", flush=True)

    print(
        f"WebP : {stats['webp_ok']} écrits, {stats['webp_skip']} déjà à jour"
        + (f" · AVIF : {stats['avif_ok']} écrits, {stats['avif_skip']} skip" if args.avif else "")
        + (f" · erreurs {stats['err']}" if stats["err"] else "")
    )
    return 1 if stats["err"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
