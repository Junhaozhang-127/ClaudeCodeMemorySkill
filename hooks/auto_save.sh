#!/usr/bin/env bash
# ============================================================================
# Claude Code Memory Skill — UserPromptSubmit Hook：轮次自动保存
#
# 每 N 轮对话自动保存一次记忆（默认 N=10）。
# 从 stdin 读取 hook JSON，提取 session_id 和 transcript_path，
# 调用 auto_save_memory.py 检查轮次计数并在达到间隔时保存。
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Python 解释器检测 ────────────────────────────────────────
PYTHON_BIN="python"
if ! command -v "$PYTHON_BIN" &>/dev/null || ! "$PYTHON_BIN" --version &>/dev/null; then
    PYTHON_BIN="python3"
fi
if ! command -v "$PYTHON_BIN" &>/dev/null || ! "$PYTHON_BIN" --version &>/dev/null; then
    echo "[AutoSave Hook] 找不到可用的 Python，跳过自动保存" >&2
    exit 0
fi

# ── 读取 hook stdin JSON ─────────────────────────────────────
HOOK_INPUT="$(cat 2>/dev/null || true)"

if [ -z "$HOOK_INPUT" ]; then
    echo "[AutoSave Hook] stdin 为空，跳过自动保存" >&2
    exit 0
fi

# ── 调用 Python 自动保存脚本 ─────────────────────────────────
cd "$PROJECT_DIR"
echo "$HOOK_INPUT" | "$PYTHON_BIN" scripts/auto_save_memory.py --stdin
