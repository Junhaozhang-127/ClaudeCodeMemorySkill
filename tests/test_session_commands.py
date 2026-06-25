"""
Session CLI Commands — Phase 2 测试套件 (v0.7.0)

覆盖:
  - TestSessionCommandRegistry: 命令注册 / alias / unknown
  - TestSessionCommandList: list 命令
  - TestSessionCommandCreate: create 命令
  - TestSessionCommandCurrent: current 命令
  - TestSessionCommandUse: use 命令
  - TestSessionCommandRename: rename 命令
  - TestSessionCommandArchive: archive 命令
  - TestSessionCommandDelete: delete 命令
  - TestSessionCommandRestore: restore 命令
  - TestSessionCommandInfo: info 命令
  - TestSessionCommandIntegration: 集成回归
  - TestSessionSlashCommand: manifest + .md 集成

运行:
    python -m pytest tests/test_session_commands.py -v
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

from session_manager import SessionManager, SessionStatus


# ═══════════════════════════════════════════════════════════════
# 测试基类
# ═══════════════════════════════════════════════════════════════

class IsolatedSessionCommandTest(unittest.TestCase):
    """每个测试使用独立的临时 session_root，通过 commands dispatch。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sescmd_"))
        self.session_root = self.tmp / "sessions"
        # Re-init global manager with isolated root
        import session_manager as sm
        sm._global_manager = None
        self.mgr = SessionManager(session_root=self.session_root)
        sm._global_manager = self.mgr
        # Reset command registry to pick up fresh manager
        import commands.registry as reg_module
        reg_module._global_registry = None

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)
        import session_manager as sm
        sm._global_manager = None

    def _dispatch(self, action: str, **kwargs) -> dict:
        """便捷 dispatch，返回 result dict。"""
        from commands.registry import get_registry
        reg = get_registry()
        kwargs["action"] = action
        result = reg.dispatch("memory:session", kwargs)
        return {
            "ok": result.ok,
            "message": result.message,
            "error": result.error,
            "data": result.data,
        }


# ═══════════════════════════════════════════════════════════════
# TestSessionCommandRegistry — 注册测试
# ═══════════════════════════════════════════════════════════════

class TestSessionCommandRegistry(unittest.TestCase):

    def test_session_command_registered(self):
        from commands.registry import get_registry
        reg = get_registry()
        cmd = reg.get("memory:session")
        self.assertIsNotNone(cmd, "memory:session 应已注册")
        self.assertIsNotNone(cmd.handler)

    def test_alias_session(self):
        from commands.registry import get_registry
        reg = get_registry()
        cmd = reg.get("session")
        self.assertIsNotNone(cmd, "session alias 应可用")
        self.assertEqual(cmd.name, "memory:session")

    def test_alias_sessions(self):
        from commands.registry import get_registry
        reg = get_registry()
        cmd = reg.get("sessions")
        self.assertIsNotNone(cmd, "sessions alias 应可用")

    def test_unknown_action_returns_error(self):
        from commands.registry import get_registry
        reg = get_registry()
        result = reg.dispatch("memory:session", {"action": "bogus_action"})
        self.assertFalse(result.ok)
        self.assertIn("未知", result.error)

    def test_help_contains_actions(self):
        from commands.registry import get_registry
        reg = get_registry()
        cmd = reg.get("memory:session")
        help_text = cmd.format_help()
        for action in ("list", "create", "current", "use",
                        "rename", "archive", "delete", "restore", "info"):
            self.assertIn(action, help_text,
                          f"help 应包含 {action}")


# ═══════════════════════════════════════════════════════════════
# TestSessionCommandList
# ═══════════════════════════════════════════════════════════════

class TestSessionCommandList(IsolatedSessionCommandTest):

    def test_list_default_shows_active(self):
        self.mgr.create_session("Alpha")
        self.mgr.create_session("Beta")
        result = self._dispatch("list")
        self.assertTrue(result["ok"])
        sessions = result["data"]["sessions"]
        self.assertGreaterEqual(len(sessions), 3)  # default + alpha + beta
        for s in sessions:
            self.assertEqual(s["status"], SessionStatus.ACTIVE)

    def test_list_includes_current_flag(self):
        s = self.mgr.create_session("Current Target")
        self.mgr.set_current_session(s.session_id)
        result = self._dispatch("list")
        sessions = result["data"]["sessions"]
        current = [s for s in sessions if s["is_current"]]
        self.assertEqual(len(current), 1)
        self.assertEqual(current[0]["session_id"], s.session_id)

    def test_list_include_archived(self):
        s = self.mgr.create_session("Archived One")
        self.mgr.archive_session(s.session_id)
        result = self._dispatch("list", include_archived=True)
        self.assertTrue(
            any(x["session_id"] == s.session_id for x in result["data"]["sessions"])
        )
        # 默认不含 archived
        result2 = self._dispatch("list")
        self.assertFalse(
            any(x["session_id"] == s.session_id for x in result2["data"]["sessions"])
        )

    def test_list_include_deleted(self):
        s = self.mgr.create_session("Deleted One")
        self.mgr.delete_session(s.session_id)
        result = self._dispatch("list", include_deleted=True)
        self.assertTrue(
            any(x["session_id"] == s.session_id for x in result["data"]["sessions"])
        )


