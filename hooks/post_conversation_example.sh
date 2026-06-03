#!/usr/bin/env bash
# 示例：会话后写入记忆。
# 实际接入 Claude Code Hook 时，需要根据 Hook 可获得的环境变量/输入调整。
#
# 用法：
# bash hooks/post_conversation_example.sh "主题" "/path/to/conversation.txt"

set -e

TOPIC="${1:-未命名对话}"
CONVERSATION_FILE="${2:-}"

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ -z "$CONVERSATION_FILE" ]; then
  echo "请提供对话文本文件路径：bash hooks/post_conversation_example.sh \"主题\" conversation.txt"
  exit 1
fi

python "$PROJECT_DIR/scripts/summarize_session.py" --topic "$TOPIC" --file "$CONVERSATION_FILE"
