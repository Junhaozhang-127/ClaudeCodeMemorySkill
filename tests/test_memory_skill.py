"""
Claude Code Memory Skill MVP 完整测试套件。

覆盖场景：
  - 保存记忆生成 Markdown 文件
  - 检索匹配 / 无匹配
  - 索引损坏恢复
  - 索引重建（含 README.md 跳过）
  - 追加 / 覆盖模式
  - format_context 空结果
  - is_memory_markdown 辅助函数
  - 原子写入后 JSON 有效性

运行：
    python tests/test_memory_skill.py
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from memory_core import (
    save_memory,
    retrieve_memory,
    format_context,
    rebuild_index,
    load_index,
    save_index,
    ensure_memory_dirs,
    is_memory_markdown,
    INDEX_FILE,
    TOPICS_DIR,
)

TEST_TOPIC_PREFIXES = (
    "测试_",
    "test_",
    "TEST_",
)


class TestMemorySkill(unittest.TestCase):
    """Claude Code Memory Skill 核心流程测试。"""

    _original_index: str | None = None

    @classmethod
    def setUpClass(cls) -> None:
        ensure_memory_dirs()
        if INDEX_FILE.exists():
            cls._original_index = INDEX_FILE.read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        # 恢复原始 index.json
        if cls._original_index is not None:
            INDEX_FILE.write_text(cls._original_index, encoding="utf-8")
        else:
            INDEX_FILE.write_text("{}", encoding="utf-8")

        # 清理测试生成的 Markdown 文件
        for p in sorted(TOPICS_DIR.glob("*.md")):
            name = p.name
            if any(name.startswith(prefix) for prefix in TEST_TOPIC_PREFIXES):
                try:
                    p.unlink()
                except FileNotFoundError:
                    pass

        # 清理可能残留的临时文件
        tmp = INDEX_FILE.with_name("index.json.tmp")
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass

    # ── 写入测试 ────────────────────────────────────────────

    def test_01_save_memory_creates_markdown_file(self):
        """保存记忆后应生成 Markdown 文件。"""
        path = save_memory("测试_保存记忆_文件生成", "这是一条测试记忆内容，用于验证文件生成。")
        self.assertTrue(path.exists(), f"文件应存在: {path}")
        content = path.read_text(encoding="utf-8")
        self.assertIn("测试_保存记忆_文件生成", content)
        self.assertIn("测试记忆内容", content)

    def test_02_append_mode_adds_content(self):
        """append=True 时同主题同日期应追加内容而非覆盖。"""
        topic = "测试_追加写入_内容合并"
        save_memory(topic, "第一段记忆内容。", append=True)
        save_memory(topic, "第二段记忆内容。", append=True)
        results = retrieve_memory(topic, top_k=1)
        self.assertTrue(len(results) > 0, "应能检索到已保存记忆")
        content = results[0]["content"]
        self.assertIn("第一段", content)
        self.assertIn("第二段", content)

    def test_03_no_append_overwrites_content(self):
        """append=False 时同主题同日期应覆盖文件内容。"""
        topic = "测试_覆盖写入_替换旧内容"
        save_memory(topic, "旧内容，不应出现。", append=False)
        save_memory(topic, "新内容，覆盖后唯一存在。", append=False)
        results = retrieve_memory(topic, top_k=1)
        self.assertTrue(len(results) > 0)
        content = results[0]["content"]
        self.assertIn("新内容，覆盖后唯一存在", content)
        self.assertNotIn("旧内容，不应出现", content)

    # ── 检索测试 ────────────────────────────────────────────

    def test_04_retrieve_returns_matching_results(self):
        """相关查询应返回匹配记忆。"""
        save_memory(
            "测试_检索匹配_Claude",
            "用户询问 Claude Code 如何通过 Hook 自动保存会话记忆到本地 Markdown 存储。",
        )
        results = retrieve_memory("Claude Code Hook 会话记忆", top_k=3)
        self.assertTrue(len(results) > 0, "相关查询应返回至少一条结果")
        # 第一条应包含 Claude Code 相关内容
        top = results[0]
        self.assertTrue(
            "Claude" in top["content"] or "Claude" in top["summary"],
            "检索结果应与查询相关",
        )

    def test_05_retrieve_no_match_returns_empty(self):
        """完全不相关的查询应返回空列表。"""
        save_memory("测试_检索无匹配_天气", "今天天气晴朗，适合户外活动。")
        results = retrieve_memory("量子计算 黑洞 相对论 弦理论", top_k=3)
        self.assertEqual(len(results), 0, "无匹配查询应返回空列表")

    def test_06_retrieve_result_structure(self):
        """检索结果应包含完整的字段结构（可用于 JSON 序列化）。"""
        save_memory("测试_检索结构_字段", "验证检索结果的结构完整性。")
        results = retrieve_memory("检索 结构 字段", top_k=1)
        self.assertTrue(len(results) > 0)
        result = results[0]
        for key in ("id", "topic", "score", "content", "summary", "keywords", "file"):
            self.assertIn(key, result, f"检索结果应包含 '{key}' 字段")
        # 验证可 JSON 序列化
        json_text = json.dumps(results, ensure_ascii=False)
        parsed = json.loads(json_text)
        self.assertEqual(len(parsed), len(results))

    # ── 索引恢复与重建 ─────────────────────────────────────

    def test_07_corrupt_index_does_not_crash(self):
        """index.json 损坏时 load_index() 应返回空字典而不是崩溃。"""
        # 写入非法 JSON
        INDEX_FILE.write_text("{这不是有效的 JSON {{{", encoding="utf-8")
        index = load_index()
        self.assertEqual(index, {}, "损坏索引应返回空字典")
        # 恢复可写状态
        INDEX_FILE.write_text("{}", encoding="utf-8")

    def test_08_rebuild_index_creates_entries(self):
        """从已有 Markdown 文件重建索引应生成正确的条目。"""
        save_memory("测试_重建索引_条目生成", "重建索引功能验证：应能扫描 Markdown 并重建索引。")
        # 清空索引
        INDEX_FILE.write_text("{}", encoding="utf-8")
        rebuilt = rebuild_index()
        self.assertGreater(len(rebuilt), 0, "重建索引应包含已保存的记忆条目")
        found = any(
            "测试_重建索引_条目生成" in record.get("topic", "")
            for record in rebuilt.values()
        )
        self.assertTrue(found, "重建索引应找到测试保存的记忆")

    def test_09_rebuild_index_skips_readme(self):
        """memory/topics/README.md 不应出现在重建索引中。"""
        save_memory("测试_跳过说明文档_真实记忆", "该记忆应被索引，而 README.md 不应被索引。")
        INDEX_FILE.write_text("{}", encoding="utf-8")
        rebuilt = rebuild_index()
        readme_indexed = False
        for key, record in rebuilt.items():
            file_path = str(record.get("file", ""))
            # 检查文件名（而非路径片段）是否匹配 README.md
            if Path(file_path).name.lower() == "readme.md":
                readme_indexed = True
            # 验证真实记忆被索引
            if "跳过说明文档" in str(record.get("topic", "")):
                self.assertIn(".md", file_path)
        self.assertFalse(readme_indexed, "README.md 不应出现在重建索引中")

    # ── format_context 测试 ─────────────────────────────────

    def test_10_format_context_empty_result(self):
        """空结果 format_context 应输出明确提示信息。"""
        result = format_context([])
        self.assertIn("未检索到", result, "空结果应有提示")

    # ── 辅助函数测试 ────────────────────────────────────────

    def test_11_is_memory_markdown_helper(self):
        """is_memory_markdown 应正确区分真实记忆和特殊文件。"""
        self.assertTrue(is_memory_markdown(Path("/fake/memory/topic_2026-06-03.md")))
        self.assertFalse(is_memory_markdown(Path("/fake/README.md")))
        self.assertFalse(is_memory_markdown(Path("/fake/READme.md")))
        self.assertFalse(is_memory_markdown(Path("/fake/.gitkeep")))
        self.assertFalse(is_memory_markdown(Path("/fake/.hidden.md")))
        self.assertFalse(is_memory_markdown(Path("/fake/notes.txt")))

    # ── 原子写入测试 ───────────────────────────────────────

    def test_12_atomic_write_produces_valid_json(self):
        """原子写入后 index.json 应为有效 JSON 且内容正确。"""
        test_data = {"atomic_test_key": {"topic": "原子写入验证"}}
        save_index(test_data)
        # 验证写入内容
        loaded = load_index()
        self.assertIn("atomic_test_key", loaded)
        # 验证临时文件已清理
        tmp = INDEX_FILE.with_name("index.json.tmp")
        self.assertFalse(tmp.exists(), "原子写入后临时文件应已被替换")
        # 清理
        save_index({})


if __name__ == "__main__":
    unittest.main(verbosity=2)
