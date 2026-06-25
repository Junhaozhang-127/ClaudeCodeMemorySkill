"""
session_cli.py — Session Workspace Manager CLI 入口 (v0.7.0 Phase 2)

命令行调用:
    python scripts/session_cli.py list
    python scripts/session_cli.py create --title "Test"
    python scripts/session_cli.py current
    python scripts/session_cli.py use --session-id default
    python scripts/session_cli.py rename --session-id xxx --title "New"
    python scripts/session_cli.py archive --session-id xxx
    python scripts/session_cli.py delete --session-id xxx
    python scripts/session_cli.py restore --session-id xxx
    python scripts/session_cli.py info [--session-id xxx]
"""

from __future__ import annotations

import argparse
import sys

# Add scripts/ to path for imports
from pathlib import Path
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Session Workspace Manager CLI",
        prog="session_cli",
    )
    sub = parser.add_subparsers(dest="action")

    # list
    lp = sub.add_parser("list", help="列出会话")
    lp.add_argument("--include-archived", action="store_true")
    lp.add_argument("--include-deleted", action="store_true")

    # create
    cp = sub.add_parser("create", help="创建新会话")
    cp.add_argument("--title", required=True, help="会话标题")
    cp.add_argument("--description", default="", help="会话描述")
    cp.add_argument("--tags", default="", help="标签，逗号分隔")
    cp.add_argument("--use", action="store_true", help="创建后立即切换")

    # current
    sub.add_parser("current", help="查看当前会话")

    # use
    up = sub.add_parser("use", help="切换当前会话")
    up.add_argument("--session-id", required=True, help="目标会话 ID")
    up.add_argument("--allow-archived", action="store_true",
                    help="允许切换到已归档会话")

    # rename
    rnp = sub.add_parser("rename", help="重命名会话")
    rnp.add_argument("--session-id", required=True)
    rnp.add_argument("--title", required=True, help="新标题")

    # archive
    arp = sub.add_parser("archive", help="归档会话")
    arp.add_argument("--session-id", required=True)

    # delete
    dp = sub.add_parser("delete", help="软删除会话")
    dp.add_argument("--session-id", required=True)

    # restore
    resp = sub.add_parser("restore", help="恢复已删除会话")
    resp.add_argument("--session-id", required=True)
    resp.add_argument("--use", action="store_true", help="恢复后立即切换")

    # info
    ip = sub.add_parser("info", help="会话详情")
    ip.add_argument("--session-id", default="", help="目标会话 ID（空则查看当前）")

    # link
    lkp = sub.add_parser("link", help="链接其他会话")
    lkp.add_argument("--from", dest="from_id", default="", help="源会话 ID（默认当前）")
    lkp.add_argument("--to", required=True, help="目标会话 ID")
    lkp.add_argument("--reason", default="", help="链接原因")
    lkp.add_argument("--allow-archived", action="store_true", help="允许链接已归档会话")

    # unlink
    ulp = sub.add_parser("unlink", help="取消链接")
    ulp.add_argument("--from", dest="from_id", default="", help="源会话 ID（默认当前）")
    ulp.add_argument("--to", required=True, help="目标会话 ID")

    # links
    lsp = sub.add_parser("links", help="列出已链接会话")
    lsp.add_argument("--session-id", default="", help="会话 ID（默认当前）")
    lsp.add_argument("--include-archived", action="store_true")

    # tui
    tui_p = sub.add_parser("tui", help="交互式会话选择器")
    tui_p.add_argument("--include-archived", action="store_true")
    tui_p.add_argument("--include-deleted", action="store_true")

    args = parser.parse_args()
    if not args.action:
        parser.print_help()
        sys.exit(1)

    if args.action == "tui":
        from session_tui import run_session_tui
        msg = run_session_tui(
            include_archived=getattr(args, 'include_archived', False),
            include_deleted=getattr(args, 'include_deleted', False),
        )
        print(msg)
        sys.exit(0)

    from commands.memory_session import _handler

    # Convert argparse namespace to dict matching Command arg schema
    kwargs = {k: v for k, v in vars(args).items() if v is not None}
    # Map --from (dest=from_id) to 'from' key
    if hasattr(args, 'from_id') and args.from_id:
        kwargs['from'] = args.from_id
    kwargs["action"] = args.action
    # Convert boolean flags to actual bool values
    for flag in ("include_archived", "include_deleted", "use",
                 "allow_archived"):
        if hasattr(args, flag):
            kwargs[flag] = getattr(args, flag, False)

    result = _handler(kwargs)
    if result.ok:
        import json
        print(json.dumps(result.data, ensure_ascii=False, indent=2))
        print(f"\nOK: {result.message}")
    else:
        print(f"ERROR: {result.error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
