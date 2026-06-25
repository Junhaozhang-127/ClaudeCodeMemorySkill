"""
session_tui.py — Interactive Session Selector TUI (v0.7.0 Phase 5)

Architecture:
  - SessionTUIState: 状态数据
  - SessionTUIController: 业务逻辑（可测试）
  - SessionTUIRenderer: 纯文本渲染（可测试）
  - read_key / SessionTUI.run: 终端 I/O

Usage:
    python scripts/session_tui.py
    python scripts/session_tui.py --include-archived
    python scripts/session_tui.py --include-deleted
"""

from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# ═══════════════════════════════════════════════════════════════
# SessionTUIState
# ═══════════════════════════════════════════════════════════════

@dataclass
class SessionTUIState:
    sessions: list[dict] = field(default_factory=list)
    selected_index: int = 0
    current_session_id: str = "default"
    include_archived: bool = False
    include_deleted: bool = False
    message: str = ""
    mode: str = "list"  # list / input_title / confirm_delete
    input_buffer: str = ""
    input_prompt: str = ""
    input_action: str = ""  # create / rename
    input_session_id: str = ""
    running: bool = False


# ═══════════════════════════════════════════════════════════════
# SessionTUIAction
# ═══════════════════════════════════════════════════════════════

class TUI_ACTION:
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    SELECT = "select"
    DELETE = "delete"
    ARCHIVE = "archive"
    CREATE = "create"
    RENAME = "rename"
    SHOW_LINKS = "show_links"
    TOGGLE_ARCHIVED = "toggle_archived"
    TOGGLE_DELETED = "toggle_deleted"
    HELP = "help"
    QUIT = "quit"
    NOOP = "noop"


# ═══════════════════════════════════════════════════════════════
# SessionTUIController — 业务逻辑（可测试）
# ═══════════════════════════════════════════════════════════════

