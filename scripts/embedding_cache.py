"""
embedding_cache.py — JSON-file-based embedding 缓存

避免对同一内容重复生成 embedding。基于内容 hash 做 key，
模型切换后自动失效旧向量。

缓存文件: memory/embedding_cache.json
格式: {
  "model": "fake-embedding-v1",
  "dimension": 128,
  "entries": {
    "abc123hash": {
      "content_hash": "abc123...",
      "embedding": [0.1, 0.2, ...],
      "embedding_model": "fake-embedding-v1",
      "dimension": 128,
      "created_at": "2026-06-25 12:00:00",
      "source_ids": ["id1", "id2"]
    }
  }
}
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence


def _cache_path(memory_dir: Path | None = None) -> Path:
    if memory_dir is None:
        memory_dir = Path(__file__).resolve().parents[3] / "Meory" / "memory"
    return memory_dir / "embedding_cache.json"


def content_hash(text: str) -> str:
    """计算文本内容的 SHA256 hash（前 16 位 hex）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_cache(memory_dir: Path | None = None) -> dict:
    """加载 embedding 缓存。"""
    path = _cache_path(memory_dir)
    if not path.exists():
        return {"model": "", "dimension": 0, "entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return {"model": "", "dimension": 0, "entries": {}}
        data.setdefault("model", "")
        data.setdefault("dimension", 0)
        data.setdefault("entries", {})
        return data
    except (json.JSONDecodeError, OSError):
        return {"model": "", "dimension": 0, "entries": {}}


def save_cache(cache: dict, memory_dir: Path | None = None) -> None:
    """原子写入 embedding 缓存。"""
    path = _cache_path(memory_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
        raise


def invalidate_cache_on_model_change(
    cache: dict, new_model: str, new_dimension: int
) -> bool:
    """模型或维度变化时清空所有旧 embedding。

    Returns:
        True 如果缓存被清空（模型/维度不匹配）。
    """
    old_model = cache.get("model", "")
    old_dim = cache.get("dimension", 0)
    if old_model != new_model or old_dim != new_dimension:
        cache["model"] = new_model
        cache["dimension"] = new_dimension
        cache["entries"] = {}
        return True
    return False


def get_cached_embedding(
    cache: dict,
    text: str,
    model_name: str,
) -> list[float] | None:
    """获取已缓存的 embedding（若存在且 model 匹配）。"""
    ch = content_hash(text)
    entry = cache.get("entries", {}).get(ch)
    if entry and entry.get("embedding_model") == model_name:
        return entry.get("embedding", None)
    return None


def set_cached_embedding(
    cache: dict,
    text: str,
    embedding: list[float],
    model_name: str,
    dimension: int,
    source_id: str = "",
) -> None:
    """存入 embedding 缓存。"""
    ch = content_hash(text)
    entry = {
        "content_hash": ch,
        "embedding": embedding,
        "embedding_model": model_name,
        "dimension": dimension,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source_ids": [],
    }
    # 更新已有条目
    existing = cache.get("entries", {}).get(ch, {})
    src_ids = set(existing.get("source_ids", []))
    if source_id:
        src_ids.add(source_id)
    entry["source_ids"] = sorted(src_ids)

    cache.setdefault("entries", {})[ch] = entry
    cache["model"] = model_name
    cache["dimension"] = dimension


def bulk_get_or_generate(
    cache: dict,
    texts: Sequence[str],
    model_name: str,
    dimension: int,
    generate_fn,
) -> tuple[list[list[float]], list[int]]:
    """批量获取或生成 embedding。

    对于已有缓存命中的不重新生成，仅对 miss 的批量生成。

    Returns:
        (embeddings, miss_indices): 所有 embedding 列表 + 需要生成的原始文本索引。
    """
    embeddings: list[list[float] | None] = [None] * len(texts)
    miss_indices: list[int] = []

    for i, text in enumerate(texts):
        cached = get_cached_embedding(cache, text, model_name)
        if cached is not None:
            embeddings[i] = cached
        else:
            miss_indices.append(i)

    if miss_indices:
        miss_texts = [texts[i] for i in miss_indices]
        generated = generate_fn(miss_texts)
        for gi, (idx, emb) in enumerate(zip(miss_indices, generated)):
            embeddings[idx] = emb
            set_cached_embedding(cache, texts[idx], emb, model_name, dimension)

    return embeddings, miss_indices
