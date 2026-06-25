"""
commands/memory_save.py — /memory save 命令处理器 (v0.6.0)
"""

from __future__ import annotations

from commands.base import Command, CommandResult

SAVE_COMMAND = Command(
    name="memory:save",
    aliases=["memory-save", "/memory-save", "save"],
    description="保存当前对话为结构化 Markdown 记忆",
    usage="/memory save <主题> [--text <内容>] [--file <路径>] [--summary-mode rule|llm|auto]",
    args_schema={
        "topic": {"type": "string", "required": True,
                  "description": "记忆主题"},
        "text": {"type": "string", "required": False,
                 "description": "对话内容文本"},
        "file": {"type": "string", "required": False,
                 "description": "从文本文件读取对话内容"},
        "summary_mode": {"type": "string", "required": False,
                         "description": "摘要模式: rule / llm / auto (默认: rule)"},
        "no_append": {"type": "bool", "required": False,
                       "description": "覆盖而非追加（默认: false）"},
        "workspace": {"type": "string", "required": False,
                       "description": "workspace 名称"},
    },
    handler=None,  # set below after import
)


def _handler(args: dict) -> CommandResult:
    """执行记忆保存命令。"""
    import sys
    import os
    # Ensure scripts/ is importable
    _scripts = os.path.join(os.path.dirname(__file__), "..", "scripts")
    sys.path.insert(0, os.path.abspath(_scripts))

    from memory_core import save_memory
    from pathlib import Path

    topic = args.get("topic", "")
    if not topic:
        return CommandResult(ok=False, message="参数错误",
                            error="topic 是必需参数")

    text = args.get("text", "")
    file_path = args.get("file", "")
    if file_path:
        try:
            text = Path(file_path).read_text(encoding="utf-8")
        except Exception as e:
            return CommandResult(ok=False, message="文件读取失败",
                                error=str(e))
    if not text:
        return CommandResult(ok=False, message="参数错误",
                            error="必须提供 --text 或 --file")

    summary_mode = args.get("summary_mode", "rule")
    append = not args.get("no_append", False)
    workspace = args.get("workspace", "")

    # LLM summarizer support
    summarizer = None
    if summary_mode in ("llm", "auto"):
        try:
            from llm_provider import get_llm_provider
            from summarizers import LLMSummarizer
            provider = get_llm_provider(provider="auto")
            kw_fn = _get_keyword_fn()
            summarizer = LLMSummarizer(provider=provider, keyword_extractor=kw_fn)
        except Exception:
            pass  # 自动降级到 rule fallback

    try:
        path = save_memory(topic, text, append=append, workspace=workspace,
                          summarizer=summarizer)
        return CommandResult(
            ok=True,
            data={"file": str(path), "topic": topic},
            message=f"记忆已保存: {path}",
        )
    except Exception as e:
        return CommandResult(ok=False, message="保存失败", error=str(e))


def _get_keyword_fn():
    try:
        from memory_core import extract_keywords
        return extract_keywords
    except Exception:
        return None


SAVE_COMMAND.handler = _handler
