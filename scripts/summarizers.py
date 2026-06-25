"""
summarizers.py

可插拔摘要器模块。

提供：
  - SummaryResult: 结构化摘要结果
  - BaseSummarizer: 摘要器抽象基类
  - RuleBasedSummarizer: 基于规则的本地摘要器

后续可接入 LLM 摘要器，只需实现 BaseSummarizer 接口即可。
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


# ═══════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════

@dataclass
class SummaryResult:
    """结构化摘要结果。"""

    summary: str = ""
    decisions: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# 抽象基类
# ═══════════════════════════════════════════════════════════════

class BaseSummarizer(ABC):
    """摘要器抽象基类。

    子类只需实现 summarize() 方法。后续接入 LLM 摘要器时，
    创建新类实现此接口即可，无需修改 memory_core 调用方。
    """

    @abstractmethod
    def summarize(self, text: str, topic: str = "") -> SummaryResult:
        """从文本生成结构化摘要。

        Args:
            text: 待摘要的原始文本。
            topic: 可选的主题提示，帮助摘要器聚焦。

        Returns:
            SummaryResult，包含 summary、decisions、todos、keywords。
        """
        ...


# ═══════════════════════════════════════════════════════════════
# 基于规则的本地摘要器
# ═══════════════════════════════════════════════════════════════

# ── 关键词触发词表 ──────────────────────────────────────────

_DECISION_TRIGGERS = re.compile(
    r"(决定|确定|采用|选择|保持|不再|改为|结论|同意|确认|最终|方案|"
    r"\bconfirmed\b|\bdecided\b|\bdecision\b|\buse\b|\bchoose\b|"
    r"\bfinalize\b|\bagree\b|\bconclusion\b)",
    re.IGNORECASE,
)

_TODO_TRIGGERS = re.compile(
    r"(需要|下一步|待办|修复|补充|优化|增加|测试|检查|实现|完善|"
    r"\bTODO\b|\bFIXME\b|\bHACK\b|\bXXX\b|"
    r"\bfix\b|\badd\b|\btest\b|\bcheck\b|\bimplement\b|\bupdate\b|\bremove\b)",
    re.IGNORECASE,
)

# ── 句子分割 ─────────────────────────────────────────────────

_SENTENCE_SPLIT = re.compile(r"[。！？；\n](?=\s*[^\s])|\.\s+(?=[A-Z])|!\s+|;\s+")


def _split_sentences(text: str) -> list[str]:
    """将文本分割为句子列表。"""
    # 先规范化空白
    text = re.sub(r"\s*\n\s*\n\s*", "\n", text)
    text = re.sub(r"```[^`]*```", " ", text)  # 移除代码块
    text = re.sub(r"`[^`]*`", " ", text)       # 移除行内代码
    text = re.sub(r"\s+", " ", text)            # 合并空白

    raw = _SENTENCE_SPLIT.split(text)
    sentences = []
    for s in raw:
        s = s.strip()
        if not s:
            continue
        # 合并过短的片段到前一句
        if len(s) < 4 and sentences:
            sentences[-1] = sentences[-1] + s
        else:
            sentences.append(s)
    return sentences


# ── 摘要生成 ─────────────────────────────────────────────────

def _generate_summary(sentences: list[str], max_chars: int = 500) -> str:
    """从句子列表中生成紧凑摘要。

    取前 3~5 个有效句子，控制在 max_chars 以内。
    """
    if not sentences:
        return ""

    selected = []
    total = 0
    max_sentences = min(5, len(sentences))
    for s in sentences[:max_sentences]:
        if total + len(s) > max_chars:
            # 如果能截断放进去
            remaining = max_chars - total
            if remaining > 30:
                selected.append(s[:remaining].rstrip() + "…")
            break
        selected.append(s)
        total += len(s)
        if total >= max_chars:
            break

    result = "。".join(selected) if selected else sentences[0][:max_chars]
    if len(result) > max_chars:
        result = result[:max_chars].rstrip() + "…"
    return result


# ── 决策抽取 ─────────────────────────────────────────────────

def _extract_decisions(sentences: list[str], max_items: int = 5) -> list[str]:
    """从句子中抽取关键决策。"""
    decisions = []
    for s in sentences:
        if _DECISION_TRIGGERS.search(s):
            clean = s.strip()
            if len(clean) > 120:
                clean = clean[:120].rstrip() + "…"
            decisions.append(clean)
            if len(decisions) >= max_items:
                break
    return decisions


# ── 待办抽取 ─────────────────────────────────────────────────

def _extract_todos(sentences: list[str], max_items: int = 8) -> list[str]:
    """从句子中抽取待办事项。"""
    # 也检测以 - * 1. 开头的列表项
    list_item = re.compile(r"^\s*[-*•]\s+", re.UNICODE)

    todos = []
    for s in sentences:
        is_list = bool(list_item.match(s))
        is_todo = bool(_TODO_TRIGGERS.search(s))
        if is_todo or (is_list and len(s) > 6):
            clean = s.strip()
            # 去掉列表标记
            clean = list_item.sub("", clean).strip()
            if len(clean) > 150:
                clean = clean[:150].rstrip() + "…"
            if clean and clean not in todos:
                todos.append(clean)
                if len(todos) >= max_items:
                    break
    return todos


# ═══════════════════════════════════════════════════════════════
# RuleBasedSummarizer
# ═══════════════════════════════════════════════════════════════

class RuleBasedSummarizer(BaseSummarizer):
    """基于规则的本地摘要器。

    不依赖任何外部 API 或模型。
    使用触发词表 + 句子分割做结构化抽取。

    工作流程：
      1. 分割文本为句子
      2. 取前 N 句生成摘要
      3. 匹配触发词抽取关键决策
      4. 匹配触发词抽取待办事项
      5. 调用外部 extract_keywords（注入依赖以避免循环导入）
    """

    def __init__(self, keyword_extractor=None):
        """
        Args:
            keyword_extractor: 可选的关键词抽取函数。
                签名为 (text: str, topic: str, max_keywords: int) -> list[str]。
                如果为 None，则不生成 keywords。
        """
        self._keyword_extractor = keyword_extractor

    def summarize(self, text: str, topic: str = "") -> SummaryResult:
        sentences = _split_sentences(text)

        summary = _generate_summary(sentences, max_chars=500)
        decisions = _extract_decisions(sentences)
        todos = _extract_todos(sentences)

        keywords: list[str] = []
        if self._keyword_extractor:
            keywords = self._keyword_extractor(text, topic)

        return SummaryResult(
            summary=summary,
            decisions=decisions,
            todos=todos,
            keywords=keywords,
        )


# ═══════════════════════════════════════════════════════════════
# EnhancedSummaryResult — LLM 摘要增强输出
# ═══════════════════════════════════════════════════════════════

@dataclass
class EnhancedSummaryResult(SummaryResult):
    """增强摘要结果，包含 LLM 元数据。

    继承 SummaryResult 保持向后兼容。
    """
    key_points: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    confidence: float = 1.0
    partial: bool = False
    metadata: dict = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════
# LLMSummarizer — LLM 语义摘要器
# ═══════════════════════════════════════════════════════════════

class LLMSummarizer(BaseSummarizer):
    """基于 LLM 的语义摘要器。

    实现了 BaseSummarizer 接口，可无缝替换 RuleBasedSummarizer。
    支持 3 类摘要模式：brief / semantic / memory。
    无 LLM provider 时自动降级为规则摘要器。

    工作流程：
      1. 检测文本长度，超阈值时分块
      2. 逐块调用 LLM 生成摘要
      3. 合并多块摘要（去重 + 保留关键约束）
      4. 输出 EnhancedSummaryResult
    """

    MAX_CHUNK_CHARS = 4000  # 单块最大字符数（约 1000 tokens）

    def __init__(
        self,
        provider=None,
        keyword_extractor=None,
        fallback_summarizer=None,
    ):
        """
        Args:
            provider: LLMProvider 实例，为 None 时使用规则 fallback。
            keyword_extractor: 可选的关键词抽取函数。
            fallback_summarizer: RuleBasedSummarizer 实例，默认自动创建。
        """
        self._provider = provider
        self._keyword_extractor = keyword_extractor
        self._fallback = fallback_summarizer or RuleBasedSummarizer(
            keyword_extractor=keyword_extractor
        )

    def summarize(
        self, text: str, topic: str = "", summary_type: str = "semantic"
    ) -> EnhancedSummaryResult:
        """生成 LLM 语义摘要。

        Args:
            text: 原始文本。
            topic: 主题提示。
            summary_type: "brief" / "semantic" / "memory"。

        Returns:
            EnhancedSummaryResult。
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # LLM 不可用时降级
        if self._provider is None:
            return self._fallback_summarize(text, topic, summary_type, now)

        # 长文本分块
        text_clean = _clean_for_summary(text)
        if len(text_clean) <= self.MAX_CHUNK_CHARS:
            return self._llm_summarize(text_clean, topic, summary_type, now, partial=False)

        # chunk → summary → merge
        chunks = self._chunk_text(text_clean)
        chunk_results = []
        for ch in chunks:
            try:
                r = self._llm_summarize(ch, topic, summary_type, now, partial=True)
                chunk_results.append(r)
            except Exception:
                # 单块失败时回退到规则摘要
                r = self._fallback_summarize(ch, topic, summary_type, now)
                chunk_results.append(r)

        return self._merge_chunk_results(chunk_results, topic, summary_type, now)

    def _llm_summarize(
        self, text: str, topic: str, summary_type: str, now: str, partial: bool
    ) -> EnhancedSummaryResult:
        """单次 LLM 摘要调用。"""
        import re

        prompt = self._build_prompt(text, topic, summary_type)
        try:
            response = self._provider.complete(prompt, task="summarize")
        except Exception:
            # LLM 调用异常，回退
            return self._fallback_summarize(text, topic, summary_type, now)

        # 从 LLM 响应中提取结构化内容
        entities = _extract_entities(response)
        key_points = _extract_key_points(response)
        open_qs = _extract_open_questions(response)

        # 使用规则抽取器生成 decisions/todos/keywords 以获得兼容字段
        rule_result = self._fallback.summarize(text, topic)

        return EnhancedSummaryResult(
            summary=response[:500],
            decisions=rule_result.decisions[:5],
            todos=rule_result.todos[:8],
            keywords=rule_result.keywords,
            key_points=key_points,
            entities=entities,
            open_questions=open_qs,
            confidence=0.7,
            partial=partial,
            metadata={
                "model": getattr(self._provider, "model_name", "unknown"),
                "provider": type(self._provider).__name__,
                "summary_type": summary_type,
                "mode": "llm",
                "created_at": now,
            },
        )

    def _fallback_summarize(
        self, text: str, topic: str, summary_type: str, now: str
    ) -> EnhancedSummaryResult:
        """降级到规则摘要。"""
        result = self._fallback.summarize(text, topic)
        return EnhancedSummaryResult(
            summary=result.summary,
            decisions=result.decisions,
            todos=result.todos,
            keywords=result.keywords,
            partial=False,
            metadata={
                "model": "rule-based",
                "provider": "RuleBasedSummarizer",
                "summary_type": summary_type,
                "mode": "rule_fallback",
                "created_at": now,
            },
        )

    def _build_prompt(self, text: str, topic: str, summary_type: str) -> str:
        if summary_type == "brief":
            return (
                f"请用 2-3 句话简洁总结以下对话内容（主题: {topic}）：\n\n{text}"
            )
        elif summary_type == "memory":
            return (
                f"从以下对话中提取可复用的记忆信息（主题: {topic}）：\n\n"
                f"请保留：项目状态、用户偏好、关键决策、待办线索、"
                f"技术实体（文件名/模块名/版本号/API名）。\n"
                f"不确定的地方标记 [不确定]。\n\n{text}"
            )
        else:  # semantic
            return (
                f"请总结以下对话内容（主题: {topic}）：\n\n"
                f"包含：任务目标、关键约束、决策、结论。\n"
                f"只输出原文中存在的内容，不要编造。\n\n{text}"
            )

    def _chunk_text(self, text: str) -> list[str]:
        """将文本按句子边界分块。"""
        import re
        sentences = re.split(r"(?<=[。！？；])\s*", text)
        chunks = []
        current = ""
        for s in sentences:
            if len(current) + len(s) > self.MAX_CHUNK_CHARS and current:
                chunks.append(current)
                current = s
            else:
                current += s
        if current.strip():
            chunks.append(current)
        return chunks

    def _merge_chunk_results(
        self,
        results: list[EnhancedSummaryResult],
        topic: str,
        summary_type: str,
        now: str,
    ) -> EnhancedSummaryResult:
        """合并多块摘要结果。"""
        if not results:
            return EnhancedSummaryResult(
                summary="", metadata={"mode": "rule_fallback", "created_at": now}
            )
        if len(results) == 1:
            return results[0]

        # 合并
        summaries = [r.summary for r in results if r.summary]
        all_decisions = []
        all_todos = []
        all_keywords = []
        all_entities = []
        all_key_points = []
        all_questions = []

        for r in results:
            all_decisions.extend(r.decisions)
            all_todos.extend(r.todos)
            all_keywords.extend(r.keywords)
            all_entities.extend(r.entities)
            all_key_points.extend(r.key_points)
            all_questions.extend(r.open_questions)

        # 去重
        seen = set()
        decisions = [d for d in all_decisions if not (d in seen or seen.add(d))][:5]
        seen.clear()
        todos = [t for t in all_todos if not (t in seen or seen.add(t))][:8]
        seen.clear()
        keywords = [k for k in all_keywords if not (k in seen or seen.add(k))][:10]
        seen.clear()
        entities = [e for e in all_entities if not (e in seen or seen.add(e))][:10]
        seen.clear()
        key_points = [p for p in all_key_points if not (p in seen or seen.add(p))][:5]
        seen.clear()
        questions = [q for q in all_questions if not (q in seen or seen.add(q))][:3]

        merged_summary = "。".join(summaries[:5])
        if len(merged_summary) > 800:
            merged_summary = merged_summary[:797] + "..."

        return EnhancedSummaryResult(
            summary=merged_summary,
            decisions=decisions,
            todos=todos,
            keywords=keywords,
            key_points=key_points,
            entities=entities,
            open_questions=questions,
            confidence=0.6,
            partial=True,
            metadata={
                "model": results[0].metadata.get("model", "unknown"),
                "provider": results[0].metadata.get("provider", "unknown"),
                "summary_type": summary_type,
                "mode": "llm_chunked",
                "chunks": len(results),
                "partial": True,
                "created_at": now,
            },
        )