class SessionTUIController:
    """TUI 业务逻辑控制器。不包含任何终端 I/O。"""

    def __init__(self, state: SessionTUIState = None):
        self.state = state or SessionTUIState()
        self._mgr = None

    @property
    def mgr(self):
        if self._mgr is None:
            from session_manager import get_session_manager
            self._mgr = get_session_manager()
        return self._mgr

    def load_sessions(self) -> None:
        sessions = self.mgr.list_sessions(
            include_archived=self.state.include_archived,
            include_deleted=self.state.include_deleted,
        )
        curr = self.mgr.get_current_session()
        self.state.current_session_id = curr.session_id if curr else "default"
        self.state.sessions = [
            {
                "session_id": s.session_id,
                "title": s.title,
                "status": s.status,
                "memory_count": s.memory_count,
                "linked_count": len(s.linked_session_ids),
                "last_accessed_at": s.last_accessed_at,
                "is_current": s.session_id == self.state.current_session_id,
                "is_default": s.session_id == "default",
            }
            for s in sessions
        ]
        if self.state.selected_index >= len(self.state.sessions):
            self.state.selected_index = max(0, len(self.state.sessions) - 1)

    def move_up(self) -> str:
        self.state.message = ""
        if self.state.selected_index > 0:
            self.state.selected_index -= 1
        return TUI_ACTION.MOVE_UP

    def move_down(self) -> str:
        self.state.message = ""
        n = len(self.state.sessions)
        if n > 0 and self.state.selected_index < n - 1:
            self.state.selected_index += 1
        return TUI_ACTION.MOVE_DOWN

    def select(self) -> str:
        if not self.state.sessions:
            self.state.message = "No sessions available."
            return TUI_ACTION.NOOP
        sel = self.state.sessions[self.state.selected_index]
        if sel["status"] == "deleted":
            self.state.message = f"Deleted session cannot be used: {sel['session_id']}. Restore first."
            return TUI_ACTION.NOOP
        if sel["status"] == "archived":
            self.state.message = f"Archived session cannot be used: {sel['session_id']}. Restore first."
            return TUI_ACTION.NOOP
        self.mgr.set_current_session(sel["session_id"])
        self.state.current_session_id = sel["session_id"]
        self.state.message = f"Switched to {sel['session_id']} ({sel['title']})"
        self.load_sessions()
        return TUI_ACTION.SELECT

    def delete_selected(self) -> str:
        if not self.state.sessions:
            return TUI_ACTION.NOOP
        sel = self.state.sessions[self.state.selected_index]
        if sel["is_default"]:
            self.state.message = "Cannot delete default session."
            return TUI_ACTION.NOOP
        if self.state.mode != "confirm_delete":
            self.state.mode = "confirm_delete"
            self.state.message = f"Press Delete again to confirm deleting: {sel['title']} ({sel['session_id']})"
            return TUI_ACTION.DELETE
        self.state.mode = "list"
        self.mgr.delete_session(sel["session_id"])
        self.state.message = f"Soft deleted: {sel['session_id']} ({sel['title']})"
        if self.state.current_session_id == sel["session_id"]:
            curr = self.mgr.get_current_session()
            self.state.current_session_id = curr.session_id
        self.load_sessions()
        return TUI_ACTION.DELETE

    def archive_selected(self) -> str:
        if not self.state.sessions:
            return TUI_ACTION.NOOP
        sel = self.state.sessions[self.state.selected_index]
        if sel["is_default"]:
            self.state.message = "Cannot archive default session."
            return TUI_ACTION.NOOP
        self.mgr.archive_session(sel["session_id"])
        self.state.message = f"Archived: {sel['session_id']} ({sel['title']})"
        self.load_sessions()
        return TUI_ACTION.ARCHIVE

    def start_create(self) -> str:
        self.state.mode = "input_title"
        self.state.input_action = "create"
        self.state.input_buffer = ""
        self.state.input_prompt = "Enter new session title: "
        self.state.input_session_id = ""
        self.state.message = ""
        return TUI_ACTION.CREATE

    def start_rename(self) -> str:
        if not self.state.sessions:
            return TUI_ACTION.NOOP
        sel = self.state.sessions[self.state.selected_index]
        self.state.mode = "input_title"
        self.state.input_action = "rename"
        self.state.input_buffer = sel["title"]
        self.state.input_prompt = "Enter new title: "
        self.state.input_session_id = sel["session_id"]
        self.state.message = ""
        return TUI_ACTION.RENAME

    def confirm_input(self) -> str:
        title = self.state.input_buffer.strip()
        self.state.mode = "list"
        if not title:
            self.state.message = "Title cannot be empty. Cancelled."
            return TUI_ACTION.NOOP
        if self.state.input_action == "create":
            s = self.mgr.create_session(title=title)
            self.state.message = f"Created: {s.session_id} ({s.title})"
            self.load_sessions()
            return TUI_ACTION.CREATE
        elif self.state.input_action == "rename":
            sid = self.state.input_session_id
            self.mgr.rename_session(sid, title)
            self.state.message = f"Renamed: {sid} -> {title}"
            self.load_sessions()
            return TUI_ACTION.RENAME
        return TUI_ACTION.NOOP

    def cancel_input(self) -> str:
        self.state.mode = "list"
        self.state.message = "Cancelled."
        return TUI_ACTION.NOOP

    def show_links(self) -> str:
        if not self.state.sessions:
            return TUI_ACTION.NOOP
        sel = self.state.sessions[self.state.selected_index]
        linked = self.mgr.list_linked_sessions(sel["session_id"])
        if not linked:
            self.state.message = f"No linked sessions for: {sel['session_id']}"
        else:
            names = ", ".join(f"{s.session_id}({s.title})" for s in linked)
            self.state.message = f"Linked [{len(linked)}]: {names}"
        return TUI_ACTION.SHOW_LINKS

    def toggle_archived(self) -> str:
        self.state.include_archived = not self.state.include_archived
        self.state.selected_index = 0
        self.load_sessions()
        self.state.message = f"Show archived: {self.state.include_archived}"
        return TUI_ACTION.TOGGLE_ARCHIVED

    def toggle_deleted(self) -> str:
        self.state.include_deleted = not self.state.include_deleted
        self.state.selected_index = 0
        self.load_sessions()
        self.state.message = f"Show deleted: {self.state.include_deleted}"
        return TUI_ACTION.TOGGLE_DELETED

    # ── key → action mapping ──────────────────────────────

    def handle_key(self, key: str) -> str:
        """将按键字符串映射为 action。返回 action name。"""
        if self.state.mode == "confirm_delete":
            if key == "DELETE":
                return self.delete_selected()
            self.state.mode = "list"
            self.state.message = "Delete cancelled."
            return TUI_ACTION.NOOP

        if self.state.mode == "input_title":
            if key == "ENTER":
                return self.confirm_input()
            if key == "ESC":
                return self.cancel_input()
            if key == "BACKSPACE":
                self.state.input_buffer = self.state.input_buffer[:-1]
                return TUI_ACTION.NOOP
            if len(key) == 1 and key.isprintable():
                self.state.input_buffer += key
                return TUI_ACTION.NOOP
            return TUI_ACTION.NOOP

        # list mode
        mapping = {
            "UP": self.move_up,
            "DOWN": self.move_down,
            "ENTER": self.select,
            "DELETE": self.delete_selected,
            "n": self.start_create,
            "N": self.start_create,
            "r": self.start_rename,
            "R": self.start_rename,
            "a": self.archive_selected,
            "A": self.archive_selected,
            "l": self.show_links,
            "L": self.show_links,
            "h": self._show_help,
            "H": self._show_help,
            "?": self._show_help,
            "q": self._quit,
            "Q": self._quit,
            "ESC": self._quit,
            "v": self.toggle_archived,
            "V": self.toggle_archived,
            "d": self.toggle_deleted,
            "D": self.toggle_deleted,
        }
        fn = mapping.get(key, lambda: TUI_ACTION.NOOP)
        return fn()

    def _show_help(self) -> str:
        self.state.message = (
            "UP/DOWN:move ENTER:use DEL:delete N:new R:rename "
            "A:archive L:links V:show-archived D:show-deleted H:help Q:quit"
        )
        return TUI_ACTION.HELP

    def _quit(self) -> str:
        self.state.running = False
        return TUI_ACTION.QUIT


