#!/usr/bin/env bash
# 示例：用户输入前检索相关记忆。
#
# 用法：
# bash hooks/pre_prompt_example.sh "用户当前问题"

set -e

QUERY="${1:-}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ -z "$QUERY" ]; then
  echo "请提供查询内容：bash hooks/pre_prompt_example.sh \"用户当前问题\""
  exit 1
fi

python "$PROJECT_DIR/scripts/retrieve_memory.py" --query "$QUERY" --top-k 5
