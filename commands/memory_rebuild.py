"""
commands/memory_rebuild.py — /memory rebuild 命令处理器 (v0.6.0)
"""

from __future__ import annotations

from commands.base import Command, CommandResult

REBUILD_COMMAND = Command(
    name="memory:rebuild",
    aliases=["memory-rebuild", "/memory-rebuild", "rebuild"],
    description="从 Markdown 文件重建 index.json 索引",
    usage="/memory rebuild [--workspace <name>]",
    args_schema={
        "workspace": {"type": "string", "required": False,
                       "description": "workspace 名称"},
    },
    handler=None,
)


def _handler(args: dict) -> CommandResult:
    import sys
    import os
    _scripts = os.path.join(os.path.dirname(__file__), "..", "scripts")
    sys.path.insert(0, os.path.abspath(_scripts))

    from memory_core import rebuild_index
    workspace = args.get("workspace", "")

    try:
        index = rebuild_index(workspace=workspace)
        return CommandResult(
            ok=True,
            data={"total_topics": len(index)},
            message=f"索引重建完成，共 {len(index)} 个主题",
        )
    except Exception as e:
        return CommandResult(ok=False, message="索引重建失败", error=str(e))


REBUILD_COMMAND.handler = _handler
