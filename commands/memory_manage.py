"""
commands/memory_manage.py — /memory manage 命令处理器 (v0.6.0)

支持子命令: quality / dedup / expire / merge / archive
"""

from __future__ import annotations

from commands.base import Command, CommandResult

MANAGE_COMMAND = Command(
    name="memory:manage",
    aliases=["memory-manage", "/memory-manage", "manage"],
    description="记忆管理命令 — 质量报告、去重、过期、合并、归档",
    usage="/memory manage <action> [options]\n"
          "  actions: quality / dedup / expire / merge / archive",
    args_schema={
        "action": {"type": "string", "required": True,
                   "description": "子命令: quality / dedup / expire / merge / archive"},
        "workspace": {"type": "string", "required": False,
                       "description": "workspace 名称"},
        "threshold": {"type": "number", "required": False,
                       "description": "去重相似度阈值 (0-1, 默认: 0.5)"},
        "days": {"type": "int", "required": False,
                  "description": "归档/过期天数阈值 (默认: 180)"},
        "apply": {"type": "bool", "required": False,
                   "description": "是否实际执行 (默认: dry-run)"},
        "topic": {"type": "string", "required": False,
                   "description": "合并时的目标主题"},
    },
    handler=None,
)


def _handler(args: dict) -> CommandResult:
    import sys
    import os
    _scripts = os.path.join(os.path.dirname(__file__), "..", "scripts")
    sys.path.insert(0, os.path.abspath(_scripts))

    action = args.get("action", "")
    if not action:
        return CommandResult(ok=False, message="参数错误",
                            error="action 是必需参数 (quality/dedup/expire/merge/archive)")

    try:
        if action == "quality":
            return _do_quality(args)
        elif action == "dedup":
            return _do_dedup(args)
        elif action == "expire":
            return _do_expire(args)
        elif action == "merge":
            return _do_merge(args)
        elif action == "archive":
            return _do_archive(args)
        else:
            return CommandResult(ok=False, message="未知子命令",
                                error=f"未知 action: {action}。"
                                      f"可用: quality, dedup, expire, merge, archive")
    except Exception as e:
        return CommandResult(ok=False, message=f"{action} 失败", error=str(e))


def _do_quality(args: dict) -> CommandResult:
    from memory_lifecycle import generate_quality_report
    report = generate_quality_report(workspace=args.get("workspace", ""))
    return CommandResult(ok=True, data=report,
                        message=f"质量报告: {report['total']} 条记忆, "
                                f"{report['active']} active, "
                                f"{report['duplicate_candidates']} 重复候选")


def _do_dedup(args: dict) -> CommandResult:
    from memory_core import load_index
    from memory_maintenance import detect_duplicates
    threshold = args.get("threshold", 0.5)
    workspace = args.get("workspace", "")
    index = load_index(workspace)
    pairs = detect_duplicates(index, threshold=threshold)
    return CommandResult(ok=True,
                        data={"pairs": len(pairs), "threshold": threshold,
                              "duplicates": [
                                  {"a": a, "b": b, "similarity": s}
                                  for a, b, s in pairs
                              ]},
                        message=f"发现 {len(pairs)} 对候选重复 (阈值={threshold})")


def _do_expire(args: dict) -> CommandResult:
    from memory_core import load_index, save_index
    from memory_lifecycle import auto_expire
    apply = args.get("apply", False)
    workspace = args.get("workspace", "")
    index = load_index(workspace)
    expired_count, updated = auto_expire(index, days=args.get("days", 0), apply=apply)
    if apply and expired_count > 0:
        save_index(updated, workspace)
    return CommandResult(ok=True,
                        data={"expired_count": expired_count, "applied": apply},
                        message=f"{'已' if apply else '将'}过期 {expired_count} 条记忆")


def _do_merge(args: dict) -> CommandResult:
    from memory_core import load_index
    from memory_maintenance import merge_memories, detect_duplicates
    from pathlib import Path

    apply = args.get("apply", False)
    workspace = args.get("workspace", "")

    # resolve paths
    from memory_core import _resolve_paths, PROJECT_ROOT
    _, topics_dir, _ = _resolve_paths(workspace)
    index = load_index(workspace)

    # Find duplicate pairs
    pairs = detect_duplicates(index, threshold=0.6)
    if not pairs:
        return CommandResult(ok=True, data={"merged": 0},
                            message="无符合条件的重复记忆可合并")

    if apply:
        merged = 0
        for a, b, _ in pairs[:5]:  # max 5 merges per run
            preview = merge_memories(index, topics_dir, [a, b], apply=True)
            if not preview:
                merged += 1
        return CommandResult(ok=True, data={"merged": merged},
                            message=f"已合并 {merged} 对重复记忆")
    else:
        return CommandResult(ok=True,
                            data={"pairs_found": len(pairs), "sample": pairs[:5]},
                            message=f"[dry-run] {len(pairs)} 对候选，"
                                    f"加 --apply 执行合并")


def _do_archive(args: dict) -> CommandResult:
    from memory_core import load_index
    from memory_maintenance import archive_old
    from pathlib import Path

    apply = args.get("apply", False)
    days = args.get("days", 180)
    workspace = args.get("workspace", "")

    from memory_core import _resolve_paths
    _, topics_dir, _ = _resolve_paths(workspace)
    index = load_index(workspace)

    result = archive_old(index, topics_dir, days=days, apply=apply)
    count = result.get("to_archive_count", 0) if result else 0
    return CommandResult(ok=True,
                        data={"count": count, "days": days, "applied": apply},
                        message=f"{'已' if apply else '将'}归档 {count} 条记忆"
                                f" (>{days} 天)")


MANAGE_COMMAND.handler = _handler
