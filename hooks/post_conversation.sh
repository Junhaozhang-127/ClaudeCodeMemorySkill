#!/usr/bin/env bash
# ============================================================================
# Claude Code Memory Skill — 会话后写入记忆 Hook
#
# 在 Claude Code Hook 事件（PostConversation / Stop / SessionEnd）触发时，
# 将对话内容保存为结构化 Markdown 记忆并更新索引。
#
# Claude Code 可注入以下环境变量（按实际版本确认）：
#   CLAUDE_CONVERSATION_TITLE    — 会话标题/主题
#   CLAUDE_CONVERSATION_CONTENT  — 会话文本内容
#   CLAUDE_PROJECT_DIR           — 项目根目录
#
# 用法（手动调试）：
#   bash hooks/post_conversation.sh "主题" "/path/to/conversation.txt"
#   bash hooks/post_conversation.sh "主题" --text "对话内容..."
# ============================================================================
set -euo pipefail

# ── 项目路径解析 ────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── 参数获取 ────────────────────────────────────────────────
TOPIC="${1:-}"
INPUT_MODE="file"
CONVERSATION_FILE="${2:-}"

# 支持从 Claude Code 环境变量获取内容
if [ -z "$TOPIC" ] && [ -n "${CLAUDE_CONVERSATION_TITLE:-}" ]; then
    TOPIC="$CLAUDE_CONVERSATION_TITLE"
fi

if [ "$INPUT_MODE" = "file" ] && [ "$CONVERSATION_FILE" = "--text" ]; then
    INPUT_MODE="text"
    CONVERSATION_TEXT="${3:-}"
fi

# 兜底
if [ -z "$TOPIC" ]; then
    TOPIC="未命名对话 $(date '+%Y-%m-%d %H:%M')"
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

# ── 执行保存 ────────────────────────────────────────────────
cd "$PROJECT_DIR"

if [ "$INPUT_MODE" = "text" ] && [ -n "${CONVERSATION_TEXT:-}" ]; then
    "$PYTHON_BIN" scripts/summarize_session.py \
        --topic "$TOPIC" \
        --text "$CONVERSATION_TEXT"
elif [ -n "${CLAUDE_CONVERSATION_CONTENT:-}" ]; then
    # 通过环境变量传递内容
    echo "$CLAUDE_CONVERSATION_CONTENT" > /tmp/claude_memory_hook_$$.txt
    "$PYTHON_BIN" scripts/summarize_session.py \
        --topic "$TOPIC" \
        --file "/tmp/claude_memory_hook_$$.txt"
    rm -f "/tmp/claude_memory_hook_$$.txt"
elif [ -n "${CONVERSATION_FILE:-}" ] && [ -f "$CONVERSATION_FILE" ]; then
    "$PYTHON_BIN" scripts/summarize_session.py \
        --topic "$TOPIC" \
        --file "$CONVERSATION_FILE"
else
    echo "[Memory Hook] 无对话内容可保存（请通过参数、文件或环境变量提供）" >&2
    exit 1
fi

if [ $? -ne 0 ]; then
    echo "[Memory Hook] 保存失败 — Python 脚本返回错误" >&2
    exit 1
fi
echo "[Memory Hook] 记忆保存完成：$TOPIC"
