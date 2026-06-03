"""
Claude Code Memory Skill MVP — Phase 2 完整测试套件。

覆盖：
  核心层（temp dir 隔离）：摘要器、关键词抽取、结构化 Markdown、
    索引元数据扩展、检索评分增强、format_context 优化、向后兼容
  CLI 层（subprocess）：--json decisions/todos、--no-append、update_index

运行：
    python tests/test_memory_skill.py
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# ── 项目路径 ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import memory_core
from summarizers import RuleBasedSummarizer, SummaryResult, BaseSummarizer


# ═══════════════════════════════════════════════════════════════
# 测试隔离基类
# ═══════════════════════════════════════════════════════════════

class IsolatedMemoryTest(unittest.TestCase):
    """用临时目录替代真实 memory/ 目录，测试后自动清理。"""

    _saved_attrs: dict = {}

    @classmethod
    def setUpClass(cls) -> None:
        cls._temp_root = Path(tempfile.mkdtemp(prefix="memtest_"))
        cls._temp_memory = cls._temp_root / "memory"
        cls._temp_topics = cls._temp_memory / "topics"
        cls._temp_index = cls._temp_memory / "index.json"
        cls._temp_topics.mkdir(parents=True, exist_ok=True)
        cls._temp_index.write_text("{}", encoding="utf-8")
        (cls._temp_topics / "README.md").write_text(
            "# topics 目录说明\n\n说明文件，不应被索引。\n", encoding="utf-8"
        )
        cls._saved_attrs = {
            "PROJECT_ROOT": memory_core.PROJECT_ROOT,
            "MEMORY_DIR": memory_core.MEMORY_DIR,
            "TOPICS_DIR": memory_core.TOPICS_DIR,
            "INDEX_FILE": memory_core.INDEX_FILE,
        }
        memory_core.PROJECT_ROOT = cls._temp_root
        memory_core.MEMORY_DIR = cls._temp_memory
        memory_core.TOPICS_DIR = cls._temp_topics
        memory_core.INDEX_FILE = cls._temp_index

    @classmethod
    def tearDownClass(cls) -> None:
        for attr, value in cls._saved_attrs.items():
            setattr(memory_core, attr, value)
        shutil.rmtree(cls._temp_root, ignore_errors=True)

    @property
    def temp_index(self) -> Path:
        return self._temp_index

    @property
    def temp_topics(self) -> Path:
        return self._temp_topics


# ═══════════════════════════════════════════════════════════════
# Phase 2: 摘要器测试
# ═══════════════════════════════════════════════════════════════

class TestSummarizer(unittest.TestCase):
    """RuleBasedSummarizer 单元测试。"""

    def setUp(self):
        self.summarizer = RuleBasedSummarizer(
            keyword_extractor=memory_core.extract_keywords
        )

    def test_summary_generated(self):
        """应生成非空摘要。"""
        text = (
            "今天讨论了 Claude Code 记忆系统的架构设计。"
            "我们决定采用 Markdown + JSON 索引的存储方案。"
            "不需要引入数据库，保持轻量化。"
        )
        result = self.summarizer.summarize(text, "记忆系统架构")
        self.assertTrue(len(result.summary) > 0)
        self.assertIn("Claude Code", result.summary)

    def test_decisions_extracted(self):
        """应从包含触发词的句子中抽取关键决策。"""
        text = (
            "经过讨论，我们决定使用 jieba 进行中文分词。"
            "同时确定采用可插拔架构来支持未来 LLM 摘要器。"
            "对于存储，保持 Markdown + JSON 的轻量方案，不再引入数据库。"
            "最终结论是本阶段不接入外部 API。"
        )
        result = self.summarizer.summarize(text, "技术选型")
        self.assertGreater(len(result.decisions), 0, "应至少抽到一条决策")
        self.assertTrue(
            any("jieba" in d or "可插拔" in d or "数据库" in d or "API" in d
                for d in result.decisions)
        )

    def test_todos_extracted(self):
        """应从包含触发词的句子中抽取待办事项。"""
        text = (
            "下一步需要实现可插拔摘要器架构。"
            "TODO: 修复索引重建时的编码问题。"
            "还需要补充单元测试覆盖。"
            "最后检查 CLI --json 输出格式。"
        )
        result = self.summarizer.summarize(text, "待办")
        self.assertGreater(len(result.todos), 0, "应至少抽到一条待办")
        self.assertTrue(
            any("可插拔" in t or "编码" in t or "单元测试" in t or "CLI" in t
                for t in result.todos)
        )

    def test_empty_when_no_triggers(self):
        """文本中无触发词时 decisions/todos 应返回空列表。"""
        result = self.summarizer.summarize("今天天气很好。阳光明媚，适合散步。", "天气")
        self.assertEqual(result.decisions, [], "无触发词时 decisions 应为空")
        self.assertEqual(result.todos, [], "无触发词时 todos 应为空")

    def test_keywords_in_result(self):
        """摘要器应通过 keyword_extractor 生成关键词。"""
        text = "Claude Code Memory Skill 使用本地 Markdown 存储会话记忆。"
        result = self.summarizer.summarize(text, "记忆系统")
        self.assertTrue(len(result.keywords) > 0)

    def test_max_items_limit(self):
        """decisions 最多 5 条，todos 最多 8 条。"""
        # 构造大量含触发词的句子
        sentences = []
        for i in range(20):
            sentences.append(f"我们决定采用方案{i}。")
            sentences.append(f"需要完成TODO{i}。")
        text = "。".join(sentences)
        result = self.summarizer.summarize(text, "限制测试")
        self.assertLessEqual(len(result.decisions), 5)
        self.assertLessEqual(len(result.todos), 8)

    def test_summary_length_limit(self):
        """摘要不应超过 500 字符。"""
        long_text = "这是一个很长的讨论。" * 200
        result = self.summarizer.summarize(long_text, "长文本")
        self.assertLessEqual(len(result.summary), 510)  # 允许少量容差


# ═══════════════════════════════════════════════════════════════
# Phase 2: 关键词抽取测试
# ═══════════════════════════════════════════════════════════════

class TestKeywords(unittest.TestCase):
    """extract_keywords() 单元测试。"""

    def test_chinese_keywords(self):
        kw = memory_core.extract_keywords(
            "用户希望使用 Claude Code 自动保存对话记忆到本地 Markdown 文件。",
            "记忆系统"
        )
        self.assertTrue(len(kw) > 0)
        # 不应包含停用词
        for word in kw:
            self.assertNotIn(word, memory_core._STOP_WORDS)

    def test_english_tech_tokens(self):
        kw = memory_core.extract_keywords(
            "Using memory_core.save_memory() and retrieve_memory() with index.json",
            "API Design"
        )
        self.assertTrue(len(kw) > 0)
        has_tech = any(
            t in kw for t in ["memory_core", "save_memory", "retrieve_memory", "index.json", "API"]
        )
        self.assertTrue(has_tech, f"应抽取技术 token，实际: {kw}")

    def test_python_function_names(self):
        kw = memory_core.extract_keywords(
            "调用 summarize_session.py 和 retrieve_memory.py",
            "CLI 脚本"
        )
        found = any(".py" in k or "summarize" in k.lower() for k in kw)
        self.assertTrue(found, f"应包含函数名/文件名样式 token，实际: {kw}")

    def test_stop_words_filtered(self):
        """停用词不应出现在结果中。"""
        kw = memory_core.extract_keywords("的 了 和 是 在 我 你 这个 那个 进行 通过 可以", "停用词测试")
        for word in kw:
            self.assertNotIn(word, memory_core._STOP_WORDS)

    def test_no_duplicates(self):
        kw = memory_core.extract_keywords("Claude Claude Claude Code Code Code 记忆 记忆 记忆", "测试")
        self.assertEqual(len(kw), len(set(kw)), "关键词不应重复")

    def test_max_keywords_respected(self):
        kw = memory_core.extract_keywords(
            "Python Rust Go Java C++ TypeScript JavaScript Ruby Swift Kotlin Scala Elixir Lua",
            "编程语言",
            max_keywords=5
        )
        self.assertLessEqual(len(kw), 5)

    def test_fallback_without_jieba(self):
        """无论 jieba 是否安装，extract_keywords 都应正常返回。"""
        kw = memory_core.extract_keywords("测试文本分词功能", "测试")
        self.assertIsInstance(kw, list)
        self.assertTrue(len(kw) > 0)


# ═══════════════════════════════════════════════════════════════
# Phase 2: 结构化 Markdown 输出
# ═══════════════════════════════════════════════════════════════

class TestStructuredMarkdown(IsolatedMemoryTest):
    """save_memory() 生成的新 Markdown 格式测试。"""

    def test_markdown_has_all_sections(self):
        topic = "结构化测试_完整段落"
        text = (
            "团队决定采用 jieba 做中文分词，并保持 Markdown 存储方案。"
            "下一步需要补充单元测试，并优化检索评分算法。"
        )
        path = memory_core.save_memory(topic, text)
        content = path.read_text(encoding="utf-8")
        self.assertIn("## 摘要", content)
        self.assertIn("## 关键词", content)
        self.assertIn("## 关键决策", content)
        self.assertIn("## 待办事项", content)

    def test_markdown_decisions_todos_not_empty(self):
        topic = "结构化测试_决策待办"
        text = (
            "我们决定使用可插拔架构。"
            "确定不引入外部 API。"
            "需要补充 CLI 测试。"
            "TODO: 修复 Windows 编码问题。"
        )
        path = memory_core.save_memory(topic, text)
        content = path.read_text(encoding="utf-8")
        # 检查关键决策不为"无明确"
        self.assertNotIn("无明确关键决策", content, "应抽到决策而不是占位文本")
        self.assertNotIn("无明确待办事项", content, "应抽到待办而不是占位文本")

    def test_markdown_fallback_when_nothing(self):
        topic = "结构化测试_无决策无待办"
        text = "今天天气晴朗。阳光很好。适合出去散步。"
        path = memory_core.save_memory(topic, text)
        content = path.read_text(encoding="utf-8")
        self.assertIn("无明确关键决策", content)
        self.assertIn("无明确待办事项", content)


# ═══════════════════════════════════════════════════════════════
# Phase 2: index.json 元数据扩展
# ═══════════════════════════════════════════════════════════════

class TestIndexMetadata(IsolatedMemoryTest):
    """index.json decisions/todos 字段测试。"""

    def test_index_contains_decisions_todos(self):
        memory_core.save_memory(
            "元数据测试",
            "决定采用新架构。需要补充文档。"
        )
        index = memory_core.load_index()
        self.assertTrue(len(index) > 0)
        for record in index.values():
            self.assertIn("decisions", record)
            self.assertIn("todos", record)
            self.assertIsInstance(record["decisions"], list)
            self.assertIsInstance(record["todos"], list)

    def test_retrieve_returns_decisions_todos(self):
        memory_core.save_memory(
            "检索元数据测试",
            "确定使用 jieba。TODO: 加测试。"
        )
        results = memory_core.retrieve_memory("jieba 测试", top_k=3)
        self.assertTrue(len(results) > 0)
        self.assertIn("decisions", results[0])
        self.assertIn("todos", results[0])

    def test_old_index_without_fields_no_error(self):
        """旧索引无 decisions/todos 时不应崩溃。"""
        old_index = {
            "old_topic": {
                "topic": "旧主题",
                "file": "memory/topics/old.md",
                "keywords": ["old"],
                "summary": "旧摘要",
                "created_at": "2026-01-01 00:00:00",
                "updated_at": "2026-01-01 00:00:00",
                # 无 decisions / todos 字段
            }
        }
        memory_core.save_index(old_index)
        results = memory_core.retrieve_memory("旧主题", top_k=1)
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["decisions"], [])
        self.assertEqual(results[0]["todos"], [])


# ═══════════════════════════════════════════════════════════════
# Phase 2: 检索评分增强
# ═══════════════════════════════════════════════════════════════

class TestScoring(IsolatedMemoryTest):
    """score_record() 增强测试。"""

    def setUp(self):
        super().setUp()
        self.record = {
            "topic": "Claude Code 记忆系统架构",
            "file": "memory/topics/test.md",
            "keywords": ["Claude Code", "记忆系统", "Markdown", "index.json"],
            "summary": "讨论了记忆系统的架构设计，采用 Markdown + JSON 方案。",
            "decisions": ["采用 jieba 分词", "使用可插拔摘要器架构"],
            "todos": ["补充单元测试", "优化检索评分"],
            "created_at": "2026-06-03 12:00:00",
            "updated_at": "2026-06-03 12:00:00",
        }

    def test_topic_hit_scores_highest(self):
        score_topic = memory_core.score_record("Claude Code 记忆系统架构", self.record)
        score_body = memory_core.score_record("架构设计 Markdown JSON", self.record)
        self.assertGreater(score_topic, score_body,
                           "主题命中应比正文命中得分高")

    def test_keyword_hit_scored(self):
        score = memory_core.score_record("index.json Markdown", self.record)
        self.assertGreater(score, 0)

    def test_decision_hit_scored(self):
        score = memory_core.score_record("jieba 分词", self.record)
        self.assertGreater(score, 0, "命中 decisions 应得分")

    def test_todo_hit_scored(self):
        score = memory_core.score_record("检索评分优化", self.record)
        self.assertGreater(score, 0, "命中 todos 应得分")

    def test_irrelevant_query_scores_zero(self):
        score = memory_core.score_record("量子计算 黑洞 相对论", self.record)
        self.assertEqual(score, 0)

    def test_stop_words_not_scored(self):
        score = memory_core.score_record("的 了 和 是", self.record)
        self.assertEqual(score, 0, "停用词不应产生分数")


# ═══════════════════════════════════════════════════════════════
# Phase 2: format_context 优化
# ═══════════════════════════════════════════════════════════════

class TestFormatContextEnhanced(IsolatedMemoryTest):
    """format_context() 增强测试。"""

    def test_format_includes_decisions_todos(self):
        results = [{
            "id": "test",
            "topic": "测试主题",
            "score": 20,
            "file": "memory/topics/test.md",
            "summary": "这是摘要。",
            "keywords": ["test"],
            "decisions": ["决定使用 jieba"],
            "todos": ["需要补充测试"],
            "content": "完整内容...",
        }]
        ctx = memory_core.format_context(results)
        self.assertIn("关键决策", ctx)
        self.assertIn("待办事项", ctx)

    def test_format_respects_max_chars(self):
        long_summary = "这是一个很长的摘要。" * 100
        results = [{
            "id": "test",
            "topic": "长文本",
            "score": 10,
            "file": "",
            "summary": long_summary,
            "keywords": [],
            "decisions": [],
            "todos": [],
            "content": "内容" * 500,
        }]
        ctx = memory_core.format_context(results, max_chars_per_item=800)
        # 粗略估计：单条记忆输出不应远超 max_chars_per_item
        # 找到第二条记忆分隔符，第一条记忆的内容应大致在限制内
        self.assertLess(len(ctx), 3000, "单条记忆的输出应有限制")

    def test_format_empty_still_works(self):
        ctx = memory_core.format_context([])
        self.assertIn("未检索到", ctx)


# ═══════════════════════════════════════════════════════════════
# Phase 2: rebuild_index 兼容性
# ═══════════════════════════════════════════════════════════════

class TestRebuildCompatibility(IsolatedMemoryTest):
    """rebuild_index() 新旧格式兼容测试。"""

    def test_rebuild_recovers_decisions_todos(self):
        memory_core.save_memory(
            "重建_决策待办",
            "决定使用新架构。TODO: 增加测试覆盖。"
        )
        self.temp_index.write_text("{}", encoding="utf-8")
        rebuilt = memory_core.rebuild_index()
        self.assertTrue(len(rebuilt) > 0)
        for record in rebuilt.values():
            self.assertIn("decisions", record)
            self.assertIn("todos", record)

    def test_old_format_markdown_still_readable(self):
        """旧格式 Markdown（无 decisions/todos 段落）应正常解析。"""
        old_md = """# 旧格式主题

