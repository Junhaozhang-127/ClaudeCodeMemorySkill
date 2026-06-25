"""
commands/memory_retrieve.py — /memory retrieve 命令处理器 (v0.6.0)
"""

from __future__ import annotations

from commands.base import Command, CommandResult

RETRIEVE_COMMAND = Command(
    name="memory:retrieve",
    aliases=["memory-retrieve", "/memory-retrieve", "retrieve"],
    description="检索相关历史记忆并注入上下文",
    usage="/memory retrieve <查询> [--mode keyword|semantic|hybrid] [--top-k N]",
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

    # Resolve tags
    tags = None
    tags_str = args.get("tags", "")
    if tags_str:
        tags = [t.strip() for t in tags_str.split(",") if t.strip()]

    # Get embedding provider for semantic/hybrid modes
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
        )

        is_json = args.get("json", False)
        if is_json:
            import json
            output = json.dumps(results, ensure_ascii=False, indent=2)
        else:
            output = format_context(results)

        return CommandResult(
            ok=True,
            data={"hit_count": len(results), "mode": mode,
                  "results": results if is_json else []},
            message=f"检索完成，返回 {len(results)} 条记忆",
        )
    except Exception as e:
        return CommandResult(ok=False, message="检索失败", error=str(e))


RETRIEVE_COMMAND.handler = _handler