# ═══════════════════════════════════════════════════════════════
# TestSessionCommandCreate
# ═══════════════════════════════════════════════════════════════

class TestSessionCommandCreate(IsolatedSessionCommandTest):

    def test_create_success(self):
        result = self._dispatch("create", title="Test Session",
                                description="Test desc", tags="a,b,c")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["title"], "Test Session")
        self.assertGreater(len(result["data"]["session_id"]), 0)

    def test_create_with_use(self):
        result = self._dispatch("create", title="Switch Session", use=True)
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["is_current"])
        curr = self.mgr.get_current_session()
        self.assertEqual(curr.session_id, result["data"]["session_id"])

    def test_create_title_required(self):
        result = self._dispatch("create")
        self.assertFalse(result["ok"])
        self.assertIn("title", result["error"])

    def test_create_creates_files(self):
        result = self._dispatch("create", title="File Check")
        session_dir = self.session_root / result["data"]["session_id"]
        self.assertTrue((session_dir / "manifest.json").exists())
        self.assertTrue((session_dir / "trash").is_dir())


# ═══════════════════════════════════════════════════════════════
# TestSessionCommandCurrent
# ═══════════════════════════════════════════════════════════════

class TestSessionCommandCurrent(IsolatedSessionCommandTest):

    def test_current_returns_default(self):
        result = self._dispatch("current")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["session_id"], "default")

    def test_current_has_path(self):
        result = self._dispatch("current")
        self.assertIn("path", result["data"])


# ═══════════════════════════════════════════════════════════════
# TestSessionCommandUse
# ═══════════════════════════════════════════════════════════════

class TestSessionCommandUse(IsolatedSessionCommandTest):

    def test_use_active_session(self):
        s = self.mgr.create_session("Switch Target")
        result = self._dispatch("use", session_id=s.session_id)
        self.assertTrue(result["ok"])
        self.assertEqual(self.mgr.get_current_session().session_id, s.session_id)

    def test_use_deleted_fails(self):
        s = self.mgr.create_session("To Delete")
        self.mgr.delete_session(s.session_id)
        result = self._dispatch("use", session_id=s.session_id)
        self.assertFalse(result["ok"])
        self.assertIn("删除", result["error"])

    def test_use_archived_fails_by_default(self):
        s = self.mgr.create_session("Archived Switch")
        self.mgr.archive_session(s.session_id)
        result = self._dispatch("use", session_id=s.session_id)
        self.assertFalse(result["ok"])

    def test_use_archived_with_flag(self):
        s = self.mgr.create_session("Archived Allow")
        self.mgr.archive_session(s.session_id)
        result = self._dispatch("use", session_id=s.session_id,
                                allow_archived=True)
        self.assertTrue(result["ok"])

    def test_use_nonexistent_fails(self):
        result = self._dispatch("use", session_id="nope")
        self.assertFalse(result["ok"])


# ═══════════════════════════════════════════════════════════════
# TestSessionCommandRename
# ═══════════════════════════════════════════════════════════════

class TestSessionCommandRename(IsolatedSessionCommandTest):

    def test_rename_success(self):
        s = self.mgr.create_session("Old Name")
        result = self._dispatch("rename", session_id=s.session_id,
                                title="New Name")
        self.assertTrue(result["ok"])
        updated = self.mgr.get_session(s.session_id)
        self.assertEqual(updated.title, "New Name")


# ═══════════════════════════════════════════════════════════════
# TestSessionCommandArchive
# ═══════════════════════════════════════════════════════════════

class TestSessionCommandArchive(IsolatedSessionCommandTest):

    def test_archive_success(self):
        s = self.mgr.create_session("To Archive")
        result = self._dispatch("archive", session_id=s.session_id)
        self.assertTrue(result["ok"])
        self.assertEqual(self.mgr.get_session(s.session_id).status,
                         SessionStatus.ARCHIVED)

    def test_archive_default_fails(self):
        result = self._dispatch("archive", session_id="default")
        self.assertFalse(result["ok"])


# ═══════════════════════════════════════════════════════════════
# TestSessionCommandDelete
# ═══════════════════════════════════════════════════════════════

class TestSessionCommandDelete(IsolatedSessionCommandTest):

    def test_delete_is_soft(self):
        s = self.mgr.create_session("Soft Delete")
        result = self._dispatch("delete", session_id=s.session_id)
        self.assertTrue(result["ok"])
        # 目录仍存在
        self.assertTrue((self.session_root / s.session_id).exists())
        self.assertIn("软删除", result["message"])

    def test_delete_default_fails(self):
        result = self._dispatch("delete", session_id="default")
        self.assertFalse(result["ok"])

    def test_delete_current_falls_back(self):
        s = self.mgr.create_session("Current To Delete")
        self.mgr.set_current_session(s.session_id)
        result = self._dispatch("delete", session_id=s.session_id)
        self.assertTrue(result["ok"])
        # 当前会话应回退到 default
        curr = self.mgr.get_current_session()
        self.assertEqual(curr.session_id, "default")