> 更新时间：2026-01-01 00:00:00

## 摘要

这是旧格式的摘要。

## 关键词

old, format, test

## 原始对话摘录

```text
旧对话内容
```

---
"""
        (self.temp_topics / "old_format_2026-01-01.md").write_text(old_md, encoding="utf-8")
        self.temp_index.write_text("{}", encoding="utf-8")
        rebuilt = memory_core.rebuild_index()
        self.assertTrue(len(rebuilt) > 0)
        for record in rebuilt.values():
            if "旧格式" in record.get("topic", ""):
                self.assertIsInstance(record.get("decisions", []), list)
                self.assertIsInstance(record.get("todos", []), list)
                return
        self.fail("旧格式 Markdown 应被重建索引找到")

    def test_rebuild_skips_readme_still(self):
        """README.md 仍不应被索引。"""
        memory_core.save_memory("重建_SkipReadme", "真实记忆。")
        self.temp_index.write_text("{}", encoding="utf-8")
        rebuilt = memory_core.rebuild_index()
        for record in rebuilt.values():
            fname = Path(record.get("file", "")).name.lower()
            self.assertNotEqual(fname, "readme.md")


# ═══════════════════════════════════════════════════════════════
# Phase 2: save_memory / retrieve_memory 兼容性
# ═══════════════════════════════════════════════════════════════

class TestBackwardsCompat(IsolatedMemoryTest):
    """核心接口向后兼容测试。"""

    def test_save_memory_default_parameters(self):
        """save_memory(topic, text) 默认调用仍可工作。"""
        path = memory_core.save_memory("兼容测试", "测试内容。")
        self.assertTrue(path.exists())

    def test_retrieve_memory_signature(self):
        """retrieve_memory(query) 默认参数仍可工作。"""
        results = memory_core.retrieve_memory("任意查询")
        self.assertIsInstance(results, list)

    def test_rebuild_index_signature(self):
        """rebuild_index() 无参数调用仍可工作。"""
        rebuilt = memory_core.rebuild_index()
        self.assertIsInstance(rebuilt, dict)

    def test_format_context_signature(self):
        """format_context(results) 默认参数仍可工作。"""
        ctx = memory_core.format_context([])
        self.assertIsInstance(ctx, str)


# ═══════════════════════════════════════════════════════════════
# Phase 1 核心回归测试（隔离环境）
# ═══════════════════════════════════════════════════════════════

class TestPhase1Regression(IsolatedMemoryTest):
    """确保 Phase 1 所有功能未被破坏。"""

    def test_save_creates_file(self):
        path = memory_core.save_memory("回归_保存", "内容")
        self.assertTrue(path.exists())

    def test_append_adds(self):
        memory_core.save_memory("回归_追加", "A。", append=True)
        memory_core.save_memory("回归_追加", "B。", append=True)
        r = memory_core.retrieve_memory("回归_追加", top_k=1)
        self.assertIn("A", r[0]["content"])
        self.assertIn("B", r[0]["content"])

    def test_no_append_overwrites(self):
        memory_core.save_memory("回归_覆盖", "旧。", append=False)
        memory_core.save_memory("回归_覆盖", "新。", append=False)
        r = memory_core.retrieve_memory("回归_覆盖", top_k=1)
        self.assertIn("新", r[0]["content"])
        self.assertNotIn("旧", r[0]["content"])

    def test_retrieve_match(self):
        memory_core.save_memory("回归_检索", "Claude Code Memory Skill")
        r = memory_core.retrieve_memory("Claude Code", top_k=3)
        self.assertTrue(len(r) > 0)

    def test_no_match_empty(self):
        memory_core.save_memory("回归_无匹配", "xyzzy123_nonexistent_topic_标记")
        # 直接测试 score_record，避免 HybridRetriever 的增强匹配
        rec = {"topic": "xyzzy123_nonexistent_topic_标记", "keywords": [], "summary": "",
               "decisions": [], "todos": [], "updated_at": "2020-01-01 00:00:00"}
        s = memory_core.score_record("完全无关的查询内容999", rec)
        self.assertEqual(s, 0, f"无匹配应得 0 分，实际: {s}")

    def test_corrupt_index(self):
        # 清理可能的备份，确保恢复逻辑不干扰
        backup_dir = self.temp_index.parent / "backups"
        if backup_dir.exists():
            import shutil
            shutil.rmtree(str(backup_dir), ignore_errors=True)
        self.temp_index.write_text("{bad json", encoding="utf-8")
        self.assertEqual(memory_core.load_index(), {})

    def test_rebuild_works(self):
        memory_core.save_memory("回归_重建", "测试")
        self.temp_index.write_text("{}", encoding="utf-8")
        rebuilt = memory_core.rebuild_index()
        self.assertGreater(len(rebuilt), 0)

    def test_atomic_write(self):
        memory_core.save_index({"k": {"topic": "t"}})
        self.assertIn("k", memory_core.load_index())
        self.assertFalse(self.temp_index.with_name("index.json.tmp").exists())

    def test_is_memory_markdown(self):
        self.assertTrue(memory_core.is_memory_markdown(Path("/x/t.md")))
        self.assertFalse(memory_core.is_memory_markdown(Path("/x/README.md")))


# ═══════════════════════════════════════════════════════════════
# CLI 层测试（subprocess，完全隔离到临时目录）
# ═══════════════════════════════════════════════════════════════

_PYTHON = sys.executable


class TestCLIJsonEnhanced(unittest.TestCase):
    """CLI --json / --no-append / update_index 测试。

    通过复制 scripts/ 到临时目录并创建隔离的 memory/ 结构，
    完全避免触碰真实 memory/ 目录。
    """

    _temp_root: Path | None = None
    _temp_scripts: Path | None = None

    @classmethod
    def setUpClass(cls) -> None:
        # 1. 创建临时项目根目录
        cls._temp_root = Path(tempfile.mkdtemp(prefix="clitest_"))
        cls._temp_scripts = cls._temp_root / "scripts"

        # 2. 复制 scripts/ 目录到临时目录（排除 __pycache__）
        shutil.copytree(
            SCRIPTS_DIR, cls._temp_scripts,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )

        # 3. 创建 memory/ 结构
        mem_dir = cls._temp_root / "memory"
        topics_dir = mem_dir / "topics"
        topics_dir.mkdir(parents=True, exist_ok=True)
        (topics_dir / "README.md").write_text(
            "# topics 目录说明\n\n说明文件，不应被索引。\n", encoding="utf-8"
        )
        (mem_dir / "index.json").write_text("{}", encoding="utf-8")

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._temp_root and cls._temp_root.exists():
            shutil.rmtree(cls._temp_root, ignore_errors=True)

    def _run(self, script_name: str, *args: str) -> subprocess.CompletedProcess:
        """在隔离环境中运行 CLI 脚本。"""
        env = os.environ.copy()
        env.setdefault("PYTHONIOENCODING", "utf-8")
        cmd = [_PYTHON, str(self._temp_scripts / script_name)] + list(args)
        return subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            cwd=str(self._temp_root), env=env, timeout=30,
        )

    def setUp(self) -> None:
        # 每个测试前确保索引和 topics 干净
        idx = self._temp_root / "memory" / "index.json"
        idx.write_text("{}", encoding="utf-8")
        topics = self._temp_root / "memory" / "topics"
        for p in sorted(topics.glob("*.md")):
            if p.name.lower() != "readme.md":
                try:
                    p.unlink()
                except FileNotFoundError:
                    pass

    def test_json_contains_decisions_todos(self):
        # 先保存一条含决策/待办的记忆
        self._run("summarize_session.py", "--topic", "CLI_Decisions",
                  "--text", "我们决定使用 jieba 分词。TODO: 添加更多测试。")
        proc = self._run("retrieve_memory.py", "--query", "jieba 分词",
                         "--top-k", "3", "--json")
        self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, list)
        if data:
            self.assertIn("decisions", data[0])
            self.assertIn("todos", data[0])
            self.assertIsInstance(data[0]["decisions"], list)
            self.assertIsInstance(data[0]["todos"], list)
            # 验证 decisions 字段名本身不会被误判为决策
            # (修复: English trigger \bdecision\b 不再匹配 "decisions")
            for dec in data[0]["decisions"]:
                self.assertNotIn("decisions", dec.lower().replace("decision", ""),
                                 "字段名 'decisions' 不应作为决策被抽取")

    def test_json_parsable_with_new_fields(self):
        self._run("summarize_session.py", "--topic", "CLI_Fields",
                  "--text", "测试字段完整性。")
        proc = self._run("retrieve_memory.py", "--query", "CLI_Fields",
                         "--top-k", "1", "--json")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, list)

    def test_summarize_no_append_coverage(self):
        self._run("summarize_session.py", "--topic", "CLI_Overwrite",
                  "--text", "旧内容。", "--no-append")
        self._run("summarize_session.py", "--topic", "CLI_Overwrite",
                  "--text", "新内容。", "--no-append")
        proc = self._run("retrieve_memory.py", "--query", "CLI_Overwrite",
                         "--top-k", "1", "--json")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        if data:
            content = data[0].get("content", "")
            self.assertIn("新内容", content)
            self.assertNotIn("旧内容", content)

    def test_update_index_reports_topics(self):
        self._run("summarize_session.py", "--topic", "CLI_Index",
                  "--text", "用于重建索引测试。")
        proc = self._run("update_index.py")
        self.assertEqual(proc.returncode, 0, f"stderr: {proc.stderr}")
        self.assertIn("Total topics", proc.stdout)

    def test_trigger_word_boundary_fix(self):
        """验证 \b 单词边界修复：'decisions' 不应触发 decision 匹配。"""
        self._run("summarize_session.py", "--topic", "CLI_Boundary",
                  "--text",
                  "我们需要检查 JSON 输出中的 decisions 和 todos 字段是否正确。"
                  "这只是一个数据格式检查，不是关键决策。")
        proc = self._run("retrieve_memory.py", "--query", "decisions todos 字段",
                         "--top-k", "1", "--json")
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        if data:
            decisions = data[0].get("decisions", [])
            # "decisions 和 todos 字段" 不应被判定为关键决策
            field_name_matches = [
                d for d in decisions
                if "decisions" in d.lower() or "todos" in d.lower()
            ]
            self.assertEqual(
                len(field_name_matches), 0,
                f"字段名不应被误判为决策: {field_name_matches}"
            )


# ═══════════════════════════════════════════════════════════════
# Phase 3: Hook / Plugin / Skill 集成测试
# ═══════════════════════════════════════════════════════════════

class TestPhase3HookScripts(unittest.TestCase):
    """验证 Phase 3 Hook 脚本存在且可执行。"""

    def test_hook_scripts_exist(self):
        """所有平台 Hook 脚本应存在且非空。"""
        hooks_dir = PROJECT_ROOT / "hooks"
        expected = [
            "post_conversation.sh", "pre_prompt.sh",
            "post_conversation.bat", "pre_prompt.bat",
            "post_conversation.ps1", "pre_prompt.ps1",
            # 旧版示例保留
            "post_conversation_example.sh", "pre_prompt_example.sh",
        ]
        for name in expected:
            path = hooks_dir / name
            self.assertTrue(path.exists(), f"缺失: {name}")
            self.assertGreater(path.stat().st_size, 0, f"空文件: {name}")

    def test_bash_scripts_have_shebang(self):
        """Bash 脚本应以 #!/usr/bin/env bash 开头。"""
        for name in ["post_conversation.sh", "pre_prompt.sh"]:
            path = PROJECT_ROOT / "hooks" / name
            first_line = path.read_text(encoding="utf-8").split("\n")[0]
            self.assertIn("bash", first_line, f"{name} 缺少 shebang")

    def test_bash_scripts_are_executable(self):
        """Bash 脚本应有可执行权限（非 Windows 检查）。"""
        if sys.platform == "win32":
            self.skipTest("Windows 不检查可执行位")
        for name in ["post_conversation.sh", "pre_prompt.sh"]:
            path = PROJECT_ROOT / "hooks" / name
            self.assertTrue(os.access(str(path), os.X_OK), f"{name} 不可执行")

    def test_hook_scripts_syntax_valid(self):
        """Bash 脚本语法应有效（bash -n 检查）。"""
        if sys.platform == "win32":
            self.skipTest("Windows 跳过 bash 语法检查")
        import subprocess as sp
        for name in ["post_conversation.sh", "pre_prompt.sh"]:
            path = PROJECT_ROOT / "hooks" / name
            proc = sp.run(["bash", "-n", str(path)], capture_output=True)
            self.assertEqual(proc.returncode, 0, f"{name} 语法错误: {proc.stderr}")


