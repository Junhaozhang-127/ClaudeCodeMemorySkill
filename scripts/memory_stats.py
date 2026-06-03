"""
memory_stats.py — 记忆库统计

统计 topics、index entries、backups、archive、文件大小等。
支持 --workspace / --all-workspaces / --json。
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def stats_for_workspace(workspace: str = "") -> dict:
    from memory_core import load_index, _resolve_paths
    _, topics_dir, index_file = _resolve_paths(workspace)

    index = load_index(workspace)
    topics = [f for f in topics_dir.glob("*.md") if f.name.lower() != "readme.md"] if topics_dir.exists() else []

    total_size = sum(f.stat().st_size for f in topics)
    keywords_all: list[str] = []
    for r in index.values():
        keywords_all.extend(r.get("keywords", []))

    # top keywords
    from collections import Counter
    top_kw = Counter(keywords_all).most_common(10)

    latest = ""
    for r in index.values():
        u = r.get("updated_at", "")
        if u > latest:
            latest = u

    backup_dir = index_file.parent / "backups"
    backups = list(backup_dir.glob("index_*.json")) if backup_dir.exists() else []

    archive_dir = index_file.parent / "archive"
    archives = list(archive_dir.rglob("*.md")) if archive_dir.exists() else []

    return {
        "workspace": workspace or "default (legacy)",
        "index_entries": len(index),
        "topics_files": len(topics),
        "total_size_bytes": total_size,
        "backups_count": len(backups),
        "archived_count": len(archives),
        "latest_update": latest,
        "top_keywords": [{"word": w, "count": c} for w, c in top_kw],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Memory statistics")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--all-workspaces", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.all_workspaces:
        ws_dir = PROJECT_ROOT / "memory" / "workspaces"
        results = {"legacy": stats_for_workspace("")}
        if ws_dir.exists():
            for d in sorted(ws_dir.iterdir()):
                if d.is_dir():
                    results[d.name] = stats_for_workspace(d.name)
    else:
        results = stats_for_workspace(args.workspace)

    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        if isinstance(results, dict) and "workspace" in results:
            _print_one(results)
        else:
            for name, st in results.items():
                print(f"\n--- {name} ---")
                _print_one(st)


def _print_one(st: dict) -> None:
    print(f"Workspace: {st['workspace']}")
    print(f"  Index entries:  {st['index_entries']}")
    print(f"  Topics files:   {st['topics_files']}")
    print(f"  Total size:     {st['total_size_bytes']:,} bytes")
    print(f"  Backups:        {st['backups_count']}")
    print(f"  Archived:       {st['archived_count']}")
    print(f"  Latest update:  {st['latest_update'] or 'N/A'}")
    if st["top_keywords"]:
        print(f"  Top keywords:   {', '.join(f'{w}({c})' for w, c in st['top_keywords'][:5])}")


if __name__ == "__main__":
    main()
