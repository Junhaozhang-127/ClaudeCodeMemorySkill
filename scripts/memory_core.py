"""
memory_core.py

Claude Code Memory Skill 的核心逻辑：
- 保存 Markdown 记忆
- 更新 index.json
- 检索相关记忆
- 重建索引

当前 MVP 版本仅使用 Python 标准库。
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = PROJECT_ROOT / "memory"
TOPICS_DIR = MEMORY_DIR / "topics"
INDEX_FILE = MEMORY_DIR / "index.json"


@dataclass
class MemoryRecord:
    """单条记忆索引记录。"""

    topic: str
    file: str
    keywords: list[str]
    summary: str
    created_at: str
    updated_at: str


def is_memory_markdown(path: Path) -> bool:
    """检查是否为真实记忆 Markdown 文件。

    排除 README.md、.gitkeep 以及其他以 . 开头的隐藏文件。
    """
    if not path.suffix == ".md":
        return False
    name = path.name
    if name.lower() == "readme.md":
        return False
    if name == ".gitkeep":
        return False
    if name.startswith("."):
        return False
    return True


def ensure_memory_dirs() -> None:
    """确保记忆目录存在。"""
    TOPICS_DIR.mkdir(parents=True, exist_ok=True)
    if not INDEX_FILE.exists():
        INDEX_FILE.write_text("{}", encoding="utf-8")


def slugify_topic(topic: str) -> str:
    """将主题转换为安全文件名。"""
    topic = topic.strip() or "untitled"
    topic = re.sub(r"[\\/:*?\"<>|]+", "_", topic)
    topic = re.sub(r"\s+", "_", topic)
    return topic[:80]


def extract_keywords(text: str, topic: str, max_keywords: int = 10) -> list[str]:
    """
    简单关键词抽取。

    MVP 版本使用规则法：
    - 保留主题词
    - 抽取英文/数字组合词
    - 抽取长度较短的中文片段
    后续可替换为 LLM 或 embedding。
    """
    candidates: list[str] = []

    for part in re.split(r"[_\s,，。；;:：/\\\-]+", topic):
        part = part.strip()
        if part:
            candidates.append(part)

    # English-like technical tokens.
    candidates.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text))

    # Common Chinese technical terms, coarse but useful for MVP.
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{2,8}", text)
    candidates.extend(chinese_terms)

    seen = set()
    result = []
    for item in candidates:
        item = item.strip()
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= max_keywords:
            break
    return result


def simple_summary(text: str, max_chars: int = 300) -> str:
    """
    生成极简摘要。

    MVP 默认截取文本前若干字符。
    后续可改成调用 Claude Code/LLM 生成摘要。
    """
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def load_index() -> dict:
    """读取 index.json。"""
    ensure_memory_dirs()
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_index(index: dict) -> None:
    """原子写入 index.json。

    先写入临时文件，成功后再替换原文件，避免写入中断导致索引损坏。
    """
    ensure_memory_dirs()
    tmp_path = INDEX_FILE.with_name("index.json.tmp")
    json_text = json.dumps(index, ensure_ascii=False, indent=2)
    try:
        tmp_path.write_text(json_text, encoding="utf-8")
        os.replace(tmp_path, INDEX_FILE)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def save_memory(topic: str, conversation_text: str, append: bool = True) -> Path:
    """
    保存一条会话记忆到 Markdown，并更新索引。

    Args:
        topic: 对话主题。
        conversation_text: 本轮对话内容。
        append: 如果同名主题文件存在，是否追加写入。

    Returns:
        写入的 Markdown 文件路径。
    """
    ensure_memory_dirs()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_topic = slugify_topic(topic)
    filename = f"{safe_topic}_{date_str}.md"
    filepath = TOPICS_DIR / filename

    summary = simple_summary(conversation_text)
    keywords = extract_keywords(conversation_text, topic)

    block = f"""# {topic}

> 更新时间：{now}

## 摘要