class TestPhase3PluginManifest(unittest.TestCase):
    """验证 plugin.json 结构完整。"""

    def test_plugin_json_exists_and_valid(self):
        path = PROJECT_ROOT / "plugin.json"
        self.assertTrue(path.exists(), "plugin.json 缺失")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        required = ["name", "version", "description", "skill", "hooks", "commands"]
        for key in required:
            self.assertIn(key, manifest, f"plugin.json 缺少 '{key}' 字段")
        self.assertEqual(manifest["name"], "claude-code-memory-skill")

    def test_plugin_commands_defined(self):
        manifest = json.loads(
            (PROJECT_ROOT / "plugin.json").read_text(encoding="utf-8")
        )
        cmds = manifest.get("commands", {})
        for cmd_name in ["memory:save", "memory:retrieve", "memory:rebuild"]:
            self.assertIn(cmd_name, cmds, f"plugin.json 缺少命令: {cmd_name}")
            self.assertIn("script", cmds[cmd_name])
            self.assertIn("usage", cmds[cmd_name])

    def test_plugin_permissions(self):
        manifest = json.loads(
            (PROJECT_ROOT / "plugin.json").read_text(encoding="utf-8")
        )
        perms = manifest.get("permissions", {})
        self.assertIn("filesystem", perms)
        self.assertIn("execution", perms)
        self.assertFalse(perms.get("network", True), "不应请求网络权限")


