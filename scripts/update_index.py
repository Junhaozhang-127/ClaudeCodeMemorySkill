"""
update_index.py

扫描 memory/topics 目录，重建 index.json。

示例：
python scripts/update_index.py
python scripts/update_index.py --workspace my-project
"""

from __future__ import annotations

import argparse
from memory_core import rebuild_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild memory index.")
    parser.add_argument("--workspace", default="", help="workspace 名称（空则使用默认路径）")
    args = parser.parse_args()
    index = rebuild_index(workspace=args.workspace)
    print(f"Index rebuilt. Total topics: {len(index)}")


if __name__ == "__main__":
    main()
