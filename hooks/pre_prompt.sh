#!/usr/bin/env bash
# ============================================================================
# Claude Code Memory Skill — UserPromptSubmit Hook：检索相关历史记忆
#
# Claude Code UserPromptSubmit hook 通过 stdin 传入 JSON：
#   {"session_id":"...", "transcript_path":"...", "prompt":"用户输入", ...}
#
# 本脚本从中提取用户输入文本，检索相关历史记忆并输出为附加上下文。
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Python 解释器检测（验证实际可执行性）────────────────────
PYTHON_BIN=""
for candidate in "python3" "python"; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import sys; print(sys.executable)" >/dev/null 2>&1; then
        PYTHON_BIN="$candidate"
        break
    fi
done
if [ -z "$PYTHON_BIN" ]; then
    echo "[Memory Hook] 找不到可用的 Python 解释器，跳过检索" >&2
    exit 0
fi

# ── 读取 hook stdin JSON ─────────────────────────────────────
HOOK_INPUT="$(cat 2>/dev/null || true)"

QUERY=""

if [ -n "$HOOK_INPUT" ]; then
    # 从 stdin JSON 提取 prompt 字段
    QUERY=$(echo "$HOOK_INPUT" | "$PYTHON_BIN" -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('prompt', ''))
except Exception:
    pass
" 2>/dev/null || true)
fi

# 回退：环境变量
if [ -z "$QUERY" ] && [ -n "${CLAUDE_USER_INPUT:-}" ]; then
    QUERY="$CLAUDE_USER_INPUT"
fi

# 回退：命令行参数
if [ -z "$QUERY" ] && [ -n "${1:-}" ]; then
    QUERY="$1"
fi

if [ -z "$QUERY" ]; then
    exit 0
fi

# ── 执行检索 ─────────────────────────────────────────────────
cd "$PROJECT_DIR"

"$PYTHON_BIN" "$PROJECT_DIR/scripts/retrieve_memory.py" --query "$QUERY" --top-k 5

echo ""
echo "[Memory Hook] 检索完成。以上上下文将注入 Claude Code。"
