"""Generate docs/knowledge-graph.mmd from docs/knowledge-graph.json and check referenced paths exist.

    python docs/generate_graph.py          # write the .mmd
    python docs/generate_graph.py --check  # exit 1 if paths are missing or the .mmd is stale
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parent
ROOT = DOCS.parent
# Generated / downloaded artifacts that legitimately do not exist before the pipeline runs.
OPTIONAL_PATHS = {
    "backend/data/processed/market_prices.parquet",
    "backend/data/processed/crop_production.parquet",
    "backend/models/price_model",
    "backend/models/current.json",
}


def render(graph: dict) -> str:
    ids = {n["id"] for n in graph["nodes"]}
    lines = ["%% GENERATED from knowledge-graph.json by docs/generate_graph.py. Do not edit by hand.", "flowchart LR"]
    for group, title in graph["groups"].items():
        members = [n for n in graph["nodes"] if n["group"] == group]
        if not members:
            continue
        lines.append(f'  subgraph {group}["{title}"]')
        for n in members:
            label = n["label"].replace('"', "'")
            lines.append(f'    {n["id"]}["{label}"]')
        lines.append("  end")
    for src, dst, rel in graph["edges"]:
        if src not in ids or dst not in ids:
            raise SystemExit(f"edge references unknown node: {src} -> {dst}")
        lines.append(f'  {src} -->|"{rel}"| {dst}')
    return "\n".join(lines) + "\n"


def main() -> int:
    graph = json.loads((DOCS / "knowledge-graph.json").read_text(encoding="utf-8"))
    missing = [
        n["path"] for n in graph["nodes"]
        if n.get("path") and n["path"] not in OPTIONAL_PATHS and not (ROOT / n["path"]).exists()
    ]
    text = render(graph)
    out = DOCS / "knowledge-graph.mmd"
    if "--check" in sys.argv:
        stale = not out.exists() or out.read_text(encoding="utf-8") != text
        for m in missing:
            print(f"missing path: {m}")
        if stale:
            print("knowledge-graph.mmd is stale; run python docs/generate_graph.py")
        return 1 if missing or stale else 0
    out.write_text(text, encoding="utf-8")
    for m in missing:
        print(f"warning: missing path {m}")
    print(f"wrote {out.relative_to(ROOT)} ({len(graph['nodes'])} nodes, {len(graph['edges'])} edges)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