# ═══════════════════════════════════════════════════════════════
# SessionTUIRenderer — 纯文本渲染（可测试）
# ═══════════════════════════════════════════════════════════════

class SessionTUIRenderer:
    """纯文本渲染器。无终端依赖。"""

    @staticmethod
    def render(state: SessionTUIState) -> str:
        cols = shutil.get_terminal_size((120, 30))

        lines = []
        lines.append("—" * min(cols.columns, 80))
        lines.append("Session Workspace Manager — v0.7.0-dev")
        lines.append(f"Current: {state.current_session_id}  |  "
                     f"Showing: {len(state.sessions)} sessions")
        lines.append("")

        if state.mode == "input_title":
            lines.append(f"{state.input_prompt}{state.input_buffer}_")
            lines.append("Enter to confirm, Esc to cancel")
            if state.message:
                lines.append(f"\nMessage: {state.message}")
            return "\n".join(lines)

        if state.mode == "confirm_delete":
            lines.append(f"!!! {state.message} !!!")
            lines.append("Press any other key to cancel.")
            return "\n".join(lines)

        # Help line
        lines.append("UP/DOWN:move ENTER:use DEL:delete N:new R:rename "
                     "A:archive L:links V:archived D:deleted H:help Q:quit")
        lines.append("")

        # Session list
        if not state.sessions:
            lines.append("  (no sessions)")
        else:
            for i, s in enumerate(state.sessions):
                cursor = ">" if i == state.selected_index else " "
                bullet = "*" if s["is_current"] else " "
                def_tag = "[default]" if s["is_default"] else ""
                status_tag = f"[{s['status']}]" if s["status"] != "active" else ""
                line = (
                    f"{cursor} {bullet} "
                    f"{s['title'][:35]:35s} "
                    f"{status_tag:10s} "
                    f"mem:{s['memory_count']:>3d}  "
                    f"linked:{s['linked_count']:>2d}  "
                    f"{def_tag:10s}"
                )
                lines.append(line.rstrip())

        lines.append("")
        if state.message:
            lines.append(f"Message: {state.message}")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# 跨平台键盘输入
