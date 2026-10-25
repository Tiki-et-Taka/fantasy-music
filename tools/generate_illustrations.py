"""Génère les plaques via Fal.ai Flux (InvokeAI en secours).

Usage :
  python tools/illustration_prompts.py
  python tools/generate_illustrations.py --lookdev
  python tools/generate_illustrations.py --limit 20
  python tools/generate_illustrations.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

JOBS = ROOT / "data" / "census" / "illustration_jobs.json"
DEST = ROOT / "out" / "illustrations"
REFS = ROOT / "data" / "census" / "invoke_refs.json"
BOARDS = ROOT / "data" / "census" / "style_boards"
DA_REFS = {
    "serigraphie": ROOT / "references" / "direction-serigraphie.jpg",
    "contrejour": ROOT / "references" / "direction-contrejour.jpg",
    "encre": ROOT / "references" / "direction-encre.jpg",
}
IP_WEIGHT = {
    "serigraphie": 0.55,
    "contrejour": 0.50,
    "encre": 0.52,
}
CATALOG = json.loads((ROOT / "tools" / "illustration_catalog.json").read_text(encoding="utf-8"))
INVOKE_DEFAULT = "http://127.0.0.1:9090"
FAL_MODELS = {
    "schnell": "https://fal.run/fal-ai/flux/schnell",
    "flash": "https://fal.run/fal-ai/flux-2/flash",
    "flash-edit": "https://fal.run/fal-ai/flux-2/flash/edit",
}
LOOKDEV_WANT = (
    ("voix", "encre", "f"),
    ("voix", "serigraphie", "m"),
    ("batterie", None, "m"),
    ("vents", "contrejour", None),
    ("guitare", None, "f"),
    ("machines", None, None),
)
ILLUSTRATION_HINTS = (
    "dreamshaper", "rev animated", "revanimated", "anything",
    "counterfeit", "comic", "illustration", "openjourney", "niji",
)
PHOTOREAL_HINTS = (
    "realistic", "photogasm", "photoreal", "stockphoto", "realvis", "epicreal",
)


def load_env() -> None:
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.split("=", 1)
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def lookdev(jobs: list[dict]) -> list[dict]:
    picked, used = [], set()
    for instr, style, sil in LOOKDEV_WANT:
        hit = next((
            j for j in jobs
            if j["id"] not in used
            and j["instrument"] == instr
            and (style is None or j["style"] == style)
            and (sil is None or j["silhouette"] == sil)
        ), None)
        if hit is None:
            hit = next((j for j in jobs if j["id"] not in used and j["instrument"] == instr), None)
        if hit:
            picked.append(hit)
            used.add(hit["id"])
    return picked or jobs[:6]


def http_json(url: str, payload: dict | None = None, timeout: int = 60) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"HTTP {exc.code} {url} {body}") from exc


def seed_of(job_id: str) -> int:
    return int(hashlib.sha256(job_id.encode()).hexdigest()[:8], 16) % (2**31)


def ident_of(model: dict) -> dict:
    return {
        "key": model["key"],
        "hash": model["hash"],
        "name": model["name"],
        "base": model["base"],
        "type": model["type"],
    }


def pick_model(base: str, model_type: str, name_part: str = "") -> dict | None:
    models = http_json(f"{base}/api/v2/models/?model_type={model_type}").get("models") or []
    if name_part:
        hit = next((m for m in models if name_part.lower() in (m.get("name") or "").lower()), None)
        if hit:
            return hit
    return models[0] if models else None


def pick_sd15_model(base: str) -> dict:
    forced = os.environ.get("INVOKE_MODEL") or ""
    models = http_json(f"{base}/api/v2/models/?model_type=main").get("models") or []
    sd = [m for m in models if m.get("base") == "sd-1" and m.get("type") == "main"]
    if forced:
        hit = next((m for m in sd if forced in (m.get("name") or "") or m.get("key") == forced), None)
        if hit:
            return hit
        raise RuntimeError(f"INVOKE_MODEL={forced} introuvable parmi les SD 1.5.")
    for hint in ILLUSTRATION_HINTS:
        hit = next((m for m in sd if hint in (m.get("name") or "").lower()), None)
        if hit:
            return hit
    non_photo = [
        m for m in sd
        if not any(h in (m.get("name") or "").lower() for h in PHOTOREAL_HINTS)
    ]
    if non_photo:
        return non_photo[0]
    names = ", ".join(m.get("name") or "?" for m in sd) or "(aucun)"
    raise RuntimeError(
        "Aucun checkpoint illustration (DreamShaper, etc.). "
        f"Les modèles dispo sont photoréalistes : {names}. "
        "Un modèle photo ne peut pas sortir les plaques sérigraphie / encre / contre-jour."
    )


def paper_grain(img: Image.Image, amount: int = 18, mix: float = 0.12) -> Image.Image:
    noise = Image.effect_noise(img.size, amount).convert("L")
    noise_rgb = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(img.convert("RGB"), noise_rgb, mix)


def board_serigraphie() -> Image.Image:
    w, h = 512, 768
    paper, navy, ochre = (239, 230, 210), (30, 58, 110), (217, 150, 43)
    img = Image.new("RGB", (w, h), paper)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, int(h * 0.62), w, h], fill=navy)
    draw.polygon([(0, 70), (w, 20), (w, 300), (0, 370)], fill=ochre)
    rng = random.Random(7)
    for y in range(6, h, 6):
        for x in range(6, w, 6):
            if (x + y + rng.randint(0, 3)) % 12:
                continue
            r = 2 if y < h * 0.6 else 1
            fill = navy if y < h * 0.55 else paper
            draw.ellipse([x - r, y - r, x + r, y + r], fill=fill)
    return paper_grain(img)


def board_contrejour() -> Image.Image:
    w, h = 512, 768
    img = Image.new("RGB", (w, h), (14, 26, 31))
    px = img.load()
    cx, cy = w * 0.55, h * 0.38
    for y in range(h):
        for x in range(w):
            d = ((x - cx) ** 2 / 1.15 + (y - cy) ** 2) ** 0.5
            t = max(0.0, 1.0 - d / 280.0) ** 1.6
            r = int(14 + (216 - 14) * t)
            g = int(26 + (180 - 26) * t)
            b = int(31 + (113 - 31) * t)
            if y > h * 0.78:
                fade = (y - h * 0.78) / (h * 0.22)
                r, g, b = (int(c * (1 - 0.72 * fade)) for c in (r, g, b))
            px[x, y] = (r, g, b)
    return paper_grain(img, 22, 0.14)


def board_encre() -> Image.Image:
    w, h = 512, 768
    img = Image.new("RGBA", (w, h), (20, 16, 18, 255))
    draw = ImageDraw.Draw(img, "RGBA")
    draw.polygon([(210, 0), (310, 0), (275, 430), (235, 430)], fill=(210, 205, 195, 80))
    rng = random.Random(11)
    for _ in range(48):
        x, y = rng.randint(0, w), rng.randint(0, h)
        rad = rng.randint(8, 75)
        col = (158, 42, 43, rng.randint(45, 150)) if rng.random() > 0.35 else (8, 6, 6, rng.randint(60, 170))
        draw.ellipse([x - rad, y - rad, x + rad, y + rad], fill=col)
        for __ in range(10):
            dx, dy = rng.randint(-100, 100), rng.randint(-100, 100)
            rr = rng.randint(1, 5)
            draw.ellipse([x + dx - rr, y + dy - rr, x + dx + rr, y + dy + rr], fill=col)
    return paper_grain(img.convert("RGB"), 20, 0.13)


def write_style_boards() -> dict[str, Path]:
    BOARDS.mkdir(parents=True, exist_ok=True)
    makers = {
        "serigraphie": board_serigraphie,
        "contrejour": board_contrejour,
        "encre": board_encre,
    }
    paths = {}
    for style, maker in makers.items():
        path = BOARDS / f"{style}.png"
        maker().save(path, "PNG")
        paths[style] = path
    return paths


def upload_image(base: str, path: Path) -> str:
    boundary = "----plaqueBoundary"
    payload = path.read_bytes()
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
    url = f"{base}/api/v1/images/upload?image_category=user&is_intermediate=false"
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            dto = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_err = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"upload {path.name}: HTTP {exc.code} {body_err}") from exc
    name = dto.get("image_name")
    if not name:
        raise RuntimeError(f"upload {path.name}: pas de image_name")
    return name


def ensure_style_refs(base: str) -> dict[str, str]:
    boards = write_style_boards()
    refs = {"serigraphie": upload_image(base, boards["serigraphie"])}
    for style, path in DA_REFS.items():
        if not path.exists():
            refs[style] = upload_image(base, boards[style])
            continue
        refs[style] = upload_image(base, path)
    REFS.parent.mkdir(parents=True, exist_ok=True)
    REFS.write_text(json.dumps(refs, ensure_ascii=False, indent=2), encoding="utf-8")
    return refs


def invoke_graph(model: dict, prompt: str, negative: str, seed: int,
                 ip_model: dict | None, ref_name: str | None,
                 ip_weight: float = 0.52) -> dict:
    nodes = {
        "model": {"id": "model", "type": "main_model_loader", "model": ident_of(model), "use_cache": False},
        "pos": {"id": "pos", "type": "compel", "prompt": prompt, "use_cache": False},
        "neg": {"id": "neg", "type": "compel", "prompt": negative, "use_cache": False},
        "noise": {
            "id": "noise", "type": "noise", "seed": seed,
            "width": 512, "height": 768, "use_cpu": True, "use_cache": False,
        },
        "denoise": {
            "id": "denoise", "type": "denoise_latents",
            "steps": 28, "cfg_scale": 7.0, "scheduler": "dpmpp_2m_k",
            "denoising_start": 0.0, "denoising_end": 1.0, "use_cache": False,
        },
        "l2i": {
            "id": "l2i", "type": "l2i", "is_intermediate": False,
            "fp32": True, "tiled": True, "use_cache": False,
        },
    }
    edges = [
        {"source": {"node_id": "model", "field": "clip"}, "destination": {"node_id": "pos", "field": "clip"}},
        {"source": {"node_id": "model", "field": "clip"}, "destination": {"node_id": "neg", "field": "clip"}},
        {"source": {"node_id": "model", "field": "unet"}, "destination": {"node_id": "denoise", "field": "unet"}},
        {"source": {"node_id": "pos", "field": "conditioning"}, "destination": {"node_id": "denoise", "field": "positive_conditioning"}},
        {"source": {"node_id": "neg", "field": "conditioning"}, "destination": {"node_id": "denoise", "field": "negative_conditioning"}},
        {"source": {"node_id": "noise", "field": "noise"}, "destination": {"node_id": "denoise", "field": "noise"}},
        {"source": {"node_id": "denoise", "field": "latents"}, "destination": {"node_id": "l2i", "field": "latents"}},
        {"source": {"node_id": "model", "field": "vae"}, "destination": {"node_id": "l2i", "field": "vae"}},
    ]
    if ip_model and ref_name:
        nodes["ipa"] = {
            "id": "ipa",
            "type": "ip_adapter",
            "image": {"image_name": ref_name},
            "ip_adapter_model": ident_of(ip_model),
            "clip_vision_model": "ViT-H",
            "weight": ip_weight,
            "method": "style",
            "begin_step_percent": 0.0,
            "end_step_percent": 0.70,
            "use_cache": False,
        }
        edges.append({
            "source": {"node_id": "ipa", "field": "ip_adapter"},
            "destination": {"node_id": "denoise", "field": "ip_adapter"},
        })
    return {"id": "plaque", "nodes": nodes, "edges": edges}


def find_image_name(obj) -> str | None:
    results = ((obj.get("session") or {}).get("results") or {})
    for val in results.values():
        if isinstance(val, dict) and val.get("type") == "image_output":
            name = (val.get("image") or {}).get("image_name")
            if name:
                return name
    return None


def generate_invoke(job: dict, base: str, model: dict,
                    ip_model: dict | None, refs: dict[str, str]) -> bytes:
    negative = CATALOG["negative"]
    style = job.get("style") or ""
    graph = invoke_graph(
        model, job["prompt"], negative, seed_of(job["id"]),
        ip_model, refs.get(style),
        IP_WEIGHT.get(style, 0.52),
    )
    enq = http_json(
        f"{base}/api/v1/queue/default/enqueue_batch",
        {"batch": {"graph": graph, "runs": 1}, "prepend": False},
        timeout=60,
    )
    ids = enq.get("item_ids") or []
    if not ids:
        raise RuntimeError(f"file d'attente vide pour {job['id']}")
    item_id = ids[0]
    deadline = time.time() + 240
    while time.time() < deadline:
        item = http_json(f"{base}/api/v1/queue/default/i/{item_id}", timeout=30)
        status = item.get("status")
        if status == "completed":
            name = find_image_name(item)
            if not name:
                raise RuntimeError(f"pas d'image dans le résultat {job['id']}")
            url = f"{base}/api/v1/images/i/{urllib.parse.quote(name)}/full"
            with urllib.request.urlopen(url, timeout=60) as resp:
                return resp.read()
        if status in ("failed", "canceled"):
            err = item.get("error") or item.get("error_type") or status
            raise RuntimeError(f"{status}: {err}")
        time.sleep(1.5)
    raise TimeoutError(f"timeout InvokeAI {job['id']}")


def as_png(blob: bytes) -> bytes:
    from io import BytesIO
    im = Image.open(BytesIO(blob)).convert("RGB")
    out = BytesIO()
    im.save(out, "PNG")
    return out.getvalue()


def da_data_uri(style: str) -> str:
    import base64
    path = DA_REFS.get(style or "")
    if path is None or not path.exists():
        raise RuntimeError(f"référence DA manquante pour {style}")
    mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode()}"


def generate_fal(job: dict, key: str, model: str = "schnell") -> bytes:
    endpoint = FAL_MODELS.get(model) or FAL_MODELS["schnell"]
    payload: dict = {
        "prompt": job["prompt"],
        "image_size": {"width": 768, "height": 1024},
        "num_images": 1,
        "enable_safety_checker": True,
        "output_format": "png",
        "seed": seed_of(job["id"]),
    }
    if model == "schnell":
        payload["num_inference_steps"] = 4
    elif model == "flash-edit":
        payload["prompt"] = (
            "Keep the exact artistic medium, paper, ink and color palette of the reference. "
            "Change only the subject and pose. " + job["prompt"]
        )
        payload["guidance_scale"] = 2.5
        payload["enable_prompt_expansion"] = False
        payload["image_urls"] = [da_data_uri(job.get("style") or "")]
    else:
        payload["guidance_scale"] = 2.5
        payload["enable_prompt_expansion"] = False
    req = urllib.request.Request(
        endpoint, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Key {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:800]
        raise RuntimeError(f"Fal HTTP {exc.code} {body}") from exc
    url = (data.get("images") or [{}])[0].get("url")
    if not url:
        raise RuntimeError(f"pas d'image renvoyée pour {job['id']}")
    with urllib.request.urlopen(url, timeout=120) as img:
        return as_png(img.read())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lookdev", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="regénère même si le PNG existe")
    parser.add_argument("--backend", choices=("invoke", "fal"), default="fal")
    parser.add_argument("--fal-model", choices=tuple(FAL_MODELS), default="schnell")
    parser.add_argument("--out", type=Path, help="dossier de sortie (défaut : out/illustrations)")
    parser.add_argument("--style", action="append", default=[], help="filtre un style (répétable)")
    args = parser.parse_args()
    dest_dir = args.out.resolve() if args.out else DEST

    if not JOBS.exists():
        print("Lancer d'abord : python tools/illustration_prompts.py")
        return 1
    jobs = json.loads(JOBS.read_text(encoding="utf-8"))
    if args.style:
        wanted = set(args.style)
        jobs = [j for j in jobs if j.get("style") in wanted]
    if args.lookdev:
        jobs = lookdev(jobs)

    load_env()
    dest_dir.mkdir(parents=True, exist_ok=True)
    if args.force:
        todo = list(jobs)
    else:
        todo = [j for j in jobs if not (dest_dir / f"{j['id']}.png").exists()]
    if args.limit:
        todo = todo[: args.limit]
    skip = len(jobs) - len(todo)
    try:
        dest_rel = dest_dir.relative_to(ROOT)
    except ValueError:
        dest_rel = dest_dir
    extra = f"  modèle {args.fal_model}" if args.backend == "fal" else ""
    print(f"{len(jobs)} jobs, {skip} déjà là, {len(todo)} à faire → {dest_rel}{extra}")
    if args.dry_run:
        for job in todo:
            print(f"  {job['id']}  ({job['cards']} cartes)  {job['exemples'][0]}")
        return 0

    invoke_base = (os.environ.get("INVOKE_URL") or INVOKE_DEFAULT).rstrip("/")
    model = None
    ip_model = None
    refs: dict[str, str] = {}
    if args.backend == "invoke":
        try:
            ver = http_json(f"{invoke_base}/api/v1/app/version")
            model = pick_sd15_model(invoke_base)
            ip_model = pick_model(invoke_base, "ip_adapter", "ip-adapter_sd15")
            refs = ensure_style_refs(invoke_base)
            extra = f"  IP-Adapter {ip_model['name']}" if ip_model and refs else "  (sans IP-Adapter)"
            print(f"InvokeAI {ver.get('version')}  modèle {model['name']}{extra}")
        except Exception as exc:
            print(f"InvokeAI injoignable ou modèle manquant ({exc}).")
            return 1
    else:
        if not os.environ.get("FAL_KEY"):
            print("FAL_KEY manquante.")
            return 1

    ok, fail = 0, 0
    for i, job in enumerate(todo, 1):
        dest = dest_dir / f"{job['id']}.png"
        try:
            t0 = time.time()
            last_exc: Exception | None = None
            blob = b""
            for attempt in range(2):
                try:
                    if args.backend == "invoke":
                        blob = generate_invoke(job, invoke_base, model, ip_model, refs)
                    else:
                        blob = generate_fal(job, os.environ["FAL_KEY"], args.fal_model)
                    last_exc = None
                    break
                except Exception as exc:
                    last_exc = exc
                    time.sleep(3)
            if last_exc:
                raise last_exc
            dest.write_bytes(blob)
            ok += 1
            print(f"  {i}/{len(todo)}  {dest.name}  {time.time()-t0:.0f}s  ({job['cards']} cartes)  {job['exemples'][0]}", flush=True)
        except Exception as exc:
            fail += 1
            print(f"  {i}/{len(todo)}  ÉCHEC {job['id']}  {exc}", flush=True)
            time.sleep(2)
    print(f"ok={ok}  échec={fail}  dossier={dest_rel}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