# ═══════════════════════════════════════════════════════════════
# TestSessionCommandRestore
# ═══════════════════════════════════════════════════════════════

class TestSessionCommandRestore(IsolatedSessionCommandTest):

    def test_restore_success(self):
        s = self.mgr.create_session("Restore Me")
        self.mgr.delete_session(s.session_id)
        result = self._dispatch("restore", session_id=s.session_id)
        self.assertTrue(result["ok"])
        self.assertEqual(self.mgr.get_session(s.session_id).status,
                         SessionStatus.ACTIVE)

    def test_restore_with_use(self):
        s = self.mgr.create_session("Restore Use")
        self.mgr.delete_session(s.session_id)
        result = self._dispatch("restore", session_id=s.session_id, use=True)
        self.assertTrue(result["ok"])
        self.assertTrue(result["data"]["is_current"])


# ═══════════════════════════════════════════════════════════════
# TestSessionCommandInfo
# ═══════════════════════════════════════════════════════════════

class TestSessionCommandInfo(IsolatedSessionCommandTest):

    def test_info_current_when_no_id(self):
        result = self._dispatch("info")
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["session_id"], "default")
        self.assertIn("path", result["data"])
        self.assertIn("files", result["data"])
        self.assertIn("events_count", result["data"])

    def test_info_by_id(self):
        s = self.mgr.create_session("Inspect Me")
        result = self._dispatch("info", session_id=s.session_id)
        self.assertTrue(result["ok"])
        self.assertEqual(result["data"]["title"], "Inspect Me")
        self.assertIn("manifest.json", result["data"]["files"])

    def test_info_nonexistent(self):
        result = self._dispatch("info", session_id="nope")
        self.assertFalse(result["ok"])


# ═══════════════════════════════════════════════════════════════
# TestSessionCommandIntegration — 回归
# ═══════════════════════════════════════════════════════════════

class TestSessionCommandIntegration(unittest.TestCase):
    """验证 session command 不破坏现有命令。"""

    def setUp(self):
        import commands.registry as reg_module
        reg_module._global_registry = None

    def test_existing_commands_still_work(self):
        from commands.registry import get_registry
        reg = get_registry()
        for name in ("memory:save", "memory:retrieve",
                     "memory:rebuild", "memory:manage"):
            cmd = reg.get(name)
            self.assertIsNotNone(cmd, f"{name} 应仍已注册")

    def test_all_five_commands_in_manifest(self):
        manifest = json.loads(
            (PROJECT_ROOT / ".claude-plugin" / "plugin.json")
            .read_text(encoding="utf-8")
        )
        cmds = manifest.get("commands", {})
        for name in ("memory:save", "memory:retrieve", "memory:rebuild",
                     "memory:manage", "memory:session"):
            self.assertIn(name, cmds, f"manifest 缺少: {name}")

    def test_registry_matches_manifest(self):
        from commands.registry import get_registry
        manifest = json.loads(
            (PROJECT_ROOT / ".claude-plugin" / "plugin.json")
            .read_text(encoding="utf-8")
        )
        manifest_cmds = set(manifest.get("commands", {}).keys())
        reg = get_registry()
        reg_cmds = {c.name for c in reg.list_all()}
        for mc in manifest_cmds:
            self.assertIn(mc, reg_cmds,
                          f"manifest 命令 {mc} 未在 registry 注册")


# ═══════════════════════════════════════════════════════════════
# TestSessionSlashCommand — slash command 声明文件 + manifest
# ═══════════════════════════════════════════════════════════════

class TestSessionSlashCommand(unittest.TestCase):

    def test_session_md_exists(self):
        path = PROJECT_ROOT / "commands" / "session.md"
        self.assertTrue(path.exists(), "commands/session.md 缺失")

    def test_session_md_has_frontmatter(self):
        path = PROJECT_ROOT / "commands" / "session.md"
        content = path.read_text(encoding="utf-8")
        self.assertIn("---", content, "session.md 应包含 YAML frontmatter")
        self.assertIn("memory:session", content)

    def test_cli_script_exists(self):
        path = PROJECT_ROOT / "scripts" / "session_cli.py"
        self.assertTrue(path.exists(), "scripts/session_cli.py 缺失")

    def test_cli_script_syntax_valid(self):
        """验证 CLI 脚本语法合法（import 不崩溃）。"""
        path = PROJECT_ROOT / "scripts" / "session_cli.py"
        import importlib.util
        spec = importlib.util.spec_from_file_location("session_cli", str(path))
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except SystemExit:
            pass  # argparse 可能触发 sys.exit(0)
        # 验证 main 函数存在
        self.assertTrue(callable(mod.main), "CLI 脚本应包含 main() 函数")


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    unittest.main(verbosity=2)
