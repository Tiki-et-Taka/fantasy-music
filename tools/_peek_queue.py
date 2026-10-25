import json
import urllib.request

item = json.loads(urllib.request.urlopen(
    "http://127.0.0.1:9090/api/v1/queue/default/i/106", timeout=30
).read())
print("top keys", item.keys())
session = item.get("session") or {}
print("session keys", session.keys())
results = session.get("results") or {}
print("results keys", list(results)[:30])
for k, v in results.items():
    s = json.dumps(v)[:250]
    print(" RESULT", k, s)

# collect all image_names
found = []

def walk(obj, path=""):
    if isinstance(obj, dict):
        if "image_name" in obj:
            found.append((path, obj["image_name"]))
        for a, b in obj.items():
            walk(b, path + "." + a)
    elif isinstance(obj, list):
        for i, b in enumerate(obj):
            walk(b, f"{path}[{i}]")

walk(item)
print("image_names:")
for p, n in found:
    print(" ", p, n)