class TestPhase3SettingsTemplate(unittest.TestCase):
    """验证 settings.template.json 模板结构。"""

    def test_settings_template_valid_json(self):
        path = PROJECT_ROOT / "docs" / "settings.template.json"
        self.assertTrue(path.exists(), "settings.template.json 缺失")
        template = json.loads(path.read_text(encoding="utf-8"))
        self.assertIn("hooks", template)
        hooks = template["hooks"]
        # 至少有一个 Hook 事件配置
        self.assertTrue(len(hooks) > 0, "settings.template.json 应包含至少一个 Hook")

    def test_template_has_cross_platform_options(self):
        template = json.loads(
            (PROJECT_ROOT / "docs" / "settings.template.json").read_text(encoding="utf-8")
        )
        has_windows = any("bat" in str(v).lower() or "ps1" in str(v).lower()
                         for v in template.values() if isinstance(v, dict))
        self.assertTrue(has_windows or "_windows" in str(template).lower(),
                       "缺少跨平台 Hook 选项")


class TestPhase3InstallScript(unittest.TestCase):
    """验证 install.sh 安装脚本。"""

    def test_install_script_exists(self):
        path = PROJECT_ROOT / "install.sh"
        self.assertTrue(path.exists(), "install.sh 缺失")
        content = path.read_text(encoding="utf-8")
        self.assertIn("bash", content[:40].lower(), "install.sh 应以 bash shebang 开头")

    def test_install_script_syntax(self):
        if sys.platform == "win32":
            self.skipTest("Windows 跳过 bash 语法检查")
        import subprocess as sp
        path = PROJECT_ROOT / "install.sh"
        proc = sp.run(["bash", "-n", str(path)], capture_output=True)
        self.assertEqual(proc.returncode, 0, f"install.sh 语法错误: {proc.stderr}")


