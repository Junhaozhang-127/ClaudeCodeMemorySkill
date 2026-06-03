"""
workspace_manager.py — Workspace 管理命令

支持：
  - init:   初始化新 workspace
  - list:   列出所有 workspace
  - status: 显示当前 workspace 状态
  - migrate-legacy: 显示迁移指引（不自动迁移）
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = PROJECT_ROOT / "memory"


def init_workspace(workspace_id: str) -> dict:
    """初始化新 workspace。

    Returns:
        {"created": bool, "path": str, "message": str}
    """
    if not workspace_id or workspace_id == "default":
        return {"created": False, "path": str(MEMORY_DIR), "message": "default workspace 无需初始化（已存在）"}

    ws_dir = MEMORY_DIR / "workspaces" / workspace_id
    topics_dir = ws_dir / "topics"
    index_path = ws_dir / "index.json"

    if index_path.exists():
        return {"created": False, "path": str(ws_dir), "message": f"workspace '{workspace_id}' 已存在"}

    topics_dir.mkdir(parents=True, exist_ok=True)
    index_path.write_text("{}", encoding="utf-8")
    (topics_dir / "README.md").write_text(
        f"# {workspace_id} 记忆目录\n\n此目录存储 workspace '{workspace_id}' 的记忆文件。\n",
        encoding="utf-8",
    )
    return {"created": True, "path": str(ws_dir), "message": f"workspace '{workspace_id}' 已创建"}


def list_workspaces() -> list[dict]:
    """列出所有 workspace。"""
    results = []
    # default / legacy
    legacy_idx = MEMORY_DIR / "index.json"
    if legacy_idx.exists():
        data = json.loads(legacy_idx.read_text(encoding="utf-8") or "{}")
        results.append({"id": "default (legacy)", "topics": len(data), "path": str(MEMORY_DIR)})

    ws_root = MEMORY_DIR / "workspaces"
    if ws_root.exists():
        for d in sorted(ws_root.iterdir()):
            if d.is_dir():
                idx = d / "index.json"
                if idx.exists():
                    data = json.loads(idx.read_text(encoding="utf-8") or "{}")
                    results.append({"id": d.name, "topics": len(data), "path": str(d)})
    return results


def workspace_status(workspace_id: str = "") -> dict:
    """显示 workspace 状态。"""
    if not workspace_id or workspace_id == "default":
        idx_path = MEMORY_DIR / "index.json"
        top_dir = MEMORY_DIR / "topics"
        label = "default (legacy)"
    else:
        base = MEMORY_DIR / "workspaces" / workspace_id
        idx_path = base / "index.json"
        top_dir = base / "topics"
        label = workspace_id

    index = {}
    if idx_path.exists():
        try:
            index = json.loads(idx_path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError:
            pass

    md_files = list(top_dir.glob("*.md")) if top_dir.exists() else []
    # exclude README
    md_files = [f for f in md_files if f.name.lower() != "readme.md"]

    return {
        "workspace": label,
        "index_path": str(idx_path),
        "topics_dir": str(top_dir),
        "index_entries": len(index),
        "markdown_files": len(md_files),
        "index_exists": idx_path.exists(),
    }


def migrate_legacy_guide() -> str:
    """显示从旧 memory/ 迁移到 workspace 的手动指引。"""
    return """
=== 迁移指引 ===

旧路径:
  memory/index.json
  memory/topics/

迁移到 workspace（手动操作）：

1. 创建目标 workspace:
   python scripts/workspace_manager.py init --workspace <your-project>

2. 复制记忆文件:
   cp memory/topics/*.md memory/workspaces/<your-project>/topics/

3. 重建索引:
   python scripts/update_index.py --workspace <your-project>

4. 验证:
   python scripts/retrieve_memory.py --workspace <your-project> --query "test"

注意：旧 memory/ 路径不会被自动删除或移动。
确认新 workspace 正常后，可手动移除旧文件。
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Workspace management")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list")

    init_p = sub.add_parser("init")
    init_p.add_argument("--workspace", required=True)

    st_p = sub.add_parser("status")
    st_p.add_argument("--workspace", default="")

    sub.add_parser("migrate-legacy")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "list":
        workspaces = list_workspaces()
        if workspaces:
            for ws in workspaces:
                print(f"  {ws['id']}: {ws['topics']} topics ({ws['path']})")
        else:
            print("暂无 workspace。使用 'init --workspace <name>' 创建。")

    elif args.command == "init":
        result = init_workspace(args.workspace)
        print(result["message"])

    elif args.command == "status":
        status = workspace_status(getattr(args, 'workspace', ''))
        for k, v in status.items():
            print(f"  {k}: {v}")

    elif args.command == "migrate-legacy":
        print(migrate_legacy_guide())


if __name__ == "__main__":
    main()
