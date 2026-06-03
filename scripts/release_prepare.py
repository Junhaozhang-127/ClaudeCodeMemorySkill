"""
release_prepare.py — 发布前清理

检查并清理缓存、临时文件、测试遗留。
默认 dry-run，--apply 才执行。不删除用户记忆数据。
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 可安全删除的目录和文件模式
CLEANABLE_DIRS = ["__pycache__", ".pytest_cache", "memory/backups"]
CLEANABLE_PATTERNS = ["*.pyc", "*.pyo", "*.lock", "index.json.tmp"]
# 测试生成的 Markdown 前缀
TEST_PREFIXES = ("test_", "TEST_", "Phase", "P31_", "P41_", "CLI_", "PS_", "Batch_", "WS_", "EnvWorkspace", "CustomDir", "Phase2_Codex", "Phase3_Codex", "Phase4_Legacy", "Codex_")


def scan_cleanable() -> dict:
    plan = {"dirs_to_remove": [], "files_to_remove": [], "test_md_files": []}

    # 缓存目录
    for d in CLEANABLE_DIRS:
        p = PROJECT_ROOT / d
        if p.exists():
            plan["dirs_to_remove"].append(str(p.relative_to(PROJECT_ROOT)))

    # 文件模式（递归扫描有限目录）
    for pattern in CLEANABLE_PATTERNS:
        for p in PROJECT_ROOT.rglob(pattern):
            if "__pycache__" not in str(p) and ".pytest_cache" not in str(p):
                plan["files_to_remove"].append(str(p.relative_to(PROJECT_ROOT)))

    # 测试生成的 Markdown（仅在 memory/topics/ 下）
    topics = PROJECT_ROOT / "memory" / "topics"
    if topics.exists():
        for f in topics.glob("*.md"):
            if f.name.lower() == "readme.md":
                continue
            if any(f.name.startswith(pre) for pre in TEST_PREFIXES):
                plan["test_md_files"].append(str(f.relative_to(PROJECT_ROOT)))

    # workspace 下的测试目录
    ws_dir = PROJECT_ROOT / "memory" / "workspaces"
    if ws_dir.exists():
        for d in ws_dir.iterdir():
            if d.is_dir() and any(d.name.startswith(p) for p in ("P4", "P5", "Phase", "Acceptance", "test_")):
                plan["dirs_to_remove"].append(str(d.relative_to(PROJECT_ROOT)))

    return plan


def main() -> None:
    parser = argparse.ArgumentParser(description="Release cleanup")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--keep-logs", action="store_true")
    parser.add_argument("--keep-backups", action="store_true")
    parser.add_argument("--keep-samples", action="store_true")
    args = parser.parse_args()

    # 默认 dry-run（无 --apply 且无 --dry-run 显式传入时也走 dry-run）
    do_apply = args.apply

    plan = scan_cleanable()

    if not args.keep_backups:
        pass  # backups are already in CLEANABLE_DIRS
    if args.keep_logs and "logs" in plan["dirs_to_remove"]:
        plan["dirs_to_remove"].remove("logs")
    if args.keep_samples:
        plan["test_md_files"] = []

    total = len(plan["dirs_to_remove"]) + len(plan["files_to_remove"]) + len(plan["test_md_files"])

    if do_apply:
        for d in plan["dirs_to_remove"]:
            p = PROJECT_ROOT / d
            if p.exists():
                shutil.rmtree(str(p), ignore_errors=True)
        for f in plan["files_to_remove"]:
            p = PROJECT_ROOT / f
            if p.exists():
                p.unlink()
        for f in plan["test_md_files"]:
            p = PROJECT_ROOT / f
            if p.exists():
                p.unlink()
        print(f"清理完成：{total} 项已删除。")
    else:
        print(f"[Dry-run] 将清理 {total} 项：")
        for d in plan["dirs_to_remove"]:
            print(f"  [目录] {d}")
        for f in plan["files_to_remove"]:
            print(f"  [文件] {f}")
        for f in plan["test_md_files"]:
            print(f"  [测试] {f}")
        print("\n添加 --apply 执行清理。")


if __name__ == "__main__":
    main()