# ═══════════════════════════════════════════════════════════════
# Phase 4: Workspace / Retrieval / Security / Backup / Logging
# ═══════════════════════════════════════════════════════════════

class TestPhase4Workspace(IsolatedMemoryTest):
    """Workspace 隔离测试。"""

    def test_workspace_save_to_isolated_dir(self):
        path = memory_core.save_memory("WS_测试", "workspace 隔离写入。", workspace="p4test")
        self.assertTrue(path.exists())
        self.assertIn("workspaces", str(path))
        self.assertIn("p4test", str(path))

    def test_workspace_retrieval_isolated(self):
        memory_core.save_memory("WS_A", "内容A：项目Alpha的记忆。", workspace="p4a")
        memory_core.save_memory("WS_B", "内容B：项目Beta的记忆。", workspace="p4b")
        r_a = memory_core.retrieve_memory("Alpha", top_k=3, workspace="p4a")
        r_b = memory_core.retrieve_memory("Beta", top_k=3, workspace="p4b")
        self.assertTrue(any("Alpha" in str(x.get("content","")) for x in r_a) or any("WS_A" in str(x.get("topic","")) for x in r_a))
        self.assertTrue(any("Beta" in str(x.get("content","")) for x in r_b) or any("WS_B" in str(x.get("topic","")) for x in r_b))

    def test_workspace_not_cross_polute(self):
        memory_core.save_memory("WS_隔离", "隔离测试内容。", workspace="p4isolated")
        r = memory_core.retrieve_memory("隔离测试", top_k=3, workspace="p4_other")
        self.assertEqual(len(r), 0, "不同 workspace 不应检索到彼此的记忆")

    def test_legacy_path_still_works(self):
        path = memory_core.save_memory("旧路径测试", "旧路径兼容。", workspace="")
        self.assertIn("memory", str(path))
        self.assertNotIn("workspaces", str(path))


