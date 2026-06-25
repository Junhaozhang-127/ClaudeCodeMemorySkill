"""
Session Workspace Manager — Phase 1 完整测试套件 (v0.7.0)

覆盖:
  - TestSessionManifest: 数据类序列化/反序列化
  - TestSessionIndex: 索引加载/保存/损坏恢复
  - TestSessionManagerCore: 创建/列表/获取/重命名
  - TestCurrentSession: 当前会话设置/获取/回退
  - TestSessionSoftDelete: 软删除/恢复/回退
  - TestSessionEvents: 事件日志
  - TestDefaultSession: 默认会话规则

运行:
    python -m pytest tests/test_session_manager.py -v
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

# 添加 scripts/ 到 path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from session_manager import (
    SessionStatus,
    SessionManifest,
    SessionIndex,
    CurrentSession,
    SessionEvent,
    SessionManager,
    _now,
    _generate_session_id,
)


# ═══════════════════════════════════════════════════════════════
# 测试隔离基类
# ═══════════════════════════════════════════════════════════════

class IsolatedSessionTest(unittest.TestCase):
    """每个测试使用独立的临时 session_root。"""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sesstest_"))
        self.session_root = self.tmp / "sessions"
        self.mgr = SessionManager(session_root=self.session_root)

    def tearDown(self):
        shutil.rmtree(str(self.tmp), ignore_errors=True)

    def _read_index(self) -> SessionIndex:
        return self.mgr._load_index()

    def _read_current(self) -> CurrentSession:
        return self.mgr._load_current()


# ═══════════════════════════════════════════════════════════════
# TestSessionManifest — 数据类测试
# ═══════════════════════════════════════════════════════════════

class TestSessionManifest(unittest.TestCase):
    """SessionManifest 序列化/反序列化测试。"""

    def test_to_dict_and_back(self):
        m = SessionManifest(
            session_id="test-123",
            title="Test Session",
            description="A test",
            tags=["test", "demo"],
            status=SessionStatus.ACTIVE,
            created_at="2026-01-01 12:00:00",
            updated_at="2026-01-02 12:00:00",
        )
        d = m.to_dict()
        m2 = SessionManifest.from_dict(d)
        self.assertEqual(m.session_id, m2.session_id)
        self.assertEqual(m.title, m2.title)
        self.assertEqual(m.description, m2.description)
        self.assertEqual(m.tags, m2.tags)
        self.assertEqual(m.status, m2.status)

    def test_from_dict_minimal(self):
        """最小字典也能正常解析（缺失字段用默认值）。"""
        m = SessionManifest.from_dict({
            "session_id": "minimal",
            "title": "Minimal",
        })
        self.assertEqual(m.session_id, "minimal")
        self.assertEqual(m.title, "Minimal")
        self.assertEqual(m.status, SessionStatus.ACTIVE)
        self.assertEqual(m.tags, [])
        self.assertEqual(m.description, "")

    def test_all_fields_roundtrip(self):
        m = SessionManifest(
            session_id="full-test",
            title="Full",
            description="desc",
            tags=["a", "b"],
            status=SessionStatus.ARCHIVED,
            created_at="2026-06-01 00:00:00",
            updated_at="2026-06-02 00:00:00",
            last_accessed_at="2026-06-03 00:00:00",
            memory_count=42,
            summary_count=7,
            linked_session_ids=["other-1", "other-2"],
            metadata={"key": "value"},
        )
        d = m.to_dict()
        m2 = SessionManifest.from_dict(d)
        self.assertEqual(m.session_id, m2.session_id)
        self.assertEqual(m.memory_count, m2.memory_count)
        self.assertEqual(m.summary_count, m2.summary_count)
        self.assertEqual(m.linked_session_ids, m2.linked_session_ids)
        self.assertEqual(m.metadata, m2.metadata)
        self.assertEqual(m.status, SessionStatus.ARCHIVED)


# ═══════════════════════════════════════════════════════════════
# TestSessionIndex — 索引测试
# ═══════════════════════════════════════════════════════════════

class TestSessionIndex(unittest.TestCase):
    """SessionIndex 序列化/反序列化测试。"""

    def test_empty_index(self):
        idx = SessionIndex()
        d = idx.to_dict()
        self.assertEqual(d["version"], "0.7.0")
        self.assertEqual(d["sessions"], [])

    def test_with_sessions(self):
        m = SessionManifest(session_id="s1", title="Session 1")
        idx = SessionIndex(sessions=[m], version="0.7.0")
        d = idx.to_dict()
        idx2 = SessionIndex.from_dict(d)
        self.assertEqual(len(idx2.sessions), 1)
        self.assertEqual(idx2.sessions[0].title, "Session 1")

    def test_corrupt_session_skipped(self):
        """损坏的 session 条目应跳过，不崩溃。"""
        data = {
            "version": "0.7.0",
            "sessions": [
                {"session_id": "good", "title": "Good"},
                {"bad": "entry"},  # 缺少必需字段
                {"session_id": "also_good", "title": "Also Good"},
            ],
        }
        idx = SessionIndex.from_dict(data)
        self.assertEqual(len(idx.sessions), 2)
        self.assertEqual(idx.sessions[0].session_id, "good")
        self.assertEqual(idx.sessions[1].session_id, "also_good")


# ═══════════════════════════════════════════════════════════════
# TestSessionManagerCore — 核心操作测试
# ═══════════════════════════════════════════════════════════════

class TestSessionManagerCore(IsolatedSessionTest):
    """SessionManager 核心 CRUD 测试。"""

    def test_init_creates_default_session(self):
        """空目录初始化应自动创建 default session。"""
        idx = self._read_index()
        sessions = idx.sessions
        self.assertGreaterEqual(len(sessions), 1)
        self.assertEqual(sessions[0].session_id, "default")
        self.assertEqual(sessions[0].title, "Default Session")
        self.assertEqual(sessions[0].status, SessionStatus.ACTIVE)

    def test_init_creates_index_file(self):
        self.assertTrue(
            (self.session_root / "index.json").exists(),
            "初始化应创建 index.json"
        )

    def test_create_session_creates_full_directory(self):
        s = self.mgr.create_session("My Session", "Description", ["tag1"])
        session_dir = self.session_root / s.session_id
        self.assertTrue(session_dir.exists())
        for fname in ["manifest.json", "memories.jsonl", "summaries.jsonl",
                       "embeddings.jsonl", "links.json", "events.jsonl"]:
            self.assertTrue(
                (session_dir / fname).exists(),
                f"create_session 应创建 {fname}"
            )
        self.assertTrue((session_dir / "trash").is_dir())

    def test_create_session_manifest_content(self):
        s = self.mgr.create_session("Project Alpha", "Alpha workspace", ["alpha"])
        self.assertEqual(s.title, "Project Alpha")
        self.assertEqual(s.description, "Alpha workspace")
        self.assertEqual(s.tags, ["alpha"])
        self.assertEqual(s.status, SessionStatus.ACTIVE)
        self.assertEqual(s.memory_count, 0)
        self.assertEqual(s.linked_session_ids, [])
        self.assertGreater(len(s.session_id), 0)
        self.assertNotEqual(s.session_id, "default")

    def test_create_session_adds_to_index(self):
        s = self.mgr.create_session("Indexed")
        idx = self._read_index()
        self.assertTrue(any(x.session_id == s.session_id for x in idx.sessions))

    def test_list_sessions_default_active(self):
        self.mgr.create_session("Active 1")
        self.mgr.create_session("Active 2")
        sessions = self.mgr.list_sessions()
        # default + 2 active = 3
        self.assertEqual(len(sessions), 3)
        for s in sessions:
            self.assertEqual(s.status, SessionStatus.ACTIVE)

    def test_list_sessions_include_archived(self):
        s = self.mgr.create_session("To Archive")
        self.mgr.archive_session(s.session_id)
        all_s = self.mgr.list_sessions(include_archived=True)
        self.assertTrue(any(x.session_id == s.session_id and
                           x.status == SessionStatus.ARCHIVED for x in all_s))
        # 不包含 archived
        active = self.mgr.list_sessions(include_archived=False)
        self.assertFalse(any(x.session_id == s.session_id for x in active))

    def test_list_sessions_include_deleted(self):
        s = self.mgr.create_session("To Delete")
        self.mgr.delete_session(s.session_id)
        all_s = self.mgr.list_sessions(include_deleted=True)
        self.assertTrue(any(x.session_id == s.session_id and
                           x.status == SessionStatus.DELETED for x in all_s))
        # 默认不含 deleted
        active = self.mgr.list_sessions(include_deleted=False)
        self.assertFalse(any(x.session_id == s.session_id for x in active))

    def test_get_session_found(self):
        s = self.mgr.create_session("Find Me")
        found = self.mgr.get_session(s.session_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.title, "Find Me")

    def test_get_session_not_found(self):
        self.assertIsNone(self.mgr.get_session("nonexistent-id"))

    def test_rename_session(self):
        s = self.mgr.create_session("Old Name")
        renamed = self.mgr.rename_session(s.session_id, "New Name")
        self.assertEqual(renamed.title, "New Name")
        # 验证 manifest 文件
        manifest_path = self.session_root / s.session_id / "manifest.json"
        saved = SessionManifest.from_dict(
            json.loads(manifest_path.read_text(encoding="utf-8"))
        )
        self.assertEqual(saved.title, "New Name")

    def test_rename_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.mgr.rename_session("nope", "Title")

    def test_get_session_path(self):
        s = self.mgr.create_session("Path Test")
        p = self.mgr.get_session_path(s.session_id)
        self.assertEqual(p.name, s.session_id)
        self.assertTrue(p.exists())

    def test_corrupt_index_recovered(self):
        """损坏的 index.json 应被备份并重建，不崩溃。"""
        idx_path = self.session_root / "index.json"
        idx_path.write_text("{bad json!!!", encoding="utf-8")
        mgr2 = SessionManager(session_root=self.session_root)
        sessions = mgr2.list_sessions()
        self.assertGreaterEqual(len(sessions), 1)
        self.assertEqual(sessions[0].session_id, "default")
        # 应有 .corrupt 备份文件
        corrupt_files = list(self.session_root.glob("index.corrupt.*.json"))
        self.assertGreaterEqual(len(corrupt_files), 1)


# ═══════════════════════════════════════════════════════════════
# TestCurrentSession — 当前会话测试
# ═══════════════════════════════════════════════════════════════

class TestCurrentSession(IsolatedSessionTest):
    """当前会话设置/获取/回退测试。"""

    def test_default_is_current(self):
        curr = self.mgr.get_current_session()
        self.assertEqual(curr.session_id, "default")
        self.assertEqual(curr.title, "Default Session")

    def test_set_current_session(self):
        s = self.mgr.create_session("Current Target")
        self.mgr.set_current_session(s.session_id)
        curr = self.mgr.get_current_session()
        self.assertEqual(curr.session_id, s.session_id)

    def test_set_current_nonexistent_raises(self):
        with self.assertRaises(ValueError):
            self.mgr.set_current_session("nope")

    def test_set_current_deleted_raises(self):
        s = self.mgr.create_session("To Current")
        self.mgr.delete_session(s.session_id)
        with self.assertRaises(ValueError):
            self.mgr.set_current_session(s.session_id)

    def test_current_falls_back_when_deleted(self):
        """当前会话被删除后，get_current 回退到 default。"""
        s = self.mgr.create_session("Will Be Deleted")
        self.mgr.set_current_session(s.session_id)
        self.mgr.delete_session(s.session_id)
        curr = self.mgr.get_current_session()
        self.assertEqual(curr.session_id, "default")

    def test_current_json_persists(self):
        s = self.mgr.create_session("Persist Test")
        self.mgr.set_current_session(s.session_id)
        # 重新加载 SessionManager 模拟新进程
        mgr2 = SessionManager(session_root=self.session_root)
        curr = mgr2.get_current_session()
        self.assertEqual(curr.session_id, s.session_id)


# ═══════════════════════════════════════════════════════════════
# TestSessionSoftDelete — 软删除测试
# ═══════════════════════════════════════════════════════════════

class TestSessionSoftDelete(IsolatedSessionTest):
    """软删除与恢复测试。"""

    def test_delete_is_soft_only(self):
        s = self.mgr.create_session("Soft Delete Me")
        session_dir = self.session_root / s.session_id
        self.mgr.delete_session(s.session_id)
        # 目录仍然存在
        self.assertTrue(session_dir.exists())
        # status 变为 DELETED
        manifest = self.mgr.get_session(s.session_id)
        self.assertEqual(manifest.status, SessionStatus.DELETED)

    def test_deleted_not_in_default_list(self):
        s = self.mgr.create_session("Hidden")
        self.mgr.delete_session(s.session_id)
        active = self.mgr.list_sessions()
        self.assertFalse(any(x.session_id == s.session_id for x in active))

    def test_deleted_visible_with_flag(self):
        s = self.mgr.create_session("Show When Deleted")
        self.mgr.delete_session(s.session_id)
        all_s = self.mgr.list_sessions(include_deleted=True)
        self.assertTrue(any(x.session_id == s.session_id for x in all_s))

    def test_restore_deleted_session(self):
        s = self.mgr.create_session("Restore Me")
        self.mgr.delete_session(s.session_id)
        restored = self.mgr.restore_session(s.session_id)
        self.assertEqual(restored.status, SessionStatus.ACTIVE)
        # 再次出现在默认列表中
        active = self.mgr.list_sessions()
        self.assertTrue(any(x.session_id == s.session_id for x in active))

    def test_restore_non_deleted_raises(self):
        s = self.mgr.create_session("Active One")
        with self.assertRaises(ValueError):
            self.mgr.restore_session(s.session_id)

    def test_archive_default_session_raises(self):
        with self.assertRaises(ValueError):
            self.mgr.archive_session("default")

    def test_delete_default_session_raises(self):
        with self.assertRaises(ValueError):
            self.mgr.delete_session("default")


# ═══════════════════════════════════════════════════════════════
# TestDefaultSession — 默认会话规则测试
# ═══════════════════════════════════════════════════════════════

class TestDefaultSession(IsolatedSessionTest):
    """默认会话规则测试。"""

    def test_default_session_always_exists(self):
        d = self.mgr.get_session("default")
        self.assertIsNotNone(d)
        self.assertEqual(d.status, SessionStatus.ACTIVE)

    def test_default_session_has_files(self):
        session_dir = self.session_root / "default"
        self.assertTrue(session_dir.exists())
        self.assertTrue((session_dir / "manifest.json").exists())
        self.assertTrue((session_dir / "trash").is_dir())

    def test_default_session_cannot_be_permanently_deleted(self):
        """即使尝试删除 default，目录仍然存在并且 manifest 状态不被永久删除。"""
        session_dir = self.session_root / "default"
        self.assertTrue(session_dir.exists())
        # delete 应被拒绝
        with self.assertRaises(ValueError):
            self.mgr.delete_session("default")
        # status 应仍为 active
        d = self.mgr.get_session("default")
        self.assertEqual(d.status, SessionStatus.ACTIVE)

    def test_ensure_default_restores_if_somehow_deleted(self):
        """如果 default 被外部强制将 status 改为 DELETED，ensure 应自动恢复。"""
        # 模拟：直接修改 manifest
        manifest_path = self.session_root / "default" / "manifest.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["status"] = SessionStatus.DELETED
        manifest_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        # 同时更新 index
        idx_path = self.session_root / "index.json"
        idx_data = json.loads(idx_path.read_text(encoding="utf-8"))
        for s in idx_data["sessions"]:
            if s["session_id"] == "default":
                s["status"] = SessionStatus.DELETED
        idx_path.write_text(json.dumps(idx_data, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        # 重新初始化应恢复
        mgr2 = SessionManager(session_root=self.session_root)
        d = mgr2.get_session("default")
        self.assertEqual(d.status, SessionStatus.ACTIVE,
                         "default session 应被自动恢复为 ACTIVE")


# ═══════════════════════════════════════════════════════════════
# TestSessionEvents — 事件日志测试
# ═══════════════════════════════════════════════════════════════

class TestSessionEvents(IsolatedSessionTest):
    """事件日志测试。"""

    def _read_events(self, session_id: str) -> list[dict]:
        path = self.session_root / session_id / "events.jsonl"
        if not path.exists():
            return []
        events = []
        for line in path.read_text(encoding="utf-8").strip().split("\n"):
            if line.strip():
                events.append(json.loads(line))
        return events

    def test_create_session_logs_event(self):
        s = self.mgr.create_session("Event Test")
        events = self._read_events(s.session_id)
        self.assertGreaterEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "create")
        self.assertEqual(events[0]["session_id"], s.session_id)

    def test_rename_logs_event(self):
        s = self.mgr.create_session("Pre Rename")
        self.mgr.rename_session(s.session_id, "Post Rename")
        events = self._read_events(s.session_id)
        rename_events = [e for e in events if e["event_type"] == "rename"]
        self.assertGreaterEqual(len(rename_events), 1)
        self.assertEqual(rename_events[-1]["details"]["new_title"], "Post Rename")

    def test_delete_logs_event(self):
        s = self.mgr.create_session("Delete Log")
        self.mgr.delete_session(s.session_id)
        events = self._read_events(s.session_id)
        delete_events = [e for e in events if e["event_type"] == "delete"]
        self.assertGreaterEqual(len(delete_events), 1)

    def test_restore_logs_event(self):
        s = self.mgr.create_session("Restore Log")
        self.mgr.delete_session(s.session_id)
        self.mgr.restore_session(s.session_id)
        events = self._read_events(s.session_id)
        restore_events = [e for e in events if e["event_type"] == "restore"]
        self.assertGreaterEqual(len(restore_events), 1)

    def test_set_current_logs_event(self):
        s = self.mgr.create_session("Current Log")
        self.mgr.set_current_session(s.session_id)
        events = self._read_events(s.session_id)
        current_events = [e for e in events if e["event_type"] == "set_current"]
        self.assertGreaterEqual(len(current_events), 1)


# ═══════════════════════════════════════════════════════════════
# TestSessionStatus — 状态枚举测试
# ═══════════════════════════════════════════════════════════════

class TestSessionStatus(unittest.TestCase):

    def test_valid_statuses(self):
        self.assertTrue(SessionStatus.is_valid("active"))
        self.assertTrue(SessionStatus.is_valid("archived"))
        self.assertTrue(SessionStatus.is_valid("deleted"))

    def test_invalid_status(self):
        self.assertFalse(SessionStatus.is_valid("bogus"))


# ═══════════════════════════════════════════════════════════════
# TestSessionArchive — 归档测试
# ═══════════════════════════════════════════════════════════════

class TestSessionArchive(IsolatedSessionTest):
    """归档功能测试。"""

    def test_archive_changes_status(self):
        s = self.mgr.create_session("Archive Me")
        archived = self.mgr.archive_session(s.session_id)
        self.assertEqual(archived.status, SessionStatus.ARCHIVED)

    def test_archive_logs_event(self):
        s = self.mgr.create_session("Archive Event")
        self.mgr.archive_session(s.session_id)
        path = self.session_root / s.session_id / "events.jsonl"
        content = path.read_text(encoding="utf-8")
        self.assertIn("archive", content)

    def test_archive_nonexistent(self):
        with self.assertRaises(ValueError):
            self.mgr.archive_session("nope")

    def test_archive_deleted_raises(self):
        s = self.mgr.create_session("Archive Deleted")
        self.mgr.delete_session(s.session_id)
        with self.assertRaises(ValueError):
            self.mgr.archive_session(s.session_id)


# ═══════════════════════════════════════════════════════════════
# 工具函数测试
# ═══════════════════════════════════════════════════════════════

class TestUtils(unittest.TestCase):

    def test_now_format(self):
        ts = _now()
        self.assertRegex(ts, r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

    def test_generate_session_id_unique(self):
        ids = {_generate_session_id() for _ in range(100)}
        self.assertEqual(len(ids), 100, "100 个 ID 应该全不同")


# ═══════════════════════════════════════════════════════════════
# 回归测试：不破坏现有 153 tests
# ═══════════════════════════════════════════════════════════════

class TestNoRegression(unittest.TestCase):
    """验证 session_manager.py 的导入不会破坏现有模块。"""

    def test_imports_not_conflicting_with_memory_core(self):
        """session_manager 导入不应与 memory_core 冲突。"""
        import memory_core
        from session_manager import SessionManager, SessionStatus
        self.assertIsNotNone(memory_core.save_memory)
        self.assertIsNotNone(SessionManager)

    def test_config_still_importable(self):
        """config.py 新增 session 字段后仍可 import。"""
        from config import MemoryConfig
        cfg = MemoryConfig()
        self.assertTrue(cfg.session_enabled)
        self.assertEqual(cfg.default_session_id, "default")


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    unittest.main(verbosity=2)
