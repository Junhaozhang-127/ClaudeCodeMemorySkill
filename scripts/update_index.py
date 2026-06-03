"""
update_index.py

扫描 memory/topics 目录，重建 index.json。

示例：
python scripts/update_index.py
"""

from __future__ import annotations

from memory_core import rebuild_index


def main() -> None:
    index = rebuild_index()
    print(f"Index rebuilt. Total topics: {len(index)}")


if __name__ == "__main__":
    main()