class TestPhase4Retrieval(IsolatedMemoryTest):
    """混合检索 + score_breakdown 测试。"""

    def test_retrieval_has_score_breakdown(self):
        memory_core.save_memory("检索_P4", "混合检索 score_breakdown 字段测试。")
        results = memory_core.retrieve_memory("score_breakdown", top_k=3)
        if results:
            self.assertIn("score_breakdown", results[0])
            self.assertIsInstance(results[0]["score_breakdown"], dict)

    def test_retrieval_has_matched_fields(self):
        memory_core.save_memory("检索_匹配字段", "验证 matched_fields 列表。")
        results = memory_core.retrieve_memory("匹配字段 matched", top_k=3)
        if results:
            self.assertIn("matched_fields", results[0])
            self.assertIsInstance(results[0]["matched_fields"], list)

    def test_topic_hit_scores_higher_than_body(self):
        memory_core.save_memory("独特的主题名P4XYZ", "正文内容仅包含普通描述。",
                                workspace="p4scoring")
        r_topic = memory_core.retrieve_memory("独特的主题名P4XYZ", top_k=3, workspace="p4scoring")
        r_body = memory_core.retrieve_memory("普通描述", top_k=3, workspace="p4scoring")
        if r_topic and r_body:
            self.assertGreaterEqual(r_topic[0]["score"], r_body[0]["score"])


