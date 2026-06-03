#!/usr/bin/env bash
# ============================================================================
# Claude Code Memory Skill — 用户输入前检索记忆 Hook
#
# 在 Claude Code Hook 事件（PrePrompt / PreUserInput / BeforeConversation）
# 触发时，根据用户输入检索相关历史记忆并输出上下文。
#
# Claude Code 可注入以下环境变量（按实际版本确认）：
#   CLAUDE_USER_INPUT            — 用户当前输入的文本
#   CLAUDE_PROJECT_DIR           — 项目根目录
#
# 用法（手动调试）：
#   bash hooks/pre_prompt.sh "用户当前问题"
# ============================================================================
set -euo pipefail

# ── 项目路径解析 ────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── 参数获取 ────────────────────────────────────────────────
QUERY="${1:-}"

# 支持从 Claude Code 环境变量获取查询
if [ -z "$QUERY" ] && [ -n "${CLAUDE_USER_INPUT:-}" ]; then
    QUERY="$CLAUDE_USER_INPUT"
fi

if [ -z "$QUERY" ]; then
    # 静默退出，不阻塞正常对话
    exit 0
fi

# ── Python 解释器检测 ───────────────────────────────────────
PYTHON_BIN="python3"
if ! command -v "$PYTHON_BIN" &>/dev/null; then
    PYTHON_BIN="python"
fi
if ! command -v "$PYTHON_BIN" &>/dev/null; then
    echo "[Memory Hook] 错误：找不到 Python 解释器" >&2
    exit 1
fi

# ── 执行检索 ────────────────────────────────────────────────
cd "$PROJECT_DIR"

"$PYTHON_BIN" scripts/retrieve_memory.py --query "$QUERY" --top-k 5

echo ""
echo "[Memory Hook] 检索完成。以上上下文将注入 Claude Code。"
