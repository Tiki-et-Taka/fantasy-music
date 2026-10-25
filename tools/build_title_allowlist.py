"""Construit l'allowlist (wiki, titre) a partir des entites Wikidata deja en cache."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

from validate_scoring import get_entities, titles_to_qids, wikipedia_sitelinks  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    spec = json.loads((ROOT / "tools" / "reference_set.json").read_text(encoding="utf-8"))
    titles = [a["wiki"] for a in spec["artists"]] + list(spec["bands"].values())
    qids = titles_to_qids(titles)
    entities = get_entities(sorted(set(qids.values())))

    allow: dict[str, set[str]] = {}
    mapping = []
    for title, qid in qids.items():
        ent = entities.get(qid)
        if not ent:
            continue
        links = wikipedia_sitelinks(ent)
        for code, page in links.items():
            wiki = f"{code}.wikipedia"
            underscored = page.replace(" ", "_")
            allow.setdefault(wiki, set()).add(underscored)
        mapping.append({"title": title, "qid": qid, "sitelinks": len(links)})

    out = {wiki: sorted(pages) for wiki, pages in sorted(allow.items())}
    dest = ROOT / "data" / "title_allowlist.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    n_titles = sum(len(v) for v in out.values())
    print(f"{len(mapping)} entites, {n_titles} titres, {len(out)} editions -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
