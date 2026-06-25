"""
retrieval.py — 可插拔检索器架构 (v0.6.0)

提供:
  - BaseRetriever: 检索器抽象基类
  - KeywordRetriever: 关键词加权匹配
  - SemanticRetriever: Embedding 语义检索
  - EmbeddingRetriever: 向后兼容别名 → SemanticRetriever
  - HybridRetriever: 混合检索 (keyword + semantic + hybrid 三模式)

不依赖任何向量库或外部 API (embedding 通过可插拔 provider 注入)。
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, Sequence

try:
    from embedding_provider import EmbeddingProvider, FakeEmbeddingProvider
    _EMBEDDING_AVAILABLE = True
except ImportError:
    _EMBEDDING_AVAILABLE = False

try:
    from embedding_cache import (
        content_hash,
        load_cache,
        save_cache,
        invalidate_cache_on_model_change,
        get_cached_embedding,
        set_cached_embedding,
        bulk_get_or_generate,
    )
    _CACHE_AVAILABLE = True
except ImportError:
    _CACHE_AVAILABLE = False


class BaseRetriever(ABC):
    """检索器抽象基类。"""

    @abstractmethod
    def retrieve(
        self, query: str, records: Iterable[dict], top_k: int = 5
    ) -> list[dict]:
        """返回按相关性排序的结果列表。"""
        ...


# ═══════════════════════════════════════════════════════════════
# KeywordRetriever — 关键词加权匹配
# ═══════════════════════════════════════════════════════════════

class KeywordRetriever(BaseRetriever):
    """基于关键词加权匹配的检索器。"""

    def __init__(self, score_fn):
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
# SemanticRetriever — Embedding 语义检索
# ═══════════════════════════════════════════════════════════════

class SemanticRetriever(BaseRetriever):
    """基于 embedding 向量相似度的语义检索器。

    对 query 和所有记忆内容生成或读取 embedding，使用 cosine similarity
    排序。自动缓存 embedding，模型切换后缓存失效。
    """

    def __init__(
        self,
        provider: EmbeddingProvider | None = None,
        memory_dir=None,
    ):
        if provider is None:
            if _EMBEDDING_AVAILABLE:
                provider = FakeEmbeddingProvider(dimension=128)
            else:
                raise ValueError("至少需要 embedding_provider 模块")
        self._provider = provider

    @property
    def provider(self):
        return self._provider

    def retrieve(
        self, query: str, records: Iterable[dict], top_k: int = 5
    ) -> list[dict]:
        records = list(records)
        if not records:
            return []

        # 收集所有文本（query + 每条记忆的摘要/关键词拼接）
        texts: list[str] = [query]
        for r in records:
            texts.append(_build_record_text(r))

        # 生成 embeddings（优先批量，支持缓存）
        all_embeddings = self._provider.embed_batch(texts)

        query_vec = all_embeddings[0]
        record_vecs = all_embeddings[1:]

        # cosine similarity 打分
        scored = []
        for i, (rec, rvec) in enumerate(zip(records, record_vecs)):
            sim = _cosine_similarity(query_vec, rvec)
            if sim <= 0:
                continue
            item = dict(rec)
            item["score"] = round(sim * 100, 2)  # scale 0-1 → 0-100
            item["score_breakdown"] = {"semantic": item["score"]}
            item["matched_fields"] = ["semantic"]
            item["retrieval_reason"] = f"语义相似度 {sim:.4f}"
            scored.append(item)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


# 向后兼容别名
EmbeddingRetriever = SemanticRetriever


# ═══════════════════════════════════════════════════════════════
# HybridRetriever — 多信号混合 + 模式选择
# ═══════════════════════════════════════════════════════════════

class HybridRetriever(BaseRetriever):
    """混合检索器 — 支持 keyword / semantic / hybrid 三种模式。

    组合以下信号:
      - 关键词匹配 (topic/keywords/decisions/todos/summary/content + recency)
      - 语义相似度 (embedding cosine similarity)
      - hybrid: 关键词分 + 语义分加权合并

    当 semantic provider 不可用时，自动降级为 keyword-only。
    """

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

    HYBRID_KEYWORD_WEIGHT = 0.4
    HYBRID_SEMANTIC_WEIGHT = 0.6

    def __init__(
        self,
        score_fn=None,
        semantic_provider: EmbeddingProvider | None = None,
        mode: str = "hybrid",
        memory_dir=None,
    ):
        """Args:
            score_fn: 关键词评分函数 (query, record) -> int。
            semantic_provider: EmbeddingProvider，为 None 时自动降级。
            mode: "keyword" / "semantic" / "hybrid"。
        """
        self._score_fn = score_fn
        self._semantic_provider = semantic_provider
        self._mode = mode
        self._memory_dir = memory_dir
        self._semantic_available = (
            semantic_provider is not None and _EMBEDDING_AVAILABLE
        )

    @property
    def mode(self) -> str:
        return self._mode

    def retrieve(
        self, query: str, records: Iterable[dict], top_k: int = 5
    ) -> list[dict]:
        records = list(records)
        if not records:
            return []

        effective_mode = self._mode
        if effective_mode in ("semantic", "hybrid") and not self._semantic_available:
            import logging
            logging.getLogger("claude_memory").warning(
                "Embedding provider 不可用，降级为 keyword 检索"
            )
            effective_mode = "keyword"

        if effective_mode == "keyword":
            return self._keyword_retrieve(query, records, top_k)
        elif effective_mode == "semantic":
            return self._semantic_retrieve(query, records, top_k)
        elif effective_mode == "hybrid":
            return self._hybrid_retrieve(query, records, top_k)
        else:
            raise ValueError(f"未知检索模式: {effective_mode}")

    def _keyword_retrieve(
        self, query: str, records: list[dict], top_k: int
    ) -> list[dict]:
        """纯关键词检索。"""
        keyword = KeywordRetriever(self._score_fn)
        results = keyword.retrieve(query, records, top_k)
        for r in results:
            r["retrieval_mode"] = "keyword"
        return results

    def _semantic_retrieve(
        self, query: str, records: list[dict], top_k: int
    ) -> list[dict]:
        """纯语义检索。"""
        semantic = SemanticRetriever(
            provider=self._semantic_provider, memory_dir=self._memory_dir
        )
        results = semantic.retrieve(query, records, top_k)
        for r in results:
            r["retrieval_mode"] = "semantic"
        return results

    def _hybrid_retrieve(
        self, query: str, records: list[dict], top_k: int
    ) -> list[dict]:
        """关键词 + 语义混合检索。"""
        # 1. 关键词检索（取 top_k * 3 召回）
        kw = KeywordRetriever(self._score_fn)
        kw_results = kw.retrieve(query, records, top_k * 3)
        kw_map = {r.get("id", ""): r for r in kw_results}

        # 2. 语义检索
        semantic = SemanticRetriever(
            provider=self._semantic_provider, memory_dir=self._memory_dir
        )
        sem_results = semantic.retrieve(query, records, top_k * 3)
        sem_map = {r.get("id", ""): r for r in sem_results}

        # 3. 合并分数
        all_ids = set(kw_map.keys()) | set(sem_map.keys())
        merged = []
        for rid in all_ids:
            kw_score = kw_map[rid].get("score", 0) if rid in kw_map else 0
            sem_score = sem_map[rid].get("score", 0) if rid in sem_map else 0
            # 归一化: keyword max ~50, semantic 0-100
            kw_normalized = min(kw_score / 50.0, 1.0) * 100
            combined = (
                self.HYBRID_KEYWORD_WEIGHT * kw_normalized
                + self.HYBRID_SEMANTIC_WEIGHT * sem_score
            )
            if combined <= 0:
                continue

            source = kw_map.get(rid, sem_map.get(rid, {}))
            item = dict(source)
            item["score"] = round(combined, 2)
            item["score_breakdown"] = {
                "keyword": round(kw_normalized, 2),
                "semantic": round(sem_score, 2),
                "hybrid": round(combined, 2),
            }
            item["matched_fields"] = list(
                set(kw_map.get(rid, {}).get("matched_fields", []) + ["semantic"])
            )
            item["retrieval_mode"] = "hybrid"
            item["retrieval_reason"] = (
                f"混合: keyword={kw_normalized:.1f}, semantic={sem_score:.1f}"
            )
            merged.append(item)

        merged.sort(key=lambda x: x["score"], reverse=True)
        return merged[:top_k]


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """计算两个向量的 cosine similarity。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _build_record_text(record: dict) -> str:
    """构造 record 的文本表示用于 embedding 生成。"""
    parts = [
        str(record.get("topic", "")),
        str(record.get("summary", "")),
        " ".join(record.get("keywords", [])),
        " ".join(record.get("decisions", [])),
        " ".join(record.get("todos", [])),
    ]
    return " ".join(p for p in parts if p)


def _tokenize(text: str) -> list[str]:
    """简单分词（2~8 字中文 + 英文 token）。"""
    import re
    tokens: list[str] = []
    tokens.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{1,}", text))
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
    """检测命中的字段。"""
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
