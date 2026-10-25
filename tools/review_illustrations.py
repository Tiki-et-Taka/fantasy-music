"""Revue locale des plaques : grille, clic = raté, JSON persisté.

  python tools/review_illustrations.py
"""

from __future__ import annotations

import json
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REJECTS = ROOT / "data" / "census" / "illustration_rejects.json"
DEST = ROOT / "out" / "illustrations"
PORT = 8765

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        sys.stdout.write("%s - %s\n" % (self.address_string(), fmt % args))
        sys.stdout.flush()

    def _json(self, payload, code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.path = "/prototypes/review-illustrations.html"
            return super().do_GET()
        if path == "/api/existing":
            DEST.mkdir(parents=True, exist_ok=True)
            names = {
                p.stem: int(p.stat().st_mtime)
                for p in DEST.glob("*.png") if p.is_file()
            }
            return self._json(names)
        return super().do_GET()

    def end_headers(self) -> None:
        path = urlparse(self.path).path
        if path.startswith("/out/illustrations/") or path.startswith("/data/census/") or path.startswith("/prototypes/") or path.startswith("/docs/"):
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
        super().end_headers()

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/rejects":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_error(400, "JSON invalide")
            return
        if not isinstance(data, dict):
            self.send_error(400, "objet attendu")
            return
        REJECTS.parent.mkdir(parents=True, exist_ok=True)
        current = {}
        if REJECTS.exists():
            try:
                current = json.loads(REJECTS.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                current = {}
            if not isinstance(current, dict):
                current = {}
        current.update(data)
        current = {k: v for k, v in current.items() if v in ("ok", "reject")}
        REJECTS.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
        body = json.dumps({"ok": True, "n": len(current)}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> int:
    REJECTS.parent.mkdir(parents=True, exist_ok=True)
    if not REJECTS.exists():
        REJECTS.write_text("{}\n", encoding="utf-8")
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    url = f"http://127.0.0.1:{PORT}/"
    print(f"Revue des plaques → {url}")
    print("Clic sur une image = raté. Reclic = bon. Fermer le terminal pour quitter.")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstop")
    return 0


if __name__ == "__main__":
    sys.exit(main())
