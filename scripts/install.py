"""
install.py — 项目安装与初始化

功能：检查环境、创建目录、校验配置、初始化 workspace。
默认不修改用户外部配置。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def check_python() -> dict:
    vi = sys.version_info
    ok = (vi.major, vi.minor) >= (3, 7)
    return {"status": "OK" if ok else "ERROR", "version": f"{vi.major}.{vi.minor}.{vi.micro}"}


def check_directories() -> list[dict]:
    results = []
    for name in ["scripts", "hooks", "memory", "docs", "tests"]:
        p = PROJECT_ROOT / name
        results.append({"name": name, "exists": p.exists(), "status": "OK" if p.exists() else "WARNING"})
    return results


def check_plugin_json() -> dict:
    p = PROJECT_ROOT / "plugin.json"
    if not p.exists():
        return {"status": "ERROR", "message": "plugin.json 缺失"}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        required = ["name", "version", "description"]
        missing = [k for k in required if k not in data]
        if missing:
            return {"status": "WARNING", "message": f"缺少字段: {missing}"}
        return {"status": "OK", "version": data.get("version", "?")}
    except json.JSONDecodeError:
        return {"status": "ERROR", "message": "plugin.json 不是有效 JSON"}


def init_directories(workspace: str = "", dry_run: bool = False) -> list[str]:
    created = []
    dirs = [
        PROJECT_ROOT / "memory" / "topics",
        PROJECT_ROOT / "memory" / "workspaces",
        PROJECT_ROOT / "logs",
    ]
    if workspace and workspace not in ("", "default"):
        dirs.append(PROJECT_ROOT / "memory" / "workspaces" / workspace / "topics")

    for d in dirs:
        if not d.exists():
            created.append(str(d.relative_to(PROJECT_ROOT)))
            if not dry_run:
                d.mkdir(parents=True, exist_ok=True)

    idx = PROJECT_ROOT / "memory" / "index.json"
    if not idx.exists() and not dry_run:
        idx.write_text("{}", encoding="utf-8")
        created.append("memory/index.json")

    return created


def main() -> None:
    parser = argparse.ArgumentParser(description="Install/check Memory Skill")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    results = {
        "python": check_python(),
        "directories": check_directories(),
        "plugin_json": check_plugin_json(),
    }

    if args.dry_run or args.check_only:
        dirs = init_directories(args.workspace, dry_run=True)
        results["would_create"] = dirs

    if args.check_only:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        errors = sum(1 for v in results.values()
                     if isinstance(v, dict) and v.get("status") in ("ERROR", "WARNING"))
        sys.exit(1 if errors > 0 else 0)

    if args.dry_run:
        print("[Dry-run] 将创建以下目录和文件：")
        for d in results["would_create"]:
            print(f"  {d}")
        return

    # 实际初始化
    created = init_directories(args.workspace, dry_run=False)
    print("安装完成。")
    if created:
        print("已创建：")
        for c in created:
            print(f"  {c}")
    print(f"\nPython: {results['python']['version']} ({results['python']['status']})")
    print(f"Plugin: {results['plugin_json'].get('status', '?')} v{results['plugin_json'].get('version', '?')}")
    print("\n下一步：将 docs/settings.template.json 中的 Hook 配置合并到 Claude Code settings.json")


if __name__ == "__main__":
    main()