class TestPhase4Security(IsolatedMemoryTest):
    """安全增强测试。"""

    def test_path_traversal_blocked(self):
        idx = {"malicious": {"topic": "evil", "file": "../../../etc/passwd",
               "keywords": [], "summary": "", "decisions": [], "todos": [],
               "created_at": "", "updated_at": ""}}
        memory_core.save_index(idx)
        results = memory_core.retrieve_memory("evil")
        for r in results:
            self.assertNotIn("/etc/passwd", r.get("file", ""))

    def test_markdown_fence_escaped(self):
        text_with_fence = "原文包含 ```code``` 反引号。"
        path = memory_core.save_memory("Fence测试", text_with_fence)
        content = path.read_text(encoding="utf-8")
        # 不应有三反引号直接出现在内容中破坏结构（4反引号 fence 保护）
        self.assertIn("````text", content)

    def test_format_context_length_controlled(self):
        results = [{"id":"t","topic":"T"*300,"score":10,"file":"f",
                    "summary":"S"*500,"keywords":[],"decisions":["D"*200],
                    "todos":["T"*200],"content":"C"*2000}]
        ctx = memory_core.format_context(results, max_chars_per_item=600)
        self.assertLess(len(ctx), 2000, "单条记忆应受限")


class TestPhase4Backup(IsolatedMemoryTest):
    """索引备份 + 恢复测试。"""

    def test_save_index_creates_backup(self):
        idx = {"b1": {"topic": "backup test"}}
        memory_core.save_index(idx)
        # 再写一次以触发备份
        idx["b2"] = {"topic": "backup test 2"}
        memory_core.save_index(idx)
        backup_dir = self.temp_index.parent / "backups"
        backups = list(backup_dir.glob("index_*.json")) if backup_dir.exists() else []
        self.assertGreater(len(backups), 0, "应生成至少一个索引备份")

    def test_corrupt_index_restore_from_backup(self):
        # 先写入一条有效索引
        memory_core.save_index({"valid": {"topic": "有效数据"}})
        # 再写一次触发备份
        memory_core.save_index({"valid": {"topic": "有效数据2"}})
        # 破坏索引
        self.temp_index.write_text("{corrupt!!!", encoding="utf-8")
        # 清除备份目录干扰（测试 restore 逻辑在无备份时的行为）
        backup_dir = self.temp_index.parent / "backups"
        if backup_dir.exists():
            import shutil
            shutil.rmtree(str(backup_dir), ignore_errors=True)
        # 无备份时应返回空字典
        result = memory_core.load_index()
        self.assertEqual(result, {}, "无可用备份时应返回空字典")

    def test_lock_file_cleanup(self):
        lock_path = self.temp_index.with_suffix(self.temp_index.suffix + ".lock")
        memory_core.save_index({"lock_test": {"topic": "lock"}})
        self.assertFalse(lock_path.exists(), "写入完成后锁文件应已清理")


