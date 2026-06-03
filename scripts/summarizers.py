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
    r"confirmed|decided|decision|use|choose|finalize|agree|conclusion)",
    re.IGNORECASE,
)

_TODO_TRIGGERS = re.compile(
    r"(需要|下一步|待办|修复|补充|优化|增加|测试|检查|实现|完善|"
    r"TODO|FIXME|HACK|XXX|"
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
