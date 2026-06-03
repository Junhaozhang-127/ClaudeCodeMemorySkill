"""
install.py — 项目安装与初始化

功能：检查环境、创建目录、校验配置、初始化 workspace。
首次运行时提供交互式路径设置向导。
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


def init_directories(memory_root: str = "memory", workspace: str = "", dry_run: bool = False) -> list[str]:
    """初始化记忆目录结构。支持自定义 memory_root 路径。"""
    created = []
    root = Path(memory_root)
    if not root.is_absolute():
        root = PROJECT_ROOT / root

    dirs = [
        root / "topics",
        root / "workspaces",
    ]
    logs_dir = PROJECT_ROOT / "logs"
    dirs.append(logs_dir)

    if workspace and workspace not in ("", "default"):
        dirs.append(root / "workspaces" / workspace / "topics")

    for d in dirs:
        if not d.exists():
            created.append(str(d))
            if not dry_run:
                d.mkdir(parents=True, exist_ok=True)

    idx = root / "index.json"
    if not idx.exists() and not dry_run:
        idx.write_text("{}", encoding="utf-8")
        created.append(str(idx))

    return created


# ═══════════════════════════════════════════════════════════════
# 首次运行设置向导
# ═══════════════════════════════════════════════════════════════

def setup_wizard() -> str:
    """交互式设置记忆存储路径。返回用户选择或确认的路径。"""
    print("=" * 60)
    print("  Claude Code Memory Skill — 首次设置")
    print("=" * 60)
    print()
    print("  记忆库用于保存对话摘要、关键决策和待办事项。")
    print("  所有记忆以 Markdown 文件形式存储在本地，不会上传。")
    print()
    default_path = str(PROJECT_ROOT / "memory")
    print(f"  默认存储路径: {default_path}")
    print()
    print("  你可以:")
    print("    1. 直接按 Enter 使用默认路径")
    print("    2. 输入自定义路径（绝对路径），例如:")
    print("       D:\\MyMemories")
    print("       /home/user/claude-memories")
    print("       ~/Documents/memories")
    print()

    while True:
        try:
            choice = input("  请输入记忆存储路径（直接回车使用默认）: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  已取消。使用默认路径。")
            choice = ""

        if not choice:
            choice = default_path

        # 展开 ~ 和相对路径
        path = Path(choice).expanduser()
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path = path.resolve()

        # 检查是否可创建
        try:
            path.mkdir(parents=True, exist_ok=True)
            # 写入测试
            test_file = path / ".write_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
        except (OSError, PermissionError) as e:
            print(f"\n  ❌ 无法写入该路径: {e}")
            print("  请尝试另一个路径。\n")
            continue

        # 确认
        print(f"\n  记忆将存储在: {path}")
        print(f"  目录结构: {path}/topics/  (记忆文件)")
        print(f"              {path}/index.json (索引)")
        print()

        if path == Path(default_path):
            print("  ✅ 使用默认路径。")
            return str(path)

        try:
            confirm = input("  确认使用此路径？[Y/n] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            confirm = "y"

        if confirm in ("", "y", "yes"):
            return str(path)
        print("  请重新输入路径。\n")


def run_setup_and_save(memory_path: str) -> None:
    """执行设置并保存 config.json。"""
    from config import save_config_file, MemoryConfig

    cfg = MemoryConfig(project_root=PROJECT_ROOT, memory_root=memory_path)
    save_config_file(cfg)

    # 初始化目录
    created = init_directories(memory_root=memory_path, dry_run=False)
    if created:
        print("  已创建：")
        for c in created:
            print(f"    {c}")

    print(f"\n  配置已保存到: {cfg.config_file_path}")
    print("  下次使用时将自动读取此配置。")
    print("  如需修改，可编辑 config.json 或设置环境变量 CLAUDE_MEMORY_DIR。")


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Install/check Memory Skill")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--interactive", action="store_true", help="交互式设置记忆存储路径")
    parser.add_argument("--path", default="", help="直接指定记忆存储路径（非交互）")
    args = parser.parse_args()

    # ── 交互式设置 ──
    if args.interactive:
        path = setup_wizard()
        run_setup_and_save(path)
        return

    # ── 直接指定路径 ──
    if args.path:
        from config import save_config_file, MemoryConfig
        cfg = MemoryConfig(project_root=PROJECT_ROOT, memory_root=args.path)
        save_config_file(cfg)
        init_directories(memory_root=args.path, dry_run=False)
        print(f"记忆路径已设置为: {args.path}")
        return

    # ── 检查模式 ──
    results = {
        "python": check_python(),
        "directories": check_directories(),
        "plugin_json": check_plugin_json(),
    }

    # 首次运行检测
    from config import is_first_run
    if is_first_run(PROJECT_ROOT):
        results["first_run"] = True
        results["hint"] = "运行 python scripts/install.py --interactive 进行首次设置"

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
        for d in results.get("would_create", []):
            print(f"  {d}")
        if results.get("first_run"):
            print("\n⚠ 检测到首次运行。运行 --interactive 设置记忆路径。")
        return

    # ── 默认初始化 ──
    if results.get("first_run"):
        print("⚠ 检测到首次运行。")
        print()
        path = setup_wizard()
        run_setup_and_save(path)
        return

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