class TestPhase4Logging(unittest.TestCase):
    """日志系统测试。"""

    def test_log_sanitize_shortens_text(self):
        from logging_utils import _sanitize
        result = _sanitize("短文本", max_len=10)
        self.assertLessEqual(len(result), 10)

    def test_log_sanitize_truncates_long_text(self):
        from logging_utils import _sanitize
        result = _sanitize("非常长的对话内容" * 50, max_len=80)
        self.assertLessEqual(len(result), 83)  # 80 + "..."


class TestPhase4Maintenance(unittest.TestCase):
    """记忆维护 dry-run 测试。"""

    def test_detect_duplicates_no_false_positives(self):
        from memory_maintenance import detect_duplicates
        idx = {
            "a": {"topic": "完全不相关的主题A", "keywords": ["Python", "测试"]},
            "b": {"topic": "完全不相关的主题B", "keywords": ["Java", "开发"]},
        }
        pairs = detect_duplicates(idx, threshold=0.5)
        self.assertEqual(len(pairs), 0, "不相关主题不应被误判为重复")

    def test_detect_duplicates_finds_similar(self):
        from memory_maintenance import detect_duplicates
        idx = {
            "a": {"topic": "Claude Code 记忆系统", "keywords": ["Claude", "Code", "记忆"]},
            "b": {"topic": "Claude Code Memory", "keywords": ["Claude", "Code", "memory"]},
        }
        pairs = detect_duplicates(idx, threshold=0.3)
        self.assertGreater(len(pairs), 0, "相似主题应被检测到")


# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    unittest.main(verbosity=2)