# ═══════════════════════════════════════════════════════════════

def _read_key_windows() -> str:
    """Windows: 使用 msvcrt 读取按键。"""
    import msvcrt
    ch = msvcrt.getch()
    if ch == b'\xe0':  # special key prefix
        ch2 = msvcrt.getch()
        if ch2 == b'H': return "UP"
        if ch2 == b'P': return "DOWN"
        if ch2 == b'S': return "DELETE"
        return "NOOP"
    if ch == b'\r' or ch == b'\n':
        return "ENTER"
    if ch == b'\x08':  # backspace
        return "BACKSPACE"
    if ch == b'\x1b':
        return "ESC"
    try:
        return ch.decode('utf-8', errors='replace')
    except Exception:
        return "NOOP"


def _read_key_unix() -> str:
    """Unix: 使用 termios 读取 ANSI escape。"""
    import termios
    import tty
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            seq = sys.stdin.read(2)
            if seq == '[A': return "UP"
            if seq == '[B': return "DOWN"
            if seq == '[3': return "DELETE"
            if seq == '\x1b':
                return "ESC"
            return "ESC"
        if ch == '\r' or ch == '\n':
            return "ENTER"
        if ch == '\x7f':
            return "BACKSPACE"
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def _read_key() -> str:
    """跨平台按键读取。返回 key name 或字符。"""
    if not sys.stdin.isatty():
        return "NO_TTY"
    if sys.platform == "win32":
        return _read_key_windows()
    try:
        return _read_key_unix()
    except (ImportError, AttributeError):
        return "NO_TTY"


# ═══════════════════════════════════════════════════════════════
# SessionTUI — 主入口
# ═══════════════════════════════════════════════════════════════

class SessionTUI:
    """交互式会话选择 TUI 入口。"""

    def __init__(
        self,
        session_root: str | Path | None = None,
        include_archived: bool = False,
        include_deleted: bool = False,
    ):
        state = SessionTUIState(
            include_archived=include_archived,
            include_deleted=include_deleted,
        )
        self.state = state
        self.controller = SessionTUIController(state)
        self.renderer = SessionTUIRenderer()
        if session_root:
            # Re-init mgr with custom root
            from session_manager import SessionManager
            import session_manager as sm
            sm._global_manager = None
            mgr = SessionManager(session_root=session_root)
            sm._global_manager = mgr

    def run(self) -> str:
        """运行交互式 TUI。返回 exit message。"""
        if not sys.stdin.isatty():
            return ("Terminal not available. "
                    "Use `memory:session list/use/delete` or "
                    "`python scripts/session_cli.py <action>` instead.")

        self.controller.load_sessions()
        self.state.running = True

        while self.state.running:
            # Render
            output = self.renderer.render(self.state)
            # Clear screen (cross-platform)
            sys.stdout.write("\033[2J\033[H")
            sys.stdout.write(output + "\n")
            sys.stdout.flush()

            # Read key
            key = _read_key()
            if key == "NO_TTY":
                self.state.running = False
                return "TTY lost. Exiting TUI."

            self.controller.handle_key(key)

        return f"TUI exited. Current session: {self.state.current_session_id}"


# ═══════════════════════════════════════════════════════════════
# 便捷调用
# ═══════════════════════════════════════════════════════════════

def run_session_tui(
    include_archived: bool = False,
    include_deleted: bool = False,
    session_root: str | Path | None = None,
) -> str:
    """启动交互式 Session TUI。返回 exit message。

    非交互环境下返回错误提示字符串。
    """
    tui = SessionTUI(
        session_root=session_root,
        include_archived=include_archived,
        include_deleted=include_deleted,
    )
    return tui.run()
