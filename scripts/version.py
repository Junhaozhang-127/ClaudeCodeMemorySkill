"""
version.py — 项目版本与元信息

提供统一的版本号、阶段状态和能力查询。
"""

from __future__ import annotations

__version__ = "0.7.0"
PHASE = "Phase 7"
BUILD_STATUS = "release"


def get_version_info() -> dict:
    """返回完整版本信息字典。"""
    return {
        "version": __version__,
        "phase": PHASE,
        "build_status": BUILD_STATUS,
        "python_min": "3.7",
        "dependencies": {
            "required": [],
            "optional": ["jieba"],
        },
        "retrievers": {
            "keyword": "implemented",
            "hybrid": "implemented",
            "embedding": "implemented",
            "semantic": "implemented",
        },
        "summarizers": {
            "rule": "implemented",
            "llm": "implemented",
        },
        "memory_lifecycle": "implemented",
        "storage": "markdown + json",
        "workspace_support": True,
        "plugin_status": "manifest-template",
    }


if __name__ == "__main__":
    import json
    import sys

    if "--json" in sys.argv:
        print(json.dumps(get_version_info(), ensure_ascii=False, indent=2))
    else:
        print(f"Claude Code Memory Skill v{__version__} ({PHASE}, {BUILD_STATUS})")
