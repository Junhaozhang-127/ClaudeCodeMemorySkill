"""
retrieve_memory.py

根据用户输入检索相关 Markdown 记忆，并输出可注入 Claude Code 的上下文。

示例：
python scripts/retrieve_memory.py --query "Claude Code 如何恢复历史上下文"
"""

from __future__ import annotations

import argparse
import sys
from memory_core import retrieve_memory, format_context

# Windows 下 stdout 默认编码为 cp936，导致 --json 输出解析失败。
# reconfigure 在 Python 3.7+ 可用。
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve Claude Code memory.")
    parser.add_argument("--query", required=True, help="用户当前输入或检索问题")
    parser.add_argument("--top-k", type=int, default=5, help="最多返回几条相关记忆")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = parser.parse_args()

    results = retrieve_memory(args.query, top_k=args.top_k)

    if args.json:
        import json
        print(json.dumps(results, ensure_ascii=False, indent=2))
    else:
        print(format_context(results))


if __name__ == "__main__":
    main()
