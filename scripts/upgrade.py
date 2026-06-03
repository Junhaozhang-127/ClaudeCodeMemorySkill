"""
upgrade.py — 升级与迁移

检查旧版本结构，提供迁移建议。默认 dry-run，需 --apply 才执行。
"""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def check_legacy() -> dict:
    idx = PROJECT_ROOT / "memory" / "index.json"
    topics = PROJECT_ROOT / "memory" / "topics"
    has_legacy = idx.exists() and topics.exists()
    topics_count = 0
    if topics.exists():
        md_files = [f for f in topics.glob("*.md") if f.name.lower() != "readme.md"]
        topics_count = len(md_files)
    return {"has_legacy": has_legacy, "topics_count": topics_count, "index_path": str(idx)}


def check_workspaces() -> list[dict]:
    ws_dir = PROJECT_ROOT / "memory" / "workspaces"
    if not ws_dir.exists():
        return []
    result = []
    for d in sorted(ws_dir.iterdir()):
        if d.is_dir():
            idx = d / "index.json"
            topics = d / "topics"
            entries = 0
            if idx.exists():
                try:
                    entries = len(json.loads(idx.read_text(encoding="utf-8") or "{}"))
                except Exception:
                    pass
            result.append({"name": d.name, "index_entries": entries, "path": str(d)})
    return result


def migrate_legacy_to_workspace(workspace: str, apply: bool = False) -> dict:
    src_idx = PROJECT_ROOT / "memory" / "index.json"
    src_topics = PROJECT_ROOT / "memory" / "topics"
    dst_base = PROJECT_ROOT / "memory" / "workspaces" / workspace
    dst_idx = dst_base / "index.json"
    dst_topics = dst_base / "topics"

    if not src_idx.exists():
        return {"status": "SKIP", "message": "无 legacy 数据可迁移"}

    plan = {
        "action": "migrate_legacy",
        "workspace": workspace,
        "source": str(src_idx),
        "destination": str(dst_idx),
        "files_to_copy": [],
    }

    for f in src_topics.glob("*.md"):
        if f.name.lower() != "readme.md":
            plan["files_to_copy"].append(f.name)

    if not apply:
        return plan

    # 执行迁移
    dst_topics.mkdir(parents=True, exist_ok=True)
    for fname in plan["files_to_copy"]:
        src = src_topics / fname
        dst = dst_topics / fname
        shutil.copy2(str(src), str(dst))

    # 备份原 index
    bak_dir = PROJECT_ROOT / "memory" / "backups"
    bak_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(str(src_idx), str(bak_dir / f"index_pre_migrate_{ts}.json"))

    # 复制 index 到新 workspace
    index_data = json.loads(src_idx.read_text(encoding="utf-8") or "{}")
    for key, rec in index_data.items():
        old_file = rec.get("file", "")
        fname = Path(old_file).name
        rec["file"] = str((dst_topics / fname).relative_to(PROJECT_ROOT))
    dst_idx.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"status": "OK", "message": f"已迁移 {len(plan['files_to_copy'])} 个文件到 workspace '{workspace}'"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Upgrade/migration tool")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--migrate-to", default="", help="迁移 legacy → workspace")
    args = parser.parse_args()

    legacy = check_legacy()
    workspaces = check_workspaces()

    print("=== 升级检查 ===")
    print(f"Legacy memory: {'存在' if legacy['has_legacy'] else '无'} ({legacy['topics_count']} topics)")
    print(f"Workspaces: {len(workspaces)}")
    for ws in workspaces:
        print(f"  - {ws['name']}: {ws['index_entries']} entries")

    if args.migrate_to:
        apply = args.apply and not args.dry_run
        result = migrate_legacy_to_workspace(args.migrate_to, apply=apply)
        if apply:
            print(f"\n迁移结果: {result.get('message')}")
        else:
            print(f"\n[Dry-run] 将迁移 {len(result.get('files_to_copy', []))} 个文件到 workspace '{args.migrate_to}'")
            print("添加 --apply 执行迁移。原文件不会被删除。")
    else:
        print("\n建议：")
        if legacy["has_legacy"] and legacy["topics_count"] > 0 and not workspaces:
            print("  使用 --migrate-to <name> 将 legacy 数据迁移到 workspace")
        print("  使用 --apply 执行迁移（原数据保留备份）")


if __name__ == "__main__":
    main()
