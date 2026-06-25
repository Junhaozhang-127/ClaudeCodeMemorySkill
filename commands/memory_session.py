"""
commands/memory_session.py — /memory session 命令处理器 (v0.7.0 Phase 4)

支持 12 个 action:
  list, create, current, use, rename, archive, delete, restore, info, link, unlink, links
"""

from __future__ import annotations

from commands.base import Command, CommandResult

SESSION_COMMAND = Command(
    name="memory:session",
    aliases=["memory-session", "/memory-session", "session", "sessions"],
    description="会话空间管理 — 创建、切换、重命名、归档、删除、恢复、查看、链接会话",
    usage=(
        "/memory session <action> [options]\n"
        "  actions:\n"
        "    list      — 列出会话\n"
        "    create    — 创建新会话\n"
        "    current   — 查看当前会话\n"
        "    use       — 切换当前会话\n"
        "    rename    — 重命名会话\n"
        "    archive   — 归档会话\n"
        "    delete    — 软删除会话\n"
        "    restore   — 恢复已删除会话\n"
        "    info      — 会话详情\n"
        "    link      — 链接其他会话\n"
        "    unlink    — 取消链接\n"
        "    links     — 列出已链接会话"
    ),
    args_schema={
        "action": {"type": "string", "required": True,
                   "description": "子命令: list / create / current / use / rename / archive / delete / restore / info / link / unlink / links"},
        "title": {"type": "string", "required": False,
                   "description": "会话标题 (create / rename 需要)"},
        "description": {"type": "string", "required": False,
                         "description": "会话描述 (create 可选)"},
        "tags": {"type": "string", "required": False,
                  "description": "标签，逗号分隔 (create 可选)"},
        "session_id": {"type": "string", "required": False,
                        "description": "目标会话 ID (use / rename / archive / delete / restore / info)"},
        "use": {"type": "bool", "required": False,
                 "description": "创建/恢复后立即切换为当前会话"},
        "allow_archived": {"type": "bool", "required": False,
                            "description": "允许操作已归档会话"},
        "include_archived": {"type": "bool", "required": False,
                              "description": "列出时包含已归档会话 (list/links 可选)"},
        "include_deleted": {"type": "bool", "required": False,
                             "description": "列出时包含已删除会话 (list 可选)"},
        "from": {"type": "string", "required": False,
                  "description": "源会话 ID (link/unlink 可选，默认当前会话)"},
        "to": {"type": "string", "required": False,
                "description": "目标会话 ID (link/unlink 需要)"},
        "reason": {"type": "string", "required": False,
                    "description": "链接原因 (link 可选)"},
    },
    handler=None,
)

ACTIONS = "list, create, current, use, rename, archive, delete, restore, info, link, unlink, links"


def _handler(args: dict) -> CommandResult:
    action = (args.get("action", "") or "").strip().lower()
    if not action:
        return CommandResult(ok=False, message="参数错误",
                            error=f"action 是必需参数。可用: {ACTIONS}")

    try:
        if action == "list":
            return _do_list(args)
        elif action == "create":
            return _do_create(args)
        elif action == "current":
            return _do_current(args)
        elif action == "use":
            return _do_use(args)
        elif action == "rename":
            return _do_rename(args)
        elif action == "archive":
            return _do_archive(args)
        elif action == "delete":
            return _do_delete(args)
        elif action == "restore":
            return _do_restore(args)
        elif action == "info":
            return _do_info(args)
        elif action == "link":
            return _do_link(args)
        elif action == "unlink":
            return _do_unlink(args)
        elif action == "links":
            return _do_links(args)
        elif action == "tui":
            return _do_tui(args)
        else:
            return CommandResult(
                ok=False, message="未知子命令",
                error=f"未知 action: {action}。可用: {ACTIONS}",
            )
    except ValueError as e:
        return CommandResult(ok=False, message="操作被拒绝", error=str(e))
    except Exception as e:
        return CommandResult(ok=False, message=f"{action} 失败", error=str(e))


def _get_mgr():
    import sys, os
    _scripts = os.path.join(os.path.dirname(__file__), "..", "scripts")
    sys.path.insert(0, os.path.abspath(_scripts))
    from session_manager import get_session_manager
    return get_session_manager()


# ── 已有 actions (Phase 2) ──────────────────────────────────

def _do_list(args: dict) -> CommandResult:
    mgr = _get_mgr()
    include_archived = bool(args.get("include_archived", False))
    include_deleted = bool(args.get("include_deleted", False))
    sessions = mgr.list_sessions(include_archived=include_archived,
                                  include_deleted=include_deleted)
    curr = mgr.get_current_session()
    curr_id = curr.session_id if curr else ""
    result_list = []
    for s in sessions:
        result_list.append({
            "session_id": s.session_id, "title": s.title, "status": s.status,
            "tags": s.tags, "memory_count": s.memory_count,
            "summary_count": s.summary_count,
            "last_accessed_at": s.last_accessed_at,
            "is_current": s.session_id == curr_id,
        })
    return CommandResult(ok=True,
                        data={"sessions": result_list, "count": len(result_list),
                              "current_session_id": curr_id},
                        message=f"共 {len(result_list)} 个会话 (当前: {curr_id})")


