"""
embedding_provider.py — 可配置的 Embedding Provider 抽象层

提供:
  - EmbeddingProvider: 抽象基类
  - FakeEmbeddingProvider: 确定性向量生成器（测试用）
  - OpenAIEmbeddingProvider: OpenAI-compatible API provider
  - get_embedding_provider: 工厂函数

安全约束: API key 只从环境变量读取，不写入配置文件。
"""

from __future__ import annotations

import hashlib
import os
from abc import ABC, abstractmethod
from typing import Sequence


class EmbeddingProvider(ABC):
    """Embedding Provider 抽象基类。

    所有 embedding 实现必须继承此类。
    """

    @abstractmethod
    def embed_text(self, text: str) -> list[float]:
        """对单条文本生成 embedding 向量。"""
        ...

    @abstractmethod
    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """对多条文本批量生成 embedding 向量。"""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """返回 embedding 向量维度。"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """返回模型名。"""
        ...


# ═══════════════════════════════════════════════════════════════
# FakeEmbeddingProvider — 确定性假向量（测试用）
# ═══════════════════════════════════════════════════════════════

class FakeEmbeddingProvider(EmbeddingProvider):
    """基于 n-gram 重叠生成确定性假向量。

    同一文本始终生成同一向量，语义相似的文本生成高相似度向量。
    使用 character n-gram（3~6 字符）映射到向量空间，
    确保测试场景下向量相似度近似真实语义检索行为。
    """

    def __init__(self, dimension: int = 128):
        self._dimension = dimension
        self._model = "fake-embedding-v1"

    @property
    def dimension(self) -> int:
        return self._dimension

    @property
    def model_name(self) -> str:
        return self._model

    def embed_text(self, text: str) -> list[float]:
        return self._ngram_to_vector(text)

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._ngram_to_vector(t) for t in texts]

    def _ngram_to_vector(self, text: str) -> list[float]:
        """基于 character n-gram 的向量生成。

        对 3~6 字符的 n-gram 做 hash 映射，使相似文本的向量
        余弦相似度 > 0，而非纯 hash 的接近 0。
        """
        if not text:
            text = " "
        text_lower = text.lower()

        vec = [0.0] * self._dimension
        # 生成 3~6 字符的 sliding window n-grams
        for n in (3, 4, 5, 6):
            for i in range(len(text_lower) - n + 1):
                ngram = text_lower[i:i + n]
                # hash ngram 到维度索引
                idx = int(hashlib.md5(ngram.encode("utf-8")).hexdigest()[:8], 16) % self._dimension
                vec[idx] += 1.0

        # 同时基于整体 hash 添加少量信号，确保完全不同的文本不会零向量
        base = int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)
        vec[base % self._dimension] += 0.5

        # L2 归一化
        norm = sum(v * v for v in vec) ** 0.5
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec


# ═══════════════════════════════════════════════════════════════
# OpenAIEmbeddingProvider — OpenAI-compatible API
# ═══════════════════════════════════════════════════════════════

class OpenAIEmbeddingProvider(EmbeddingProvider):
    """OpenAI-compatible Embedding API provider。

    支持 OpenAI / DeepSeek / 任何兼容 /v1/embeddings 端点。

    Config (all from env vars, no config file storage of secrets):
      EMBEDDING_API_KEY — required
      EMBEDDING_API_BASE — defaults to https://api.openai.com/v1
      EMBEDDING_MODEL — defaults to text-embedding-3-small
    """

    def __init__(
        self,
        api_key: str = "",
        api_base: str = "",
        model: str = "",
        timeout: float = 30.0,
    ):
        self._api_key = api_key or os.environ.get("EMBEDDING_API_KEY", "")
        self._api_base = api_base or os.environ.get(
            "EMBEDDING_API_BASE", "https://api.openai.com/v1"
        )
        self._model = model or os.environ.get(
            "EMBEDDING_MODEL", "text-embedding-3-small"
        )
        self._timeout = timeout

    @property
    def dimension(self) -> int:
        return 1536  # text-embedding-3-small default

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def is_configured(self) -> bool:
        """检查是否已配置 API key。"""
        return bool(self._api_key)

    def embed_text(self, text: str) -> list[float]:
        results = self.embed_batch([text])
        return results[0] if results else []

    def embed_batch(self, texts: Sequence[str]) -> list[list[float]]:
        if not self._api_key:
            raise ValueError(
                "EMBEDDING_API_KEY 未设置。请设置环境变量 EMBEDDING_API_KEY 或"
                " 使用 FakeEmbeddingProvider 进行测试。"
            )

        import json
        import urllib.request
        import urllib.error

        url = self._api_base.rstrip("/") + "/embeddings"
        payload = json.dumps({
            "model": self._model,
            "input": list(texts),
            "encoding_format": "float",
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )

        try:
            resp = urllib.request.urlopen(req, timeout=self._timeout)
            body = json.loads(resp.read().decode("utf-8"))
            # data[*].embedding 按输入顺序返回
            data = sorted(body.get("data", []), key=lambda d: d.get("index", 0))
            return [d["embedding"] for d in data]
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"Embedding API 请求失败 ({e.code}): {e.reason}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Embedding API 请求失败: {e}") from e


# ═══════════════════════════════════════════════════════════════
# 工厂函数
# ═══════════════════════════════════════════════════════════════

def get_embedding_provider(
    provider: str = "auto",
    fake_dimension: int = 128,
) -> EmbeddingProvider:
    """获取 EmbeddingProvider 实例。

    Args:
        provider: "auto" / "openai" / "fake" / "null"
            - auto: 优先使用 OpenAI（若 EMBEDDING_API_KEY 已设），否则回退到 Fake
            - openai: 强制 OpenAI，无 key 时抛异常
            - fake/null: 使用 FakeEmbeddingProvider
        fake_dimension: Fake provider 的向量维度（仅用于测试）。

    Returns:
        EmbeddingProvider 实例。

    Raises:
        ValueError: provider="openai" 且 EMBEDDING_API_KEY 未设置时。
    """
    if provider in ("fake", "null"):
        return FakeEmbeddingProvider(dimension=fake_dimension)

    if provider == "openai":
        p = OpenAIEmbeddingProvider()
        if not p.is_configured:
            raise ValueError(
                "EMBEDDING_API_KEY 环境变量未设置。"
                " 请设置后重试，或使用 provider='fake'。"
            )
        return p

    # auto: 优先 OpenAI
    openai_p = OpenAIEmbeddingProvider()
    if openai_p.is_configured:
        return openai_p
    return FakeEmbeddingProvider(dimension=fake_dimension)
