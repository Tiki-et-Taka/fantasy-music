import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "out" / "illustrations"
jobs = json.loads((ROOT / "data" / "census" / "illustration_jobs.json").read_text(encoding="utf-8"))
LOOKDEV_WANT = (
    ("voix", "encre", "f"),
    ("voix", "serigraphie", "m"),
    ("batterie", None, "m"),
    ("vents", "contrejour", None),
    ("guitare", None, "f"),
    ("machines", None, None),
)
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

rows = []
for item_id in range(90, 107):
    try:
        item = json.loads(urllib.request.urlopen(
            f"http://127.0.0.1:9090/api/v1/queue/default/i/{item_id}", timeout=30
        ).read())
    except Exception:
        continue
    results = (item.get("session") or {}).get("results") or {}
    out_name = ref = None
    for val in results.values():
        if not isinstance(val, dict):
            continue
        if val.get("type") == "image_output":
            out_name = (val.get("image") or {}).get("image_name")
        ipa = val.get("ip_adapter") or {}
        if isinstance(ipa, dict) and (ipa.get("image") or {}).get("image_name"):
            ref = ipa["image"]["image_name"]
    print(item_id, item.get("status"), "out", out_name, "ref", (ref or "")[:12])
    if out_name:
        rows.append((item_id, out_name, ref))

# last 6 completed with outputs, in order
last = rows[-6:]
print("mapping last 6 to lookdev")
for job, (item_id, out_name, ref) in zip(picked, last):
    url = f"http://127.0.0.1:9090/api/v1/images/i/{out_name}/full"
    with urllib.request.urlopen(url, timeout=60) as resp:
        blob = resp.read()
    dest = DEST / f"{job['id']}.png"
    dest.write_bytes(blob)
    print(job["id"], "<-", item_id, len(blob), "ref", (ref or "")[:20])