def _do_create(args: dict) -> CommandResult:
    title = (args.get("title", "") or "").strip()
    if not title:
        return CommandResult(ok=False, message="参数错误", error="title 是必需参数")
    description = (args.get("description", "") or "").strip()
    tags_str = (args.get("tags", "") or "").strip()
    tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else []
    do_use = bool(args.get("use", False))
    mgr = _get_mgr()
    manifest = mgr.create_session(title=title, description=description, tags=tags)
    if do_use:
        mgr.set_current_session(manifest.session_id)
    return CommandResult(ok=True,
                        data={"session_id": manifest.session_id, "title": manifest.title,
                              "status": manifest.status, "is_current": do_use},
                        message=f"会话已创建: {manifest.session_id}{' (已切换)' if do_use else ''}")


def _do_current(args: dict) -> CommandResult:
    mgr = _get_mgr()
    curr = mgr.get_current_session()
    path = str(mgr.get_session_path(curr.session_id))
    return CommandResult(ok=True,
                        data={"session_id": curr.session_id, "title": curr.title,
                              "status": curr.status, "path": path},
                        message=f"当前会话: {curr.session_id} ({curr.title})")


def _do_use(args: dict) -> CommandResult:
    session_id = (args.get("session_id", "") or "").strip()
    if not session_id:
        return CommandResult(ok=False, message="参数错误", error="session_id 是必需参数")
    mgr = _get_mgr()
    manifest = mgr.get_session(session_id)
    if manifest is None:
        return CommandResult(ok=False, message="会话不存在", error=f"未找到会话: {session_id}")
    if manifest.status == "deleted":
        return CommandResult(ok=False, message="无法切换", error=f"会话 {session_id} 已删除，请先 restore")
    if manifest.status == "archived" and not bool(args.get("allow_archived", False)):
        return CommandResult(ok=False, message="无法切换", error=f"会话 {session_id} 已归档，使用 --allow-archived")
    mgr.set_current_session(session_id)
    return CommandResult(ok=True, data={"session_id": session_id, "title": manifest.title},
                        message=f"已切换到: {session_id} ({manifest.title})")


def _do_rename(args: dict) -> CommandResult:
    session_id = (args.get("session_id", "") or "").strip()
    title = (args.get("title", "") or "").strip()
    if not session_id:
        return CommandResult(ok=False, message="参数错误", error="session_id 是必需参数")
    if not title:
        return CommandResult(ok=False, message="参数错误", error="title 是必需参数，不能为空")
    mgr = _get_mgr()
    manifest = mgr.rename_session(session_id, title)
    return CommandResult(ok=True, data={"session_id": session_id, "title": manifest.title},
                        message=f"已重命名: {session_id} → {title}")


def _do_archive(args: dict) -> CommandResult:
    session_id = (args.get("session_id", "") or "").strip()
    if not session_id:
        return CommandResult(ok=False, message="参数错误", error="session_id 是必需参数")
    if session_id == "default":
        return CommandResult(ok=False, message="操作被拒绝", error="不能归档 default session")
    mgr = _get_mgr()
    manifest = mgr.archive_session(session_id)
    return CommandResult(ok=True, data={"session_id": session_id, "status": manifest.status},
                        message=f"已归档: {session_id} ({manifest.title})")


def _do_delete(args: dict) -> CommandResult:
    session_id = (args.get("session_id", "") or "").strip()
    if not session_id:
        return CommandResult(ok=False, message="参数错误", error="session_id 是必需参数")
    if session_id == "default":
        return CommandResult(ok=False, message="操作被拒绝", error="不能删除 default session")
    mgr = _get_mgr()
    manifest = mgr.delete_session(session_id)
    return CommandResult(ok=True, data={"session_id": session_id, "status": manifest.status},
                        message=f"已软删除: {session_id} ({manifest.title})。目录保留，可用 restore 恢复。")


def _do_restore(args: dict) -> CommandResult:
    session_id = (args.get("session_id", "") or "").strip()
    if not session_id:
        return CommandResult(ok=False, message="参数错误", error="session_id 是必需参数")
    mgr = _get_mgr()
    manifest = mgr.restore_session(session_id)
    do_use = bool(args.get("use", False))
    if do_use:
        mgr.set_current_session(session_id)
    return CommandResult(ok=True,
                        data={"session_id": session_id, "status": manifest.status,
                              "is_current": do_use},
                        message=f"已恢复: {session_id} ({manifest.title}){' (已切换)' if do_use else ''}")


