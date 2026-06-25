"""
Session TUI — Phase 5 测试套件 (v0.7.0)

测试 Controller / Renderer / Key Mapping / Command / CLI，不启动真实 TUI。

运行:
    python -m pytest tests/test_session_tui.py -v
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from session_tui import (
    SessionTUIState, SessionTUIController, SessionTUIRenderer,
    TUI_ACTION, run_session_tui,
)
from session_manager import SessionManager, SessionStatus


# ═══════════════════════════════════════════════════════════════
# Test Helpers
# ═══════════════════════════════════════════════════════════════

def _setup_isolated():
    tmp = Path(tempfile.mkdtemp(prefix="tuitest_"))
    sr = tmp / "sessions"
    import session_manager as sm
    sm._global_manager = None
    mgr = SessionManager(session_root=sr)
    sm._global_manager = mgr
    return tmp, sr, mgr


def _teardown_isolated(tmp):
    shutil.rmtree(str(tmp), ignore_errors=True)
    import session_manager as sm
    sm._global_manager = None


# ═══════════════════════════════════════════════════════════════
# TestTUIStateAndController
# ═══════════════════════════════════════════════════════════════

class TestTUIStateAndController(unittest.TestCase):

    def setUp(self):
        self.tmp, self.sr, self.mgr = _setup_isolated()
        self.state = SessionTUIState()
        self.ctrl = SessionTUIController(self.state)

    def tearDown(self):
        _teardown_isolated(self.tmp)

    def test_load_sessions_has_default(self):
        self.ctrl.load_sessions()
        self.assertGreaterEqual(len(self.state.sessions), 1)
        self.assertEqual(self.state.sessions[0]["session_id"], "default")

    def test_selected_index_defaults_to_zero(self):
        self.ctrl.load_sessions()
        self.assertEqual(self.state.selected_index, 0)

    def test_move_down_not_out_of_bounds(self):
        self.ctrl.load_sessions()
        n = len(self.state.sessions)
        for _ in range(n + 5):
            self.ctrl.move_down()
        self.assertLess(self.state.selected_index, n)

    def test_move_up_not_out_of_bounds(self):
        self.ctrl.load_sessions()
        self.state.selected_index = 0
        self.ctrl.move_up()
        self.assertEqual(self.state.selected_index, 0)

    def test_select_active_session(self):
        sid = self.mgr.create_session("Target").session_id
        self.ctrl.load_sessions()
        # Find the Target session index
        for i, s in enumerate(self.state.sessions):
            if s["session_id"] == sid:
                self.state.selected_index = i
                break
        action = self.ctrl.select()
        self.assertEqual(action, TUI_ACTION.SELECT)
        self.assertEqual(self.state.current_session_id, sid)

    def test_select_archived_fails(self):
        sid = self.mgr.create_session("ArchSelect").session_id
        self.mgr.archive_session(sid)
        self.state.include_archived = True
        self.ctrl.load_sessions()
        for i, s in enumerate(self.state.sessions):
            if s["session_id"] == sid:
                self.state.selected_index = i
                break
        action = self.ctrl.select()
        self.assertEqual(action, TUI_ACTION.NOOP)
        self.assertIn("Archived", self.state.message)

    def test_delete_is_soft(self):
        sid = self.mgr.create_session("DelTest").session_id
        self.ctrl.load_sessions()
        for i, s in enumerate(self.state.sessions):
            if s["session_id"] == sid:
                self.state.selected_index = i
                break
        # First press: confirm mode
        self.ctrl.delete_selected()
        self.assertEqual(self.state.mode, "confirm_delete")
        # Second press: actually delete
        self.ctrl.delete_selected()
        manifest = self.mgr.get_session(sid)
        self.assertEqual(manifest.status, SessionStatus.DELETED)

    def test_delete_default_denied(self):
        self.ctrl.load_sessions()
        for i, s in enumerate(self.state.sessions):
            if s["session_id"] == "default":
                self.state.selected_index = i
                break
        self.ctrl.delete_selected()
        self.assertIn("Cannot delete default", self.state.message)

    def test_delete_current_session_falls_back(self):
        sid = self.mgr.create_session("CurrDel").session_id
        self.mgr.set_current_session(sid)
        self.ctrl.load_sessions()
        for i, s in enumerate(self.state.sessions):
            if s["session_id"] == sid:
                self.state.selected_index = i
                break
        self.ctrl.delete_selected()
        self.ctrl.delete_selected()
        curr = self.mgr.get_current_session()
        self.assertEqual(curr.session_id, "default")

    def test_archive_default_denied(self):
        self.ctrl.load_sessions()
        for i, s in enumerate(self.state.sessions):
            if s["session_id"] == "default":
                self.state.selected_index = i
                break
        self.ctrl.archive_selected()
        self.assertIn("Cannot archive default", self.state.message)

    def test_archive_selected_succeeds(self):
        sid = self.mgr.create_session("ArchTest").session_id
        self.ctrl.load_sessions()
        for i, s in enumerate(self.state.sessions):
            if s["session_id"] == sid:
                self.state.selected_index = i
                break
        action = self.ctrl.archive_selected()
        self.assertEqual(action, TUI_ACTION.ARCHIVE)
        self.assertEqual(self.mgr.get_session(sid).status, SessionStatus.ARCHIVED)

    def test_create_session(self):
        self.state.mode = "input_title"
        self.state.input_action = "create"
        self.state.input_buffer = "TUI Created"
        action = self.ctrl.confirm_input()
        self.assertEqual(action, TUI_ACTION.CREATE)
        self.assertEqual(self.state.mode, "list")

    def test_create_empty_title_cancelled(self):
        self.state.mode = "input_title"
        self.state.input_action = "create"
        self.state.input_buffer = "  "
        action = self.ctrl.confirm_input()
        self.assertEqual(action, TUI_ACTION.NOOP)

    def test_rename_session(self):
        sid = self.mgr.create_session("OldName").session_id
        self.state.mode = "input_title"
        self.state.input_action = "rename"
        self.state.input_session_id = sid
        self.state.input_buffer = "NewName"
        action = self.ctrl.confirm_input()
        self.assertEqual(action, TUI_ACTION.RENAME)
        self.assertEqual(self.mgr.get_session(sid).title, "NewName")

    def test_show_links_empty(self):
        self.ctrl.load_sessions()
        self.ctrl.show_links()
        self.assertIn("No linked sessions", self.state.message)

    def test_show_links_with_data(self):
        tgt = self.mgr.create_session("LinkTgt").session_id
        self.mgr.link_session("default", tgt)
        self.ctrl.load_sessions()
        for i, s in enumerate(self.state.sessions):
            if s["session_id"] == "default":
                self.state.selected_index = i
                break
        self.ctrl.show_links()
        self.assertIn("LinkTgt", self.state.message)

    def test_toggle_archived(self):
        was = self.state.include_archived
        self.ctrl.toggle_archived()
        self.assertNotEqual(was, self.state.include_archived)

    def test_refresh_keeps_index_valid(self):
        self.ctrl.load_sessions()
        self.state.selected_index = len(self.state.sessions) - 1
        self.mgr.create_session("NewSess")
        self.ctrl.load_sessions()
        self.assertLess(self.state.selected_index, len(self.state.sessions))

    def test_help_sets_message(self):
        self.ctrl._show_help()
        self.assertIn("UP", self.state.message)

    def test_quit_stops_running(self):
        self.state.running = True
        action = self.ctrl._quit()
        self.assertEqual(action, TUI_ACTION.QUIT)
        self.assertFalse(self.state.running)


# ═══════════════════════════════════════════════════════════════
# TestTUIKeyMapping
# ═══════════════════════════════════════════════════════════════

class TestTUIKeyMapping(unittest.TestCase):

    def setUp(self):
        self.tmp, self.sr, self.mgr = _setup_isolated()
        self.state = SessionTUIState()
        self.ctrl = SessionTUIController(self.state)
        self.ctrl.load_sessions()

    def tearDown(self):
        _teardown_isolated(self.tmp)

    def test_up_key(self):
        self.state.selected_index = 1
        action = self.ctrl.handle_key("UP")
        self.assertEqual(action, TUI_ACTION.MOVE_UP)
        self.assertEqual(self.state.selected_index, 0)

    def test_down_key(self):
        action = self.ctrl.handle_key("DOWN")
        self.assertEqual(action, TUI_ACTION.MOVE_DOWN)

    def test_enter_maps_select(self):
        action = self.ctrl.handle_key("ENTER")
        self.assertEqual(action, TUI_ACTION.SELECT)

    def test_delete_maps_delete(self):
        # Non-default session
        sid = self.mgr.create_session("DelKey").session_id
        self.ctrl.load_sessions()
        for i, s in enumerate(self.state.sessions):
            if s["session_id"] == sid:
                self.state.selected_index = i
                break
        self.ctrl.handle_key("DELETE")
        self.ctrl.handle_key("DELETE")
        self.assertEqual(self.mgr.get_session(sid).status, SessionStatus.DELETED)

    def test_n_maps_create(self):
        self.ctrl.handle_key("N")
        self.assertEqual(self.state.mode, "input_title")
        self.assertEqual(self.state.input_action, "create")

    def test_r_maps_rename(self):
        self.ctrl.handle_key("R")
        self.assertEqual(self.state.mode, "input_title")
        self.assertEqual(self.state.input_action, "rename")

    def test_a_maps_archive(self):
        sid = self.mgr.create_session("ArchKey").session_id
        self.ctrl.load_sessions()
        for i, s in enumerate(self.state.sessions):
            if s["session_id"] == sid:
                self.state.selected_index = i
                break
        self.ctrl.handle_key("A")
        self.assertEqual(self.mgr.get_session(sid).status, SessionStatus.ARCHIVED)

    def test_l_maps_links(self):
        self.ctrl.handle_key("L")
        self.assertIn("No linked", self.state.message)

    def test_h_maps_help(self):
        self.ctrl.handle_key("H")
        self.assertIn("UP", self.state.message)

    def test_q_maps_quit(self):
        self.state.running = True
        self.ctrl.handle_key("Q")
        self.assertFalse(self.state.running)

    def test_unknown_key_maps_noop(self):
        action = self.ctrl.handle_key("ZZZ_UNKNOWN")
        self.assertEqual(action, TUI_ACTION.NOOP)


# ═══════════════════════════════════════════════════════════════
# TestTUIRenderer
# ═══════════════════════════════════════════════════════════════

class TestTUIRenderer(unittest.TestCase):

    def setUp(self):
        self.state = SessionTUIState()
        self.renderer = SessionTUIRenderer()

    def _load_fake_sessions(self):
        self.state.sessions = [
            {"session_id": "default", "title": "Default Session",
             "status": "active", "memory_count": 10, "linked_count": 1,
             "last_accessed_at": "2026-06-25 12:00:00",
             "is_current": True, "is_default": True},
            {"session_id": "abc", "title": "Project Alpha",
             "status": "active", "memory_count": 25, "linked_count": 2,
             "last_accessed_at": "2026-06-24 12:00:00",
             "is_current": False, "is_default": False},
            {"session_id": "xyz", "title": "Old Archive",
             "status": "archived", "memory_count": 5, "linked_count": 0,
             "last_accessed_at": "2026-05-01 12:00:00",
             "is_current": False, "is_default": False},
        ]
        self.state.current_session_id = "default"

    def test_render_has_title(self):
        output = self.renderer.render(self.state)
        self.assertIn("Session Workspace Manager", output)

    def test_render_shows_current(self):
        self._load_fake_sessions()
        output = self.renderer.render(self.state)
        self.assertIn("*", output)  # current bullet

    def test_render_shows_selected(self):
        self._load_fake_sessions()
        self.state.selected_index = 1
        output = self.renderer.render(self.state)
        lines = output.split("\n")
        has_cursor = any(">  " in l and "Project Alpha" in l for l in lines)
        self.assertTrue(has_cursor)

    def test_render_shows_memory_count(self):
        self._load_fake_sessions()
        output = self.renderer.render(self.state)
        self.assertIn("mem:", output)

    def test_render_shows_linked_count(self):
        self._load_fake_sessions()
        output = self.renderer.render(self.state)
        self.assertIn("linked:", output)

    def test_render_shows_archived_status(self):
        self._load_fake_sessions()
        output = self.renderer.render(self.state)
        self.assertIn("[archived]", output)

    def test_render_shows_help_line(self):
        output = self.renderer.render(self.state)
        self.assertIn("UP", output)

    def test_render_empty_sessions(self):
        output = self.renderer.render(self.state)
        self.assertIn("(no sessions)", output)

    def test_render_input_mode(self):
        self.state.mode = "input_title"
        self.state.input_prompt = "Title: "
        self.state.input_buffer = "My Session"
        output = self.renderer.render(self.state)
        self.assertIn("My Session", output)

    def test_render_confirm_delete_mode(self):
        self.state.mode = "confirm_delete"
        self.state.message = "Press Delete again to confirm"
        output = self.renderer.render(self.state)
        self.assertIn("confirm", output)


# ═══════════════════════════════════════════════════════════════
# TestTUICommandAndCLI
# ═══════════════════════════════════════════════════════════════

class TestTUICommandAndCLI(unittest.TestCase):

    def setUp(self):
        self.tmp, self.sr, self.mgr = _setup_isolated()

    def tearDown(self):
        _teardown_isolated(self.tmp)

    def test_tui_command_non_interactive_returns_error(self):
        from commands.memory_session import _do_tui
        result = _do_tui({})
        self.assertFalse(result.ok)
        self.assertIn("terminal", result.error.lower())

    def test_tui_command_registered(self):
        from commands.registry import get_registry
        reg = get_registry()
        cmd = reg.get("memory:session")
        self.assertIsNotNone(cmd, "memory:session command should be registered")
        self.assertIsNotNone(cmd.handler, "handler should exist")
        # Dispatch tui should work (returns error in non-TTY)
        r = cmd.handler({"action": "tui"})
        self.assertFalse(r.ok)  # non-TTY
        self.assertIn("terminal", r.error.lower())

    def test_cli_tui_help_parsable(self):
        import subprocess
        path = PROJECT_ROOT / "scripts" / "session_cli.py"
        r = subprocess.run(
            [sys.executable, str(path), "tui", "--help"],
            capture_output=True, text=True,
            cwd=str(PROJECT_ROOT), timeout=10,
        )
        self.assertIn("include", r.stdout.lower())

    def test_existing_commands_unaffected(self):
        from commands.registry import get_registry
        reg = get_registry()
        for name in ("memory:save", "memory:retrieve", "memory:manage"):
            self.assertIsNotNone(reg.get(name))

    def test_run_session_tui_non_tty_returns_message(self):
        # force non-TTY by patching isatty
        import session_tui
        original = sys.stdin.isatty
        try:
            sys.stdin.isatty = lambda: False
            msg = run_session_tui()
            self.assertIn("Terminal not available", msg)
        finally:
            sys.stdin.isatty = original


# ═══════════════════════════════════════════════════════════════
class TestTUIRegression(unittest.TestCase):

    def test_module_importable(self):
        import session_tui
        self.assertTrue(hasattr(session_tui, "SessionTUI"))
        self.assertTrue(hasattr(session_tui, "SessionTUIController"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
