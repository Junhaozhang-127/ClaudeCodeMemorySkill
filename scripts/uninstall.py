"""
uninstall.py — 安全卸载

默认只检查可卸载项，不删除用户记忆数据。
删除 memory/ 需显式 --delete-memory + --yes。
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

SAFE_TO_DELETE = [
    "logs",
    "__pycache__",
    ".pytest_cache",
    "memory/backups",
]


def scan_removable(dry_run: bool = True) -> dict:
    result = {"safe_to_delete": [], "memory_data": [], "warnings": []}
    for pattern in SAFE_TO_DELETE:
        p = PROJECT_ROOT / pattern
        if p.exists():
            result["safe_to_delete"].append(str(p.relative_to(PROJECT_ROOT)))

    # 检查 memory/ 数据
    topics = PROJECT_ROOT / "memory" / "topics"
    if topics.exists():
        md_files = [f.name for f in topics.glob("*.md") if f.name.lower() != "readme.md"]
        if md_files:
            result["memory_data"].extend(md_files)
            result["warnings"].append(f"memory/topics/ 包含 {len(md_files)} 个记忆文件")

    ws_dir = PROJECT_ROOT / "memory" / "workspaces"
    if ws_dir.exists():
        ws_count = len(list(ws_dir.iterdir()))
        if ws_count:
            result["warnings"].append(f"memory/workspaces/ 包含 {ws_count} 个 workspace")

    return result


def do_remove(items: list[str]) -> None:
    for item in items:
        p = PROJECT_ROOT / item
        if p.is_dir():
            shutil.rmtree(str(p), ignore_errors=True)
        elif p.exists():
            p.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(description="Safe uninstall")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--delete-memory", action="store_true")
    parser.add_argument("--yes", action="store_true")
    args = parser.parse_args()

    do_apply = args.apply and not args.dry_run

    scan = scan_removable(dry_run=not do_apply)

    if do_apply and args.delete_memory:
        if not args.yes:
            print("警告：--delete-memory 将永久删除所有记忆数据！")
            print("请添加 --yes 确认，或使用 --dry-run 预览。")
            return
        scan["safe_to_delete"].append("memory/topics")
        scan["safe_to_delete"].append("memory/workspaces")
        scan["safe_to_delete"].append("memory/index.json")

    if do_apply:
        print("删除以下内容：")
        for item in scan["safe_to_delete"]:
            print(f"  {item}")
        do_remove(scan["safe_to_delete"])
        print("卸载完成。")
    else:
        print("[Dry-run] 将删除以下安全项：")
        for item in scan["safe_to_delete"]:
            print(f"  {item}")
        if scan["memory_data"]:
            print(f"\n记忆文件（受保护，不会被删除）：{len(scan['memory_data'])} 个")
        for w in scan["warnings"]:
            print(f"  {w}")
        print("\n使用 --delete-memory --yes --apply 可删除记忆数据。")


if __name__ == "__main__":
    main()
