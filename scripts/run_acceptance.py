"""
run_acceptance.py — 发布前验收测试套件

依次运行：单元测试 → CLI 检查 → health_check → 配置校验 → 安装检查 → 清理预览。
使用临时 workspace，不污染真实 memory。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
_PY = sys.executable


def _run(cmd: list[str], timeout: int = 30) -> dict:
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            cwd=str(PROJECT_ROOT), env=env, timeout=timeout,
        )
        return {"name": " ".join(cmd[:3]), "exit": proc.returncode,
                "stdout": proc.stdout[:500], "stderr": proc.stderr[:200]}
    except Exception as e:
        return {"name": " ".join(cmd[:3]), "exit": -1, "error": str(e)}


def run_quick() -> list[dict]:
    results = []

    # 1. 单元测试
    r = _run([_PY, "tests/test_memory_skill.py"])
    results.append({**r, "check": "unit_tests"})

    # 2. 版本检查
    r = _run([_PY, "scripts/version.py", "--json"])
    results.append({**r, "check": "version"})

    # 3. 安装检查
    r = _run([_PY, "scripts/install.py", "--check-only"])
    results.append({**r, "check": "install_check"})

    # 4. 健康检查
    r = _run([_PY, "scripts/health_check.py", "--json"])
    results.append({**r, "check": "health_check"})

    # 5. plugin.json 校验
    r = _run([_PY, "-c", "import json;d=json.load(open('plugin.json','r',encoding='utf-8'));print('OK:',d['name'],d['version'])"])
    results.append({**r, "check": "plugin_json"})

    # 6. 配置校验
    r = _run([_PY, "-c", "from scripts.config import MemoryConfig;c=MemoryConfig();print('OK:',c.memory_dir)"])
    results.append({**r, "check": "config"})

    # 7. 清理预览
    r = _run([_PY, "scripts/release_prepare.py", "--dry-run"])
    results.append({**r, "check": "release_prepare"})

    return results


def run_full(workspace: str = "AcceptanceTest") -> list[dict]:
    results = run_quick()

    # 使用临时 workspace 做完整流程
    ws = workspace

    # 初始化 workspace
    r = _run([_PY, "scripts/workspace_manager.py", "init", "--workspace", ws])
    results.append({**r, "check": "workspace_init"})

    # 保存记忆
    r = _run([_PY, "scripts/summarize_session.py", "--workspace", ws,
              "--topic", "验收测试", "--text", "接受测试：验证完整流程。"])
    results.append({**r, "check": "save_to_workspace"})

    # 检索
    r = _run([_PY, "scripts/retrieve_memory.py", "--workspace", ws,
              "--query", "验收测试 完整流程", "--json"])
    results.append({**r, "check": "retrieve_from_workspace"})

    # 统计
    r = _run([_PY, "scripts/memory_stats.py", "--workspace", ws, "--json"])
    results.append({**r, "check": "memory_stats"})

    # 重建
    r = _run([_PY, "scripts/update_index.py", "--workspace", ws])
    results.append({**r, "check": "rebuild_index"})

    # 清理
    ws_path = PROJECT_ROOT / "memory" / "workspaces" / ws
    if ws_path.exists():
        import shutil
        shutil.rmtree(str(ws_path), ignore_errors=True)

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Acceptance test suite")
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--workspace", default="AcceptanceTest")
    args = parser.parse_args()

    if args.full:
        results = run_full(args.workspace)
    else:
        results = run_quick()

    passed = sum(1 for r in results if r.get("exit") == 0)
    failed = sum(1 for r in results if r.get("exit") != 0)

    if args.json:
        print(json.dumps({
            "total": len(results), "passed": passed, "failed": failed,
            "results": results,
        }, ensure_ascii=False, indent=2))
    else:
        for r in results:
            icon = "OK" if r["exit"] == 0 else "FAIL"
            print(f"[{icon}] {r['check']}")
        print(f"\n{passed}/{len(results)} 通过, {failed} 失败")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