def _do_info(args: dict) -> CommandResult:
    mgr = _get_mgr()
    session_id = (args.get("session_id", "") or "").strip()
    if not session_id:
        curr = mgr.get_current_session()
        session_id = curr.session_id
    manifest = mgr.get_session(session_id)
    if manifest is None:
        return CommandResult(ok=False, message="会话不存在", error=f"未找到会话: {session_id}")
    session_dir = mgr.get_session_path(session_id)
    try:
        events_path = session_dir / "events.jsonl"
        events_count = sum(1 for _ in events_path.read_text(encoding="utf-8").split("\n") if _.strip()) if events_path.exists() else 0
    except Exception:
        events_count = -1
    file_status = {}
    for fname in ["manifest.json", "memories.jsonl", "summaries.jsonl",
                   "embeddings.jsonl", "links.json", "events.jsonl"]:
        p = session_dir / fname
        file_status[fname] = {"exists": p.exists(), "size_bytes": p.stat().st_size if p.exists() else 0}
    is_current = mgr.get_current_session().session_id == session_id
    return CommandResult(ok=True,
                        data={"session_id": manifest.session_id, "title": manifest.title,
                              "description": manifest.description, "status": manifest.status,
                              "tags": manifest.tags, "created_at": manifest.created_at,
                              "updated_at": manifest.updated_at,
                              "last_accessed_at": manifest.last_accessed_at,
                              "memory_count": manifest.memory_count,
                              "summary_count": manifest.summary_count,
                              "linked_session_ids": manifest.linked_session_ids,
                              "metadata": manifest.metadata, "path": str(session_dir),
                              "is_current": is_current, "events_count": events_count,
                              "files": file_status},
                        message=f"会话详情: {session_id} ({manifest.title})")


# ── Phase 4: link / unlink / links ──────────────────────────

def _do_link(args: dict) -> CommandResult:
    source_id = (args.get("from", "") or "").strip()
    target_id = (args.get("to", "") or "").strip()
    if not target_id:
        return CommandResult(ok=False, message="参数错误", error="--to 是必需参数")
    mgr = _get_mgr()
    if not source_id:
        source_id = mgr.get_current_session().session_id
    reason = (args.get("reason", "") or "").strip()
    allow_archived = bool(args.get("allow_archived", False))
    result = mgr.link_session(source_id, target_id, reason=reason,
                               allow_archived=allow_archived)
    if result.get("already_linked"):
        return CommandResult(ok=True, data=result,
                            message=f"已链接: {target_id} (already linked)")
    return CommandResult(ok=True, data=result,
                        message=f"已链接: {source_id} → {target_id}")


def _do_unlink(args: dict) -> CommandResult:
    source_id = (args.get("from", "") or "").strip()
    target_id = (args.get("to", "") or "").strip()
    if not target_id:
        return CommandResult(ok=False, message="参数错误", error="--to 是必需参数")
    mgr = _get_mgr()
    if not source_id:
        source_id = mgr.get_current_session().session_id
    result = mgr.unlink_session(source_id, target_id)
    return CommandResult(ok=True, data=result,
                        message=f"已取消链接: {target_id}")


def _do_links(args: dict) -> CommandResult:
    mgr = _get_mgr()
    session_id = (args.get("session_id", "") or "").strip()
    if not session_id:
        session_id = mgr.get_current_session().session_id
    include_archived = bool(args.get("include_archived", False))
    linked = mgr.list_linked_sessions(session_id, include_archived=include_archived)
    result = []
    for m in linked:
        result.append({"session_id": m.session_id, "title": m.title,
                       "status": m.status, "memory_count": m.memory_count,
                       "last_accessed_at": m.last_accessed_at})
    return CommandResult(ok=True,
                        data={"source_session_id": session_id,
                              "linked_sessions": result, "count": len(result)},
                        message=f"{session_id} 有 {len(result)} 个链接会话")


def _do_tui(args: dict) -> CommandResult:
    import sys
    if not sys.stdin.isatty():
        return CommandResult(
            ok=False, message="非交互环境",
            error="Interactive TUI requires a terminal. "
                  "Use `memory:session list/use/delete` or "
                  "`python scripts/session_cli.py tui` instead.",
        )
    from session_tui import run_session_tui
    include_archived = bool(args.get("include_archived", False))
    include_deleted = bool(args.get("include_deleted", False))
    result = run_session_tui(
        include_archived=include_archived,
        include_deleted=include_deleted,
    )
    return CommandResult(ok=True, data={"exit_message": result},
                        message="TUI exited")


SESSION_COMMAND.handler = _handler