{summary}

## 关键词

{", ".join(keywords) if keywords else "暂无"}

## 关键决策

- 暂未抽取。后续可接入 LLM 自动生成。

## 待办事项

- 暂未抽取。后续可接入 LLM 自动生成。

## 原始对话摘录

```text
{conversation_text.strip()}
```

---

"""

    if filepath.exists() and append:
        with filepath.open("a", encoding="utf-8") as f:
            f.write("\n\n" + block)
    else:
        filepath.write_text(block, encoding="utf-8")

    index = load_index()
    record = MemoryRecord(
        topic=topic,
        file=str(filepath.relative_to(PROJECT_ROOT)),
        keywords=keywords,
        summary=summary,
        created_at=index.get(safe_topic, {}).get("created_at", now),
        updated_at=now,
    )
    index[safe_topic] = asdict(record)
    save_index(index)

    return filepath


def score_record(query: str, record: dict) -> int:
    """基于主题、关键词、摘要进行简单相关性评分。"""
    query_lower = query.lower()
    score = 0

    topic = str(record.get("topic", ""))
    summary = str(record.get("summary", ""))
    keywords = record.get("keywords", [])

    if topic and topic.lower() in query_lower:
        score += 10

    for token in re.split(r"\s+|,|，|。|；|;|:|：", query):
        token = token.strip()
        if not token:
            continue
        if token in topic:
            score += 4
        if token in summary:
            score += 2
        if token.lower() in topic.lower():
            score += 2
        if token.lower() in summary.lower():
            score += 1

    for kw in keywords:
        kw = str(kw).strip()
        if kw and kw.lower() in query_lower:
            score += 5

    return score


def retrieve_memory(query: str, top_k: int = 5) -> list[dict]:
    """
    根据用户输入检索相关记忆。

    Returns:
        包含 topic、score、file、content 的结果列表。
    """
    index = load_index()
    scored = []

    for key, record in index.items():
        score = score_record(query, record)
        if score <= 0:
            continue

        filepath = PROJECT_ROOT / record.get("file", "")
        content = ""
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")

        scored.append(
            {
                "id": key,
                "topic": record.get("topic", key),
                "score": score,
                "file": record.get("file", ""),
                "summary": record.get("summary", ""),
                "keywords": record.get("keywords", []),
                "content": content,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def format_context(results: Iterable[dict], max_chars_per_item: int = 1200) -> str:
    """把检索结果格式化为可注入 Claude Code 的上下文。"""
    blocks = []
    for i, item in enumerate(results, start=1):
        content = item.get("content", "")[:max_chars_per_item]
        blocks.append(
            f"""## 相关记忆 {i}: {item.get("topic")}

文件：{item.get("file")}
相关分：{item.get("score")}

{content}
"""
        )

    if not blocks:
        return "未检索到相关历史记忆。"

    return "# Claude Code Memory Context\n\n" + "\n\n".join(blocks)


def rebuild_index() -> dict:
    """扫描 memory/topics 下的 Markdown 文件，重建基础索引。"""
    ensure_memory_dirs()
    index = {}

    for path in TOPICS_DIR.glob("*.md"):
        if not is_memory_markdown(path):
            continue
        content = path.read_text(encoding="utf-8")
        first_heading = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
        topic = first_heading.group(1).strip() if first_heading else path.stem
        summary_match = re.search(r"## 摘要\s+(.+?)(?:\n## |\Z)", content, flags=re.S)
        summary = summary_match.group(1).strip() if summary_match else simple_summary(content)
        keywords = extract_keywords(content, topic)
        stat = path.stat()
        created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        updated = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        key = slugify_topic(path.stem)
        index[key] = asdict(
            MemoryRecord(
                topic=topic,
                file=str(path.relative_to(PROJECT_ROOT)),
                keywords=keywords,
                summary=simple_summary(summary),
                created_at=created,
                updated_at=updated,
            )
        )

    save_index(index)
    return index