# ═══════════════════════════════════════════════════════════════
# LLM 响应解析辅助函数
# ═══════════════════════════════════════════════════════════════

def _clean_for_summary(text: str) -> str:
    """清理文本用于摘要（移除代码块，规范化空白）。"""
    import re
    text = re.sub(r"```[^`]*```", " [代码块] ", text)
    text = re.sub(r"`[^`]*`", " [代码] ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_entities(text: str) -> list[str]:
    """从文本中提取技术实体。"""
    import re
    patterns = [
        r"\b\w+\.py\b", r"\b\w+\.json\b", r"\b\w+\.md\b",
        r"\b\w+\.sh\b", r"\b\w+\.bat\b", r"\b\w+\.ps1\b",
        r"v\d+\.\d+\.\d+", r"Phase\s*\d+",
        r"\b[A-Z][a-z]+[A-Z]\w*\b",
    ]
    entities = set()
    for pat in patterns:
        found = re.findall(pat, text)
        entities.update(found)
    return sorted(entities)[:10]


def _extract_key_points(text: str) -> list[str]:
    """从文本中提取关键点。"""
    import re
    lines = text.replace("\n", " ").split("。")
    key_words = ["关键", "重要", "核心", "必须", "要求", "目标", "约束"]
    points = []
    for line in lines:
        for kw in key_words:
            if kw in line:
                points.append(line.strip()[:150])
                break
    return points[:5]


def _extract_open_questions(text: str) -> list[str]:
    """从文本中提取开放问题。"""
    import re
    lines = text.replace("\n", " ").split("。")
    question_words = ["不确定", "待定", "需要进一步", "需要确认",
                     "TBD", "unknown", "需要讨论"]
    questions = []
    for line in lines:
        for kw in question_words:
            if kw in line:
                questions.append(line.strip()[:150])
                break
    return questions[:3]
