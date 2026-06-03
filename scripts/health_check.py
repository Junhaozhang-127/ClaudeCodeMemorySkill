"""
health_check.py — 系统健康检查

检查项目结构、Python 环境、memory 完整性、日志、安全性。
支持 --json / --workspace / --all-workspaces / --fix。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _ok(msg="") -> dict:
    return {"status": "OK", "message": msg}


def _warn(msg) -> dict:
    return {"status": "WARNING", "message": str(msg)}


def _err(msg) -> dict:
    return {"status": "ERROR", "message": str(msg)}


def check_project_structure() -> list[dict]:
    results = []
    for name in ["scripts", "hooks", "memory", "docs", "tests", "plugin.json"]:
        p = PROJECT_ROOT / name
        results.append({"item": name, "exists": p.exists(), "status": "OK" if p.exists() else "WARNING"})
    return results


def check_python_env() -> dict:
    vi = sys.version_info
    py_ok = (vi.major, vi.minor) >= (3, 7)
    jieba_ok = False
    try:
        import jieba  # noqa: F401
        jieba_ok = True
    except ImportError:
        pass
    return {
        "python_version": f"{vi.major}.{vi.minor}.{vi.micro}",
        "python_ok": py_ok,
        "jieba_installed": jieba_ok,
        "status": "OK" if py_ok else "ERROR",
    }


def check_memory(workspace: str = "") -> dict:
    from memory_core import load_index, _resolve_paths

    _, topics_dir, index_file = _resolve_paths(workspace)
    results = {
        "workspace": workspace or "default (legacy)",
        "index_path": str(index_file),
        "index_exists": index_file.exists(),
        "index_valid": False,
        "index_entries": 0,
        "topics_count": 0,
        "status": "OK",
    }

    if index_file.exists():
        try:
            data = json.loads(index_file.read_text(encoding="utf-8") or "{}")
            results["index_valid"] = True
            results["index_entries"] = len(data)
        except json.JSONDecodeError:
            results["status"] = "WARNING"
            results["index_valid"] = False

    if topics_dir.exists():
        md_files = [f for f in topics_dir.glob("*.md") if f.name.lower() != "readme.md"]
        results["topics_count"] = len(md_files)
        # 检查异常大文件 (>500KB)
        large = [f.name for f in md_files if f.stat().st_size > 512_000]
        if large:
            results["large_files"] = large
            results["status"] = "WARNING"

    # 检查锁残留
    lock = index_file.with_suffix(index_file.suffix + ".lock")
    if lock.exists():
        results["stale_lock"] = True
        results["status"] = "WARNING"

    # 检查备份
    backup_dir = index_file.parent / "backups"
    if backup_dir.exists():
        results["backups_count"] = len(list(backup_dir.glob("index_*.json")))

    # 检查 archive
    archive_dir = index_file.parent / "archive"
    if archive_dir.exists():
        results["archive_count"] = len(list(archive_dir.rglob("*.md")))

    return results


def check_security(workspace: str = "") -> list[dict]:
    from memory_core import load_index, _resolve_paths
    warnings = []
    index = load_index(workspace)

    # 检查越界路径
    for key, rec in index.items():
        f = rec.get("file", "")
        if ".." in f or f.startswith("/"):
            warnings.append(_warn(f"可疑路径: {key} -> {f}"))

    # 检查敏感词（启发式）
    sensitive_patterns = ["api_key", "password", "token", "secret", "sk-", "Bearer"]
    for key, rec in index.items():
        summary = str(rec.get("summary", "")).lower()
        for pat in sensitive_patterns:
            if pat in summary:
                warnings.append(_warn(f"疑似敏感信息: {key} 摘要含 '{pat}'"))
                break

    return warnings


def check_logs() -> dict:
    log_dir = PROJECT_ROOT / "logs"
    if not log_dir.exists():
        return {"status": "OK", "message": "logs/ 目录不存在（尚未产生日志）"}
    log_files = list(log_dir.glob("*.log"))
    total_size = sum(f.stat().st_size for f in log_files)
    return {
        "status": "OK",
        "log_files": len(log_files),
        "total_size_bytes": total_size,
    }


def do_fix(results: dict) -> list[str]:
    fixed = []
    if results.get("stale_lock"):
        lock = Path(results["index_path"]).with_suffix(".json.lock")
        if lock.exists():
            lock.unlink()
            fixed.append(f"已删除残留锁: {lock}")
    return fixed


def main() -> None:
    parser = argparse.ArgumentParser(description="Health check")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--all-workspaces", action="store_true")
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()

    report = {
        "project_structure": check_project_structure(),
        "python_env": check_python_env(),
        "logs": check_logs(),
    }

    if args.all_workspaces:
        ws_dir = PROJECT_ROOT / "memory" / "workspaces"
        workspaces = ["(legacy)"]
        if ws_dir.exists():
            workspaces.extend(d.name for d in sorted(ws_dir.iterdir()) if d.is_dir())
        report["workspaces"] = {}
        for ws in workspaces:
            w = "" if ws == "(legacy)" else ws
            report["workspaces"][ws] = check_memory(w)
    else:
        report["memory"] = check_memory(args.workspace)
        report["security"] = check_security(args.workspace)

    if args.fix:
        mem = report.get("memory", {})
        report["fixed"] = do_fix(mem)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_text(report)

    # 退出码
    has_error = any(
        isinstance(v, dict) and v.get("status") == "ERROR"
        for v in report.values() if isinstance(v, dict)
    )
    sys.exit(1 if has_error else 0)


def _print_text(report: dict) -> None:
    print("=== 项目结构 ===")
    for item in report.get("project_structure", []):
        print(f"  [{item['status']}] {item['item']}")

    py = report.get("python_env", {})
    print(f"\n=== Python ===\n  {py.get('python_version')} (jieba: {py.get('jieba_installed')}) [{py.get('status')}]")

    mem = report.get("memory", {})
    if mem:
        ws = mem.get("workspace", "?")
        print(f"\n=== Memory ({ws}) ===\n  Index: {mem.get('index_entries')} entries (valid: {mem.get('index_valid')})\n  Topics: {mem.get('topics_count')} files\n  Status: {mem.get('status')}")
        if mem.get("stale_lock"):
            print("  ⚠ 残留锁文件")

    sec = report.get("security", [])
    if sec:
        print(f"\n=== 安全 ===\n  发现 {len(sec)} 个 warning")

    logs = report.get("logs", {})
    print(f"\n=== 日志 ===\n  {logs.get('status')}: {logs.get('log_files', 0)} files, {logs.get('total_size_bytes', 0)} bytes")


if __name__ == "__main__":
    main()
