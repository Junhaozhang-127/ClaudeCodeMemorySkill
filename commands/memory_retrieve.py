"""
commands/memory_retrieve.py — /memory retrieve 命令处理器 (v0.7.0)
"""

from __future__ import annotations

from commands.base import Command, CommandResult

RETRIEVE_COMMAND = Command(
    name="memory:retrieve",
    aliases=["memory-retrieve", "/memory-retrieve", "retrieve"],
    description="检索相关历史记忆并注入上下文",
    usage="/memory retrieve <查询> [--mode keyword|semantic|hybrid] [--top-k N] [--session-id <id>] [--all-sessions]",
    args_schema={
        "query": {"type": "string", "required": True,
                  "description": "检索查询"},
        "mode": {"type": "string", "required": False,
                 "description": "检索模式: keyword / semantic / hybrid (默认: hybrid)"},
        "top_k": {"type": "int", "required": False,
                   "description": "返回结果数 (默认: 5)"},
        "json": {"type": "bool", "required": False,
                  "description": "以 JSON 格式输出"},
        "workspace": {"type": "string", "required": False,
                       "description": "workspace 名称"},
        "tags": {"type": "string", "required": False,
                 "description": "按标签过滤 (逗号分隔，暂未实现)"},
        "include_expired": {"type": "bool", "required": False,
                            "description": "包含已过期记忆"},
        "session_id": {"type": "string", "required": False,
                        "description": "只检索指定会话（默认: 当前会话）"},
        "all_sessions": {"type": "bool", "required": False,
                          "description": "检索所有活跃会话"},
        "include_archived_sessions": {"type": "bool", "required": False,
                                       "description": "all_sessions 时包含已归档会话"},
        "include_linked_sessions": {"type": "bool", "required": False,
                                     "description": "包含当前会话已链接的会话"},
    },
    handler=None,
)


def _handler(args: dict) -> CommandResult:
    import sys
    import os
    _scripts = os.path.join(os.path.dirname(__file__), "..", "scripts")
    sys.path.insert(0, os.path.abspath(_scripts))

    from memory_core import retrieve_memory, format_context

    query = args.get("query", "")
    if not query:
        return CommandResult(ok=False, message="参数错误",
                            error="query 是必需参数")

    mode = args.get("mode", "hybrid")
    top_k = args.get("top_k", 5)
    workspace = args.get("workspace", "")
    include_expired = args.get("include_expired", False)
    session_id = args.get("session_id", None)
    all_sessions = bool(args.get("all_sessions", False))
    include_archived_sessions = bool(args.get("include_archived_sessions", False))
    include_linked_sessions = bool(args.get("include_linked_sessions", False))

    tags = None
    tags_str = args.get("tags", "")
    if tags_str:
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

    embedding_provider = None
    if mode in ("semantic", "hybrid"):
        try:
            from embedding_provider import get_embedding_provider
            embedding_provider = get_embedding_provider(provider="auto")
        except Exception:
            pass

    try:
        results = retrieve_memory(
            query, top_k=top_k, workspace=workspace,
            mode=mode, embedding_provider=embedding_provider,
            tags=tags, include_expired=include_expired,
            session_id=session_id, all_sessions=all_sessions,
            include_archived_sessions=include_archived_sessions,
            include_linked_sessions=include_linked_sessions,
        )

        is_json = args.get("json", False)
        if is_json:
            import json
            output = json.dumps(results, ensure_ascii=False, indent=2)
        else:
            output = format_context(results)

        scope = "all" if all_sessions else (session_id or "current")
        return CommandResult(
            ok=True,
            data={"hit_count": len(results), "mode": mode,
                  "retrieval_scope": scope,
                  "results": results if is_json else []},
            message=f"检索完成 (scope={scope})，返回 {len(results)} 条记忆",
        )
    except Exception as e:
        return CommandResult(ok=False, message="检索失败", error=str(e))


RETRIEVE_COMMAND.handler = _handler
