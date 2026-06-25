"""
memory_core Session-Aware Integration — Phase 3 测试套件 (v0.7.0)

覆盖:
  - TestSaveSessionIntegration: save_memory session-aware
  - TestRetrieveSessionIntegration: retrieve_memory session filter
  - TestFormatContextSession: format_context session annotations
  - TestOldDataCompatibility: 旧数据兼容
  - TestCommandSessionIntegration: save/retrieve commands
  - TestSessionMirroring: memories.jsonl 镜像
  - TestSessionCountSync: memory_count 同步
  - TestRetrieverSessionFilter: retriever 遵守 session filter
  - TestMigration: 迁移函数

运行:
    python -m pytest tests/test_memory_session_integration.py -v
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

import memory_core
from memory_core import MemoryRecord, save_memory, retrieve_memory, format_context
from session_manager import SessionManager, SessionStatus


# ═══════════════════════════════════════════════════════════════
# 测试隔离基类
# ═══════════════════════════════════════════════════════════════

class IsolatedSessionMemoryTest(unittest.TestCase):
    """使用临时目录隔离 memory_core 和 session 存储。"""

    _saved: dict = {}

    @classmethod
    def setUpClass(cls):
        temp_root = Path(tempfile.mkdtemp(prefix="sesint_"))
        mem_dir = temp_root / "memory"
        topics_dir = mem_dir / "topics"
        idx_file = mem_dir / "index.json"
        topics_dir.mkdir(parents=True, exist_ok=True)
        idx_file.write_text("{}", encoding="utf-8")
        (topics_dir / "README.md").write_text("# README\n", encoding="utf-8")

        cls._temp_root = temp_root
        cls._temp_memory = mem_dir
        cls._temp_topics = topics_dir
        cls._temp_index = idx_file

        cls._saved = {
            "PROJECT_ROOT": memory_core.PROJECT_ROOT,
            "MEMORY_DIR": memory_core.MEMORY_DIR,
            "TOPICS_DIR": memory_core.TOPICS_DIR,
            "INDEX_FILE": memory_core.INDEX_FILE,
        }
        memory_core.PROJECT_ROOT = temp_root
        memory_core.MEMORY_DIR = mem_dir
        memory_core.TOPICS_DIR = topics_dir
        memory_core.INDEX_FILE = idx_file

        # SessionManager with isolated root
        import session_manager as sm
        sm._global_manager = None
        cls._session_root = temp_root / ".memory" / "sessions"
        cls._mgr = SessionManager(session_root=cls._session_root)
        sm._global_manager = cls._mgr

        # Reset command registry
        import commands.registry as reg_module
        reg_module._global_registry = None

    @classmethod
    def tearDownClass(cls):
        for attr, value in cls._saved.items():
            setattr(memory_core, attr, value)
        shutil.rmtree(str(cls._temp_root), ignore_errors=True)
        import session_manager as sm
        sm._global_manager = None

    def setUp(self):
        memory_core.save_index({})
        for p in self._temp_topics.glob("*.md"):
            if p.name.lower() != "readme.md":
                try:
                    p.unlink()
                except Exception:
                    pass

    # ── helpers ─────────────────────────────────────────────

    def _create_session(self, title: str, **kw) -> str:
        return self._mgr.create_session(title, **kw).session_id

    def _save(self, topic: str, text: str = None, **kw) -> Path:
        if text is None:
            text = f"Content for {topic}"
        return save_memory(topic, text, **kw)


# ═══════════════════════════════════════════════════════════════
# TestSaveSessionIntegration
# ═══════════════════════════════════════════════════════════════

class TestSaveSessionIntegration(IsolatedSessionMemoryTest):

    def test_save_defaults_to_current_session(self):
        path = self._save("SaveCurrent")
        idx = memory_core.load_index()
        rec = list(idx.values())[0]
        self.assertEqual(rec.get("session_id", ""), "default")
        self.assertTrue(path.exists())

    def test_save_with_explicit_session_id(self):
        sid = self._create_session("Target Session")
        self._mgr.set_current_session("default")
        self._save("SaveExplicit", session_id=sid)
        idx = memory_core.load_index()
        rec = list(idx.values())[0]
        self.assertEqual(rec.get("session_id", ""), sid)

    def test_save_to_deleted_session_fails(self):
        sid = self._create_session("Delete Target")
        self._mgr.delete_session(sid)
        with self.assertRaises(ValueError):
            self._save("Should Fail", session_id=sid)

    def test_save_to_archived_session_fails_by_default(self):
        sid = self._create_session("Archive Target")
        self._mgr.archive_session(sid)
        with self.assertRaises(ValueError):
            self._save("Should Fail", session_id=sid)

    def test_save_to_archived_with_flag(self):
        sid = self._create_session("Archive Allow")
        self._mgr.archive_session(sid)
        path = self._save("Archived OK", session_id=sid, allow_archived=True)
        self.assertTrue(path.exists())

    def test_save_updates_memory_count(self):
        sid = self._create_session("Count Test")
        self._save("Count 1", session_id=sid)
        manifest = self._mgr.get_session(sid)
        self.assertGreaterEqual(manifest.memory_count, 1)

    def test_save_mirrors_to_jsonl(self):
        sid = self._create_session("Mirror Test")
        self._save("Mirror", session_id=sid)
        jsonl = self._session_root / sid / "memories.jsonl"
        content = jsonl.read_text(encoding="utf-8")
        self.assertIn("Mirror", content)

    def test_save_old_signature_still_works(self):
        path = save_memory("OldWay", "old content", append=True)
        self.assertTrue(path.exists())


# ═══════════════════════════════════════════════════════════════
# TestRetrieveSessionIntegration
# ═══════════════════════════════════════════════════════════════

class TestRetrieveSessionIntegration(IsolatedSessionMemoryTest):

    def _save_with_session(self, topic: str, sid: str):
        return self._save(topic, session_id=sid)

    def test_retrieve_default_current_session(self):
        sid_a = self._create_session("Session A")
        self._mgr.set_current_session(sid_a)
        self._save_with_session("A Topic", sid_a)
        # default session has no memories
        self._mgr.set_current_session("default")
        results = retrieve_memory("A Topic", mode="keyword")
        # searching from default session — should find nothing since A is not default
        self.assertEqual(len(results), 0)

    def test_retrieve_specific_session(self):
        sid = self._create_session("Target")
        self._save_with_session("Target Topic", sid)
        results = retrieve_memory("Target Topic", session_id=sid, mode="keyword")
        self.assertGreater(len(results), 0)
        self.assertIn(results[0]["source_session"], (sid, ""))

    def test_retrieve_all_sessions(self):
        self._save_with_session("Default Mem", "default")
        sid = self._create_session("Extra")
        self._save_with_session("Extra Mem", sid)
        results = retrieve_memory("Mem", all_sessions=True, mode="keyword")
        self.assertGreaterEqual(len(results), 2)

    def test_retrieve_all_sessions_excludes_archived_by_default(self):
        sid = self._create_session("Archived")
        self._save_with_session("Archived Mem", sid)
        self._mgr.archive_session(sid)
        results = retrieve_memory("Archived Mem", all_sessions=True, mode="keyword")
        self.assertEqual(len(results), 0)

    def test_retrieve_include_archived_sessions(self):
        sid = self._create_session("Archived Inc")
        self._save_with_session("Archived Mem", sid)
        self._mgr.archive_session(sid)
        results = retrieve_memory("Archived Mem", all_sessions=True,
                                  include_archived_sessions=True, mode="keyword")
        self.assertGreater(len(results), 0)

    def test_retrieve_results_have_retrieval_scope(self):
        self._save("Scoped", session_id="default")
        results = retrieve_memory("Scoped", mode="keyword")
        self.assertGreater(len(results), 0)
        self.assertIn("retrieval_scope", results[0])
        self.assertIn("default", results[0]["retrieval_scope"])

    def test_retrieve_results_have_source_session(self):
        self._save("SourceCheck", session_id="default")
        results = retrieve_memory("SourceCheck", mode="keyword")
        self.assertEqual(results[0].get("source_session", ""), "default")


# ═══════════════════════════════════════════════════════════════
# TestFormatContextSession
# ═══════════════════════════════════════════════════════════════

class TestFormatContextSession(IsolatedSessionMemoryTest):

    def test_format_includes_retrieval_scope(self):
        self._save("FmtScope", session_id="default")
        results = retrieve_memory("FmtScope", mode="keyword")
        ctx = format_context(results)
        self.assertIn("Retrieval scope", ctx)
        self.assertIn("default", ctx)

    def test_format_includes_session_tag_on_items(self):
        sid = self._create_session("Fmt Session")
        self._save("FmtTag", session_id=sid)
        results = retrieve_memory("FmtTag", all_sessions=True, mode="keyword")
        ctx = format_context(results)
        self.assertIn("session:", ctx)

    def test_format_old_style_still_works(self):
        results = [{
            "id": "test", "topic": "Test", "score": 10,
            "file": "", "summary": "s", "keywords": [],
            "decisions": [], "todos": [], "content": "c",
        }]
        ctx = format_context(results)
        self.assertIn("相关记忆", ctx)


# ═══════════════════════════════════════════════════════════════
# TestOldDataCompatibility
# ═══════════════════════════════════════════════════════════════

class TestOldDataCompatibility(IsolatedSessionMemoryTest):

    def test_old_record_without_session_id_defaults(self):
        old_record = MemoryRecord(
            topic="Old Topic", file="memory/topics/old.md",
            keywords=["old"], summary="legacy",
            created_at="2025-01-01 00:00:00",
            updated_at="2025-01-01 00:00:00",
        )
        self.assertEqual(old_record.session_id, "default")

    def test_index_record_missing_session_id(self):
        old_idx = {
            "old_key": {
                "topic": "Legacy", "file": "memory/topics/old.md",
                "keywords": ["legacy"], "summary": "old",
                "created_at": "2025-01-01 00:00:00",
                "updated_at": "2025-01-01 00:00:00",
            }
        }
        memory_core.save_index(old_idx)
        results = retrieve_memory("Legacy", mode="keyword")
        self.assertGreater(len(results), 0)
        self.assertEqual(results[0].get("source_session", ""), "default")


# ═══════════════════════════════════════════════════════════════
# TestCommandSessionIntegration
# ═══════════════════════════════════════════════════════════════

class TestCommandSessionIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.temp = Path(tempfile.mkdtemp(prefix="sescmdint_"))
        cls.session_root = cls.temp / "sessions"
        import session_manager as sm
        sm._global_manager = None
        cls.mgr = SessionManager(session_root=cls.session_root)
        sm._global_manager = cls.mgr
        # memory_core to temp
        mem_dir = cls.temp / "memory"
        topics_dir = mem_dir / "topics"
        idx_file = mem_dir / "index.json"
        topics_dir.mkdir(parents=True, exist_ok=True)
        idx_file.write_text("{}", encoding="utf-8")
        (topics_dir / "README.md").write_text("# README\n", encoding="utf-8")

        cls._saved = {
            "PROJECT_ROOT": memory_core.PROJECT_ROOT,
            "MEMORY_DIR": memory_core.MEMORY_DIR,
            "TOPICS_DIR": memory_core.TOPICS_DIR,
            "INDEX_FILE": memory_core.INDEX_FILE,
        }
        memory_core.PROJECT_ROOT = cls.temp
        memory_core.MEMORY_DIR = mem_dir
        memory_core.TOPICS_DIR = topics_dir
        memory_core.INDEX_FILE = idx_file

        import commands.registry as reg_module
        reg_module._global_registry = None

    @classmethod
    def tearDownClass(cls):
        for attr, value in cls._saved.items():
            setattr(memory_core, attr, value)
        shutil.rmtree(str(cls.temp), ignore_errors=True)
        import session_manager as sm
        sm._global_manager = None

    def setUp(self):
        memory_core.save_index({})

    def test_save_command_defaults_to_current(self):
        from commands.registry import get_registry
        reg = get_registry()
        r = reg.dispatch("memory:save",
                         {"topic": "CmdSave", "text": "session test"})
        self.assertTrue(r.ok, f"save failed: {r.error}")
        idx = memory_core.load_index()
        rec = list(idx.values())[0]
        self.assertEqual(rec.get("session_id", ""), "default")

    def test_save_command_with_session_id(self):
        from commands.registry import get_registry
        sid = self.mgr.create_session("Cmd Target").session_id
        reg = get_registry()
        r = reg.dispatch("memory:save",
                         {"topic": "CmdSave2", "text": "targeted",
                          "session_id": sid})
        self.assertTrue(r.ok)
        idx = memory_core.load_index()
        rec = list(idx.values())[0]
        self.assertEqual(rec.get("session_id", ""), sid)

    def test_retrieve_command_defaults_to_current(self):
        from commands.registry import get_registry
        reg = get_registry()
        reg.dispatch("memory:save",
                     {"topic": "CurrRetrieve", "text": "current session data"})
        r = reg.dispatch("memory:retrieve",
                         {"query": "current session", "mode": "keyword"})
        self.assertTrue(r.ok)
        self.assertGreater(r.data.get("hit_count", 0), 0)

    def test_retrieve_all_sessions_direct(self):
        sid = self.mgr.create_session("AllSess").session_id
        memory_core.save_memory("AllData", "unique phrase all session content",
                                session_id=sid)
        results = memory_core.retrieve_memory(
            "AllData unique phrase", all_sessions=True, mode="keyword")
        self.assertGreater(len(results), 0,
                          "Should find AllData in all_sessions mode")
        self.assertIn(results[0].get("source_session", ""), (sid, ""))

    def test_retrieve_help_contains_session_params(self):
        from commands.registry import get_registry
        reg = get_registry()
        cmd = reg.get("memory:retrieve")
        help_text = cmd.format_help()
        self.assertIn("session_id", help_text)
        self.assertIn("all_sessions", help_text)

    def test_existing_memory_manage_still_works(self):
        from commands.registry import get_registry
        reg = get_registry()
        r = reg.dispatch("memory:manage", {"action": "quality"})
        self.assertTrue(r.ok)

    def test_existing_memory_session_still_works(self):
        from commands.registry import get_registry
        reg = get_registry()
        r = reg.dispatch("memory:session", {"action": "current"})
        self.assertTrue(r.ok)


# ═══════════════════════════════════════════════════════════════
# TestRetrieverSessionFilter
# ═══════════════════════════════════════════════════════════════

class TestRetrieverSessionFilter(IsolatedSessionMemoryTest):

    def test_keyword_retriever_obeys_session(self):
        sid = self._create_session("KwSession")
        self._save("Kw Default", session_id="default")
        self._save("Kw Specific", session_id=sid)
        results = retrieve_memory("Kw", session_id=sid, mode="keyword")
        self.assertEqual(len(results), 1)
        self.assertIn("Specific", results[0]["content"])

    def test_hybrid_retriever_obeys_session(self):
        sid = self._create_session("HySession")
        self._save("Hy Default", session_id="default")
        self._save("Hy Specific", session_id=sid)
        from embedding_provider import FakeEmbeddingProvider
        provider = FakeEmbeddingProvider(dimension=64)
        results = retrieve_memory("Hy", session_id=sid, mode="hybrid",
                                  embedding_provider=provider)
        self.assertEqual(len(results), 1)


# ═══════════════════════════════════════════════════════════════
# TestSessionCountSync
# ═══════════════════════════════════════════════════════════════

class TestSessionCountSync(IsolatedSessionMemoryTest):

    def test_memory_count_increments_on_save(self):
        sid = self._create_session("Count Sync")
        before = self._mgr.get_session(sid).memory_count
        self._save("Count A", session_id=sid)
        self._save("Count B", session_id=sid)
        after = self._mgr.get_session(sid).memory_count
        self.assertEqual(after, before + 2)

    def test_session_info_shows_memory_count(self):
        from commands.registry import get_registry
        sid = self._create_session("Info Count")
        self._save("Info A", session_id=sid)
        reg = get_registry()
        r = reg.dispatch("memory:session", {"action": "info",
                                             "session_id": sid})
        self.assertTrue(r.ok)
        self.assertGreaterEqual(r.data.get("memory_count", 0), 1)


# ═══════════════════════════════════════════════════════════════
# TestNoRegression
# ═══════════════════════════════════════════════════════════════

class TestNoRegression(unittest.TestCase):
    """验证 session integration 不破坏现有测试。"""

    def test_memory_core_importable(self):
        import memory_core
        self.assertTrue(callable(memory_core.save_memory))
        self.assertTrue(callable(memory_core.retrieve_memory))

    def test_session_manager_importable(self):
        from session_manager import SessionManager, SessionStatus
        self.assertIsNotNone(SessionManager)


if __name__ == "__main__":
    unittest.main(verbosity=2)
