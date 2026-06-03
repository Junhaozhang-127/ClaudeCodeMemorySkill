"""
summarize_session.py

保存当前 Claude Code 对话摘要到 Markdown 记忆库。

示例：
python scripts/summarize_session.py --topic "Claude Code 记忆机制" --text "本轮对话内容"
"""

from __future__ import annotations

import argparse
from pathlib import Path
from memory_core import save_memory


def main() -> None:
    parser = argparse.ArgumentParser(description="Save Claude Code conversation memory.")
    parser.add_argument("--topic", required=True, help="对话主题")
    parser.add_argument("--text", help="对话内容")
    parser.add_argument("--file", help="从文本文件读取对话内容")
    parser.add_argument("--no-append", action="store_true", help="同主题同日期文件存在时不追加，而是覆盖")
    args = parser.parse_args()

    if args.file:
        conversation_text = Path(args.file).read_text(encoding="utf-8")
    elif args.text:
        conversation_text = args.text
    else:
        raise SystemExit("必须提供 --text 或 --file")

    path = save_memory(args.topic, conversation_text, append=not args.no_append)
    print(f"Memory saved: {path}")


if __name__ == "__main__":
    main()
