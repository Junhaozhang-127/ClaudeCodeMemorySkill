"""
retrieval.py — 可插拔检索器架构

提供：
  - BaseRetriever: 检索器抽象基类
  - KeywordRetriever: 封装现有 score_record() 逻辑
  - HybridRetriever: 多信号混合检索 + score_breakdown
  - EmbeddingRetriever: 向量检索占位接口（未来接入）

不依赖任何向量库或外部 API。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable


class BaseRetriever(ABC):
    """检索器抽象基类。"""

    @abstractmethod
    def retrieve(
        self, query: str, records: Iterable[dict], top_k: int = 5
    ) -> list[dict]:
        """返回按相关性排序的结果列表。"""
        ...


# ═══════════════════════════════════════════════════════════════
# KeywordRetriever — 封装现有评分逻辑
# ═══════════════════════════════════════════════════════════════

class KeywordRetriever(BaseRetriever):
    """基于关键词加权匹配的检索器。

    将现有 score_record() 逻辑封装为 BaseRetriever 接口。
    """

    def __init__(self, score_fn):
        """
        Args:
            score_fn: 评分函数，签名 (query: str, record: dict) -> int。
        """
        self._score_fn = score_fn

    def retrieve(
        self, query: str, records: Iterable[dict], top_k: int = 5
    ) -> list[dict]:
        scored = []
        for record in records:
            score = self._score_fn(query, record)
            if score <= 0:
                continue
            item = dict(record)
            item["score"] = score
            item["score_breakdown"] = {"total": score}
            item["matched_fields"] = _detect_matched_fields(query, record)
            scored.append(item)
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


# ═══════════════════════════════════════════════════════════════
# HybridRetriever — 多信号混合 + score_breakdown
# ═══════════════════════════════════════════════════════════════

class HybridRetriever(BaseRetriever):
    """多信号混合检索器。

    组合以下信号加权评分：
      - 主题匹配 (topic):       权重 15
      - 关键词匹配 (keywords):  权重 4
      - 决策匹配 (decisions):   权重 3
      - 待办匹配 (todos):       权重 3
      - 摘要匹配 (summary):     权重 2
      - 时间衰减 (recency):     权重 2 (7d) / 1 (30d)
      - 全文匹配 (content):     权重 1

    返回包含 score_breakdown 和 matched_fields 的详细结果。
    """

    # 信号权重配置
    WEIGHTS = {
        "topic": 15,
        "keywords": 4,
        "decisions": 3,
        "todos": 3,
        "summary": 2,
        "content": 1,
        "recency_7d": 2,
        "recency_30d": 1,
    }

    def __init__(self, score_fn=None):
        """
        Args:
            score_fn: 可选的外部评分函数，用于 content 字段匹配。
                      为 None 时使用内建简单匹配。
        """
        self._score_fn = score_fn

    def retrieve(
        self, query: str, records: Iterable[dict], top_k: int = 5
    ) -> list[dict]:
        query_lower = query.lower()
        scored = []

        for record in records:
            breakdown: dict[str, int] = {}
            matched: list[str] = []

            topic = str(record.get("topic", ""))
            topic_lower = topic.lower()
            summary = str(record.get("summary", ""))
            summary_lower = summary.lower()
            keywords = [str(k).lower() for k in record.get("keywords", [])]
            decisions = [str(d).lower() for d in record.get("decisions", [])]
            todos = [str(t).lower() for t in record.get("todos", [])]
            content = str(record.get("content", ""))
            content_lower = content.lower()

            # topic
            if topic_lower in query_lower:
                breakdown["topic"] = self.WEIGHTS["topic"]
                matched.append("topic")
            elif any(w in topic_lower for w in _tokenize(query_lower)):
                breakdown["topic"] = max(breakdown.get("topic", 0), 5)

            # keywords
            kw_hits = sum(1 for k in keywords if k in query_lower or query_lower in k)
            if kw_hits:
                breakdown["keywords"] = min(kw_hits * self.WEIGHTS["keywords"], 16)
                matched.append("keywords")

            # decisions
            dec_hits = sum(1 for d in decisions if any(w in d for w in _tokenize(query_lower)))
            if dec_hits:
                breakdown["decisions"] = min(dec_hits * self.WEIGHTS["decisions"], 9)
                matched.append("decisions")

            # todos
            todo_hits = sum(1 for t in todos if any(w in t for w in _tokenize(query_lower)))
            if todo_hits:
                breakdown["todos"] = min(todo_hits * self.WEIGHTS["todos"], 9)
                matched.append("todos")

            # summary
            if any(w in summary_lower for w in _tokenize(query_lower)):
                breakdown["summary"] = self.WEIGHTS["summary"]
                matched.append("summary")

            # content
            content_score = 0
            if self._score_fn:
                content_score = self._score_fn(query, record)
            if content_score > 0:
                breakdown["content"] = min(content_score, 5)
                matched.append("content")

            # recency
            recency = _calc_recency(record.get("updated_at", ""))
            if recency:
                breakdown["recency"] = recency
                if recency > 0:
                    matched.append("recency")

            total = sum(breakdown.values())
            if total <= 0:
                continue

            item = dict(record)
            item["score"] = total
            item["score_breakdown"] = dict(breakdown)
            item["matched_fields"] = matched
            scored.append(item)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


# ═══════════════════════════════════════════════════════════════
# EmbeddingRetriever — 向量检索占位（未来接入）
# ═══════════════════════════════════════════════════════════════

class EmbeddingRetriever(BaseRetriever):
    """向量检索器占位接口。

    未来可接入 sentence-transformers / OpenAI Embeddings 等。
    当前为 stub 实现，始终返回空结果。
    """

    def __init__(self, model_name: str = ""):
        self.model_name = model_name

    def retrieve(
        self, query: str, records: Iterable[dict], top_k: int = 5
    ) -> list[dict]:
        """当前未实现。返回空结果。"""
        return []


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _tokenize(text: str) -> list[str]:
    """简单分词（2~8 字中文 + 英文 token）。"""
    import re
    tokens: list[str] = []
    tokens.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{1,}", text))
    # 中文 2-6 字滑动
    chinese = re.findall(r"[一-鿿]+", text)
    for chunk in chinese:
        for wlen in (4, 3, 2):
            for i in range(len(chunk) - wlen + 1):
                tokens.append(chunk[i:i + wlen])
    return [t.lower() for t in tokens if len(t) >= 2]


def _calc_recency(updated_str: str) -> int:
    """计算时间衰减加分。"""
    if not updated_str:
        return 0
    try:
        dt = datetime.strptime(updated_str, "%Y-%m-%d %H:%M:%S")
        days = (datetime.now() - dt).days
        if days <= 7:
            return 2
        if days <= 30:
            return 1
    except (ValueError, TypeError):
        pass
    return 0


def _detect_matched_fields(query: str, record: dict) -> list[str]:
    """检测命中的字段（用于 KeywordRetriever）。"""
    q = query.lower()
    matched = []
    if q in str(record.get("topic", "")).lower():
        matched.append("topic")
    if any(q in str(k).lower() for k in record.get("keywords", [])):
        matched.append("keywords")
    if any(q in str(d).lower() for d in record.get("decisions", [])):
        matched.append("decisions")
    if any(q in str(t).lower() for t in record.get("todos", [])):
        matched.append("todos")
    if q in str(record.get("summary", "")).lower():
        matched.append("summary")
    return matched or ["content"]
