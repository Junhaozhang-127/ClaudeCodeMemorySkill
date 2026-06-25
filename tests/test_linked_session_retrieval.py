"""
Linked Session Retrieval — Phase 4 测试套件 (v0.7.0)

覆盖:
  - TestLinkAPI: link/unlink/list linked sessions
  - TestLinkCommand: memory:session link/unlink/links
  - TestLinkedRetrieval: retrieve_memory with include_linked_sessions
  - TestLinkedFormatContext: format_context linked annotations
  - TestLinkedRegression: regression checks

运行:
    python -m pytest tests/test_linked_session_retrieval.py -v
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
from memory_core import save_memory, retrieve_memory, format_context
from session_manager import SessionManager, SessionStatus, _now


# ═══════════════════════════════════════════════════════════════
# 测试隔离基类
# ═══════════════════════════════════════════════════════════════

class IsolatedLinkedTest(unittest.TestCase):

    _saved: dict = {}

    @classmethod
    def setUpClass(cls):
        temp_root = Path(tempfile.mkdtemp(prefix="linktest_"))
        mem_dir = temp_root / "memory"
        topics_dir = mem_dir / "topics"
        idx_file = mem_dir / "index.json"
        topics_dir.mkdir(parents=True, exist_ok=True)
        idx_file.write_text("{}", encoding="utf-8")
        (topics_dir / "README.md").write_text("# README\n", encoding="utf-8")

        cls._temp_root = temp_root
        cls._session_root = temp_root / ".memory" / "sessions"

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

        import session_manager as sm
        sm._global_manager = None
        cls.mgr = SessionManager(session_root=cls._session_root)
        sm._global_manager = cls.mgr

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


# ═══════════════════════════════════════════════════════════════
# TestLinkAPI
# ═══════════════════════════════════════════════════════════════

class TestLinkAPI(IsolatedLinkedTest):

    def test_link_writes_links_json(self):
        src = self.mgr.create_session("Source").session_id
        tgt = self.mgr.create_session("Target").session_id
        result = self.mgr.link_session(src, tgt, reason="test")
        self.assertTrue(result["ok"])
        links_path = self._session_root / src / "links.json"
        data = json.loads(links_path.read_text(encoding="utf-8"))
        self.assertGreater(len(data["linked_sessions"]), 0)
        self.assertEqual(data["linked_sessions"][0]["session_id"], tgt)

    def test_link_syncs_manifest(self):
        src = self.mgr.create_session("Src2").session_id
        tgt = self.mgr.create_session("Tgt2").session_id
        self.mgr.link_session(src, tgt)
        manifest = self.mgr.get_session(src)
        self.assertIn(tgt, manifest.linked_session_ids)

    def test_link_logs_event(self):
        src = self.mgr.create_session("Src3").session_id
        tgt = self.mgr.create_session("Tgt3").session_id
        self.mgr.link_session(src, tgt)
        events_path = self._session_root / src / "events.jsonl"
        content = events_path.read_text(encoding="utf-8")
        self.assertIn("session_linked", content)

    def test_link_idempotent(self):
        src = self.mgr.create_session("Src4").session_id
        tgt = self.mgr.create_session("Tgt4").session_id
        r1 = self.mgr.link_session(src, tgt)
        r2 = self.mgr.link_session(src, tgt)
        self.assertTrue(r1["ok"])
        self.assertTrue(r2["ok"])
        self.assertTrue(r2["already_linked"])

    def test_cannot_link_self(self):
        src = self.mgr.create_session("SelfLink").session_id
        with self.assertRaises(ValueError):
            self.mgr.link_session(src, src)

    def test_cannot_link_nonexistent(self):
        src = self.mgr.create_session("Src5").session_id
        with self.assertRaises(ValueError):
            self.mgr.link_session(src, "nonexistent")

    def test_cannot_link_deleted(self):
        src = self.mgr.create_session("Src6").session_id
        tgt = self.mgr.create_session("TgtDel").session_id
        self.mgr.delete_session(tgt)
        with self.assertRaises(ValueError):
            self.mgr.link_session(src, tgt)

    def test_cannot_link_archived_by_default(self):
        src = self.mgr.create_session("Src7").session_id
        tgt = self.mgr.create_session("TgtArch").session_id
        self.mgr.archive_session(tgt)
        with self.assertRaises(ValueError):
            self.mgr.link_session(src, tgt)

    def test_link_archived_with_flag(self):
        src = self.mgr.create_session("Src8").session_id
        tgt = self.mgr.create_session("TgtArch2").session_id
        self.mgr.archive_session(tgt)
        result = self.mgr.link_session(src, tgt, allow_archived=True)
        self.assertTrue(result["ok"])

    def test_unlink_removes_link(self):
        src = self.mgr.create_session("Src9").session_id
        tgt = self.mgr.create_session("Tgt9").session_id
        self.mgr.link_session(src, tgt)
        result = self.mgr.unlink_session(src, tgt)
        self.assertTrue(result["ok"])
        links_path = self._session_root / src / "links.json"
        data = json.loads(links_path.read_text(encoding="utf-8"))
        self.assertEqual(len(data["linked_sessions"]), 0)

    def test_unlink_syncs_manifest(self):
        src = self.mgr.create_session("Src10").session_id
        tgt = self.mgr.create_session("Tgt10").session_id
        self.mgr.link_session(src, tgt)
        self.mgr.unlink_session(src, tgt)
        manifest = self.mgr.get_session(src)
        self.assertNotIn(tgt, manifest.linked_session_ids)

    def test_list_linked_sessions_default_active(self):
        src = self.mgr.create_session("Src11").session_id
        tgt = self.mgr.create_session("Tgt11").session_id
        self.mgr.link_session(src, tgt)
        linked = self.mgr.list_linked_sessions(src)
        self.assertEqual(len(linked), 1)
        self.assertEqual(linked[0].session_id, tgt)

    def test_list_linked_excludes_deleted(self):
        src = self.mgr.create_session("Src12").session_id
        tgt = self.mgr.create_session("Tgt12").session_id
        self.mgr.link_session(src, tgt)
        self.mgr.delete_session(tgt)
        linked = self.mgr.list_linked_sessions(src)
        self.assertEqual(len(linked), 0)

    def test_old_links_format_compatible(self):
        """旧格式 links.json (字符串列表) 可兼容读取并规范化。"""
        src = self.mgr.create_session("SrcOld").session_id
        tgt1 = self.mgr.create_session("OldTgt1").session_id
        tgt2 = self.mgr.create_session("OldTgt2").session_id
        path = self._session_root / src / "links.json"
        old_data = {"version": "0.7.0", "linked_sessions": [tgt1, tgt2],
                     "updated_at": _now()}
        path.write_text(json.dumps(old_data), encoding="utf-8")
        ids = self.mgr.get_linked_session_ids(src)
        self.assertEqual(len(ids), 2)


# ═══════════════════════════════════════════════════════════════
# TestLinkCommand
# ═══════════════════════════════════════════════════════════════

class TestLinkCommand(IsolatedLinkedTest):

    def test_link_default_from_current(self):
        from commands.registry import get_registry
        tgt = self.mgr.create_session("CmdTgt").session_id
        reg = get_registry()
        r = reg.dispatch("memory:session",
                         {"action": "link", "to": tgt, "reason": "cmd test"})
        self.assertTrue(r.ok, f"link failed: {r.error}")

    def test_link_explicit_from(self):
        from commands.registry import get_registry
        src = self.mgr.create_session("CmdSrc").session_id
        tgt = self.mgr.create_session("CmdTgt2").session_id
        reg = get_registry()
        r = reg.dispatch("memory:session",
                         {"action": "link", "from": src, "to": tgt})
        self.assertTrue(r.ok)

    def test_unlink_default_from_current(self):
        from commands.registry import get_registry
        tgt = self.mgr.create_session("UnlinkTgt").session_id
        reg = get_registry()
        reg.dispatch("memory:session", {"action": "link", "to": tgt})
        r = reg.dispatch("memory:session", {"action": "unlink", "to": tgt})
        self.assertTrue(r.ok)

    def test_links_shows_current(self):
        tgt = self.mgr.create_session("LinksTgt").session_id
        self.mgr.link_session("default", tgt, reason="test links")
        linked = self.mgr.list_linked_sessions("default")
        self.assertGreaterEqual(len(linked), 1)
        self.assertIn(tgt, [s.session_id for s in linked])

    def test_links_with_session_id(self):
        from commands.registry import get_registry
        src = self.mgr.create_session("LinksSrc").session_id
        tgt = self.mgr.create_session("LinksTgt2").session_id
        reg = get_registry()
        reg.dispatch("memory:session", {"action": "link", "from": src, "to": tgt})
        r = reg.dispatch("memory:session",
                         {"action": "links", "session_id": src})
        self.assertEqual(r.data.get("count", 0), 1)


# ═══════════════════════════════════════════════════════════════
# TestLinkedRetrieval
# ═══════════════════════════════════════════════════════════════

class TestLinkedRetrieval(IsolatedLinkedTest):

    def _save(self, topic, text, sid):
        return save_memory(topic, text, session_id=sid)

    def test_default_only_current(self):
        tgt = self.mgr.create_session("RetTgt").session_id
        self.mgr.link_session("default", tgt)
        self._save("DefaultOnly", "default session data", "default")
        self._save("LinkedOnly", "linked session data", tgt)
        results = retrieve_memory("session data", mode="keyword")
        self.assertEqual(len(results), 1)
        self.assertIn("default", results[0]["content"])

    def test_include_linked_returns_both(self):
        tgt = self.mgr.create_session("RetTgt2").session_id
        self.mgr.link_session("default", tgt)
        self._save("DefaultData", "alpha memory content", "default")
        self._save("LinkedData", "beta memory content", tgt)
        results = retrieve_memory("memory content", include_linked_sessions=True, mode="keyword")
        self.assertGreaterEqual(len(results), 2)

    def test_linked_excludes_archived_by_default(self):
        tgt = self.mgr.create_session("RetArch").session_id
        self.mgr.link_session("default", tgt)
        self._save("LinkedArch", "linked archived content", tgt)
        self.mgr.archive_session(tgt)
        results = retrieve_memory("linked archived content",
                                  include_linked_sessions=True, mode="keyword")
        self.assertEqual(len(results), 0)

    def test_linked_include_archived_with_flag(self):
        tgt = self.mgr.create_session("RetArch2").session_id
        self.mgr.link_session("default", tgt, allow_archived=True)  # archive then link via allow
        self._save("LinkedArch2", "linked archived with flag", tgt)
        self.mgr.archive_session(tgt)
        # Re-link after archive using allow_archived
        self.mgr.unlink_session("default", tgt)
        self.mgr.link_session("default", tgt, allow_archived=True)
        results = retrieve_memory("linked archived with flag",
                                  include_linked_sessions=True,
                                  include_archived_sessions=True, mode="keyword")
        self.assertGreater(len(results), 0)

    def test_results_have_is_linked_flag(self):
        tgt = self.mgr.create_session("RetFlag").session_id
        self.mgr.link_session("default", tgt)
        self._save("DefaultFlag", "default flag content", "default")
        self._save("LinkedFlag", "linked flag content", tgt)
        results = retrieve_memory("flag content", include_linked_sessions=True, mode="keyword")
        linked = [r for r in results if r.get("is_linked_session")]
        self.assertGreater(len(linked), 0)

    def test_all_sessions_overrides_linked(self):
        tgt = self.mgr.create_session("RetAll").session_id
        self.mgr.link_session("default", tgt)
        self._save("AllDefault", "all default data", "default")
        self._save("AllLinked", "all linked data", tgt)
        results = retrieve_memory("all default linked", all_sessions=True, mode="keyword")
        self.assertGreaterEqual(len(results), 2)

    def test_hybrid_retriever_obeys_linked(self):
        tgt = self.mgr.create_session("RetHybrid").session_id
        self.mgr.link_session("default", tgt)
        self._save("HyDefault", "hybrid default memory", "default")
        self._save("HyLinked", "hybrid linked memory", tgt)
        from embedding_provider import FakeEmbeddingProvider
        prov = FakeEmbeddingProvider(dimension=64)
        results = retrieve_memory("hybrid memory", include_linked_sessions=True,
                                  mode="hybrid", embedding_provider=prov)
        self.assertGreaterEqual(len(results), 2)


# ═══════════════════════════════════════════════════════════════
# TestLinkedFormatContext
# ═══════════════════════════════════════════════════════════════

class TestLinkedFormatContext(IsolatedLinkedTest):

    def test_linked_item_has_linked_tag(self):
        tgt = self.mgr.create_session("FmtTgt").session_id
        self.mgr.link_session("default", tgt)
        save_memory("FmtDefault", "fmt default content", session_id="default")
        save_memory("FmtLinked", "fmt linked content", session_id=tgt)
        results = retrieve_memory("fmt", include_linked_sessions=True, mode="keyword")
        ctx = format_context(results)
        self.assertIn("[linked]", ctx)

    def test_all_sessions_format_unchanged(self):
        save_memory("AllSessFmt", "all sessions format test", session_id="default")
        results = retrieve_memory("all sessions format", all_sessions=True, mode="keyword")
        ctx = format_context(results)
        self.assertIn("all sessions", ctx)

    def test_current_session_format_unchanged(self):
        save_memory("CurrFmt", "current format test", session_id="default")
        results = retrieve_memory("current format", mode="keyword")
        ctx = format_context(results)
        self.assertIn("Retrieval scope", ctx)


if __name__ == "__main__":
    unittest.main(verbosity=2)
