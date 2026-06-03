"""
memory_core.py

Claude Code Memory Skill 的核心逻辑：
- 保存 Markdown 记忆（支持可插拔摘要器）
- 更新 index.json（含 decisions / todos 元数据）
- 检索相关记忆（优化评分算法）
- 重建索引（兼容新旧 Markdown 格式）

当前版本仅使用 Python 标准库 + 可选 jieba。
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

# ── 可选依赖 ─────────────────────────────────────────────────
try:
    import jieba  # noqa: F401

    _JIEBA_AVAILABLE = True
except ImportError:
    _JIEBA_AVAILABLE = False


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = PROJECT_ROOT / "memory"
TOPICS_DIR = MEMORY_DIR / "topics"
INDEX_FILE = MEMORY_DIR / "index.json"


# ═══════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════

@dataclass
class MemoryRecord:
    """单条记忆索引记录。"""

    topic: str
    file: str
    keywords: list[str]
    summary: str
    created_at: str
    updated_at: str
    decisions: list[str] = field(default_factory=list)
    todos: list[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# 停用词表
# ═══════════════════════════════════════════════════════════════

_CN_STOP_WORDS: set[str] = {
    "的", "了", "和", "是", "在", "我", "你", "他", "她", "它",
    "我们", "你们", "他们", "一个", "这个", "那个", "进行", "当前",
    "通过", "可以", "需要", "什么", "怎么", "为什么", "如何",
    "已经", "还", "就", "都", "也", "把", "被", "让", "从",
    "到", "对", "上", "下", "中", "与", "或", "但", "而",
    "因为", "所以", "如果", "然后", "之后", "之前", "之后",
    "一些", "所有", "很多", "非常", "比较", "可能", "应该",
    "不是", "没有", "还是", "只是", "就是", "还有", "这个",
    "这样", "那样", "这些", "那些", "这里", "那里", "自己",
    "知道", "觉得", "认为", "希望", "想", "要", "会", "能",
}
_EN_STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "shall",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above",
    "below", "between", "under", "and", "but", "or", "nor", "not",
    "this", "that", "these", "those", "it", "its", "he", "she",
    "they", "them", "we", "us", "i", "you", "me", "my", "your",
}
_STOP_WORDS = _CN_STOP_WORDS | _EN_STOP_WORDS


# ═══════════════════════════════════════════════════════════════
# 文件过滤
# ═══════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════
# 目录与索引 I/O
# ═══════════════════════════════════════════════════════════════

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


def load_index() -> dict:
    """读取 index.json。"""
    ensure_memory_dirs()
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_index(index: dict) -> None:
    """原子写入 index.json。"""
    ensure_memory_dirs()
    tmp_path = INDEX_FILE.with_name("index.json.tmp")
    json_text = json.dumps(index, ensure_ascii=False, indent=2)
    try:
        tmp_path.write_text(json_text, encoding="utf-8")
        os.replace(tmp_path, INDEX_FILE)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
        raise


# ═══════════════════════════════════════════════════════════════
# 关键词抽取（jieba 优先，规则法回退）
# ═══════════════════════════════════════════════════════════════

def _extract_keywords_jieba(text: str, topic: str, max_keywords: int = 10) -> list[str]:
    """使用 jieba 分词提取关键词。"""
    import jieba as _jieba

    candidates: list[str] = []

    # 主题切分
    for part in re.split(r"[_\s,，。；;:：/\\\-]+", topic):
        part = part.strip()
        if part:
            candidates.append(part)

    # 英文技术 token
    candidates.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text))

    # jieba 分词 → 过滤停用词和短词
    seg_list = _jieba.cut(text)
    for word in seg_list:
        word = word.strip()
        if not word:
            continue
        if len(word) < 2:
            continue
        if word.lower() in _STOP_WORDS:
            continue
        # 纯数字/标点跳过
        if re.fullmatch(r"[\d\.\,\;\:\!\?\-]+", word):
            continue
        candidates.append(word)

    # 去重保序
    seen: set[str] = set()
    result: list[str] = []
    for item in candidates:
        item = item.strip()
        if not item or item in seen:
            continue
        if item.lower() in _STOP_WORDS:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= max_keywords:
            break

    return result


def _extract_keywords_regex(text: str, topic: str, max_keywords: int = 10) -> list[str]:
    """规则法提取关键词（jieba 不可用时的回退方案）。"""
    candidates: list[str] = []

    # 主题切分
    for part in re.split(r"[_\s,，。；;:：/\\\-]+", topic):
        part = part.strip()
        if part:
            candidates.append(part)

    # 英文技术 token
    candidates.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text))

    # 中文片段提取（2~8 字）
    chinese_terms = re.findall(r"[一-鿿]{2,8}", text)
    # 过滤停用词和过短词
    for term in chinese_terms:
        if len(term) >= 2 and term not in _STOP_WORDS:
            candidates.append(term)

    # 去重 + 停用词过滤
    seen: set[str] = set()
    result: list[str] = []
    for item in candidates:
        item = item.strip()
        if not item or item in seen:
            continue
        if item.lower() in _STOP_WORDS:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= max_keywords:
            break

    return result


def extract_keywords(text: str, topic: str = "", max_keywords: int = 10) -> list[str]:
    """抽取关键词。

    jieba 可用时优先使用 jieba 分词；不可用时回退到正则规则法。
    签名和默认行为保持向后兼容。
    """
    if _JIEBA_AVAILABLE:
        try:
            return _extract_keywords_jieba(text, topic, max_keywords)
        except Exception:
            pass
    return _extract_keywords_regex(text, topic, max_keywords)


# ═══════════════════════════════════════════════════════════════
# 摘要生成
# ═══════════════════════════════════════════════════════════════

def simple_summary(text: str, max_chars: int = 300) -> str:
    """生成极简摘要（截断法，兼容旧调用）。"""
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def _get_default_summarizer():
    """懒加载默认摘要器（避免循环导入）。"""
    from summarizers import RuleBasedSummarizer

    return RuleBasedSummarizer(keyword_extractor=extract_keywords)


# ═══════════════════════════════════════════════════════════════
# 记忆保存
# ═══════════════════════════════════════════════════════════════

def save_memory(
    topic: str,
    conversation_text: str,
    append: bool = True,
    summarizer=None,
) -> Path:
    """保存一条会话记忆到 Markdown，并更新索引。

    Args:
        topic: 对话主题。
        conversation_text: 本轮对话内容。
        append: 如果同名主题文件存在，是否追加写入。
        summarizer: 可选摘要器（需实现 BaseSummarizer 接口）。
                   为 None 时使用 RuleBasedSummarizer。

    Returns:
        写入的 Markdown 文件路径。
    """
    ensure_memory_dirs()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_topic = slugify_topic(topic)
    filename = f"{safe_topic}_{date_str}.md"
    filepath = TOPICS_DIR / filename

    # ── 使用摘要器生成结构化结果 ──
    if summarizer is None:
        summarizer = _get_default_summarizer()
    result = summarizer.summarize(conversation_text, topic)

    summary = result.summary or simple_summary(conversation_text)
    keywords = result.keywords if result.keywords else extract_keywords(conversation_text, topic)

    # ── 构建决策/待办段落 ──
    decisions_lines = _format_list_section(result.decisions, "无明确关键决策。")
    todos_lines = _format_list_section(result.todos, "无明确待办事项。")

    keywords_str = ", ".join(keywords) if keywords else "暂无"

    block = f"""# {topic}

> 更新时间：{now}

## 摘要

{summary}

## 关键词

{keywords_str}

## 关键决策

{decisions_lines}

## 待办事项

{todos_lines}

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

    # ── 更新索引 ──
    index = load_index()
    record = MemoryRecord(
        topic=topic,
        file=str(filepath.relative_to(PROJECT_ROOT)),
        keywords=keywords,
        summary=summary,
        decisions=result.decisions,
        todos=result.todos,
        created_at=index.get(safe_topic, {}).get("created_at", now),
        updated_at=now,
    )
    index[safe_topic] = asdict(record)
    save_index(index)

    return filepath


def _format_list_section(items: list[str], fallback: str) -> str:
    """格式化列表段落：有内容时每条一行 '- 内容'，否则输出 fallback。"""
    if not items:
        return fallback
    return "\n".join(f"- {item}" for item in items)


# ═══════════════════════════════════════════════════════════════
# 检索评分
# ═══════════════════════════════════════════════════════════════

def _tokenize_query(query: str) -> list[str]:
    """将查询文本切分为有意义的 token 列表（过滤停用词和短词）。"""
    tokens: list[str] = []

    # 英文 token
    tokens.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{1,}", query))

    # 中文 token（2~6 字滑动窗口）
    chinese_chars = re.findall(r"[一-鿿]+", query)
    for chunk in chinese_chars:
        # 2~4 字滑动（避免过长组合）
        for wlen in (4, 3, 2):
            for i in range(len(chunk) - wlen + 1):
                tokens.append(chunk[i : i + wlen])

    # 过滤停用词和短词
    filtered: list[str] = []
    for t in tokens:
        t = t.strip()
        if len(t) < 2:
            continue
        if t.lower() in _STOP_WORDS:
            continue
        filtered.append(t)

    return filtered


def score_record(query: str, record: dict) -> int:
    """基于主题、关键词、摘要、决策、待办进行加权相关性评分。

    返回整数分数，越高越相关。0 表示不相关。
    """
    query_lower = query.lower()
    score = 0

    topic = str(record.get("topic", ""))
    topic_lower = topic.lower()
    summary = str(record.get("summary", ""))
    summary_lower = summary.lower()
    keywords = [str(k).lower() for k in record.get("keywords", [])]
    decisions = [str(d).lower() for d in record.get("decisions", [])]
    todos = [str(t).lower() for t in record.get("todos", [])]

    # ── 1. 主题完全命中（最高权重）──
    if topic_lower and topic_lower in query_lower:
        score += 15

    # ── 2. 按 token 逐项匹配 ──
    tokens = _tokenize_query(query)
    # 同时保留原始 query 的空白切分作为补充
    raw_tokens = re.split(r"\s+|,|，|。|；|;|:|：", query)
    all_tokens = list(set(t.lower() for t in tokens + raw_tokens if len(t.strip()) >= 2))

    for token in all_tokens:
        token = token.strip().lower()
        if not token or token in _STOP_WORDS:
            continue

        if token in topic_lower:
            score += 5
        if token in keywords:
            score += 4
        if token in summary_lower:
            score += 2
        # decisions / todos 命中加分
        for dec in decisions:
            if token in dec:
                score += 3
                break
        for td in todos:
            if token in td:
                score += 3
                break

    # ── 3. 时间衰减加分（仅在已有内容命中时生效）──
    if score > 0:
        try:
            updated_str = str(record.get("updated_at", ""))
            if updated_str:
                updated_dt = datetime.strptime(updated_str, "%Y-%m-%d %H:%M:%S")
                days_ago = (datetime.now() - updated_dt).days
                if days_ago <= 7:
                    score += 2
        except (ValueError, TypeError):
            pass

    return score


# ═══════════════════════════════════════════════════════════════
# 记忆检索
# ═══════════════════════════════════════════════════════════════

def _safe_get_list(record: dict, key: str) -> list[str]:
    """安全地从 record 中获取列表字段，兼容旧索引无此字段的情况。"""
    val = record.get(key, [])
    if isinstance(val, list):
        return val
    return []


def retrieve_memory(query: str, top_k: int = 5) -> list[dict]:
    """根据用户输入检索相关记忆。

    Returns:
        包含 id、topic、score、file、content、summary、keywords、
        decisions、todos 的结果列表。
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
                "decisions": _safe_get_list(record, "decisions"),
                "todos": _safe_get_list(record, "todos"),
                "content": content,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ═══════════════════════════════════════════════════════════════
# 上下文格式化
# ═══════════════════════════════════════════════════════════════

def format_context(results: Iterable[dict], max_chars_per_item: int = 1200) -> str:
    """把检索结果格式化为可注入 Claude Code 的上下文。

    优先展示：摘要 → 关键决策 → 待办事项 → 内容片段。
    保持每条记忆在 max_chars_per_item 字符以内。
    """
    blocks = []
    for i, item in enumerate(results, start=1):
        topic = item.get("topic", "未知主题")
        file_path = item.get("file", "")
        score = item.get("score", 0)
        summary = item.get("summary", "")
        decisions = _safe_get_list(item, "decisions")
        todos = _safe_get_list(item, "todos")

        # 组装优先级内容
        parts: list[str] = []
        remaining = max_chars_per_item

        # 摘要
        if summary:
            parts.append(f"**摘要**：{summary}")
            remaining -= len(summary) + 10

        # 关键决策
        if decisions and remaining > 40:
            dec_text = "；".join(decisions[:3])
            if len(dec_text) > remaining - 20:
                dec_text = dec_text[: remaining - 20] + "…"
            parts.append(f"**关键决策**：{dec_text}")
            remaining -= len(dec_text) + 15

        # 待办事项
        if todos and remaining > 40:
            todo_text = "；".join(todos[:3])
            if len(todo_text) > remaining - 20:
                todo_text = todo_text[: remaining - 20] + "…"
            parts.append(f"**待办事项**：{todo_text}")
            remaining -= len(todo_text) + 15

        # 内容补充（低优先级，截断）
        if remaining > 60:
            content = item.get("content", "")
            content = re.sub(r"\s*\n\s*\n\s*", " ", content)
            content = re.sub(r"\s+", " ", content)
            if len(content) > remaining - 5:
                content = content[: remaining - 5] + "…"
            parts.append(f"**内容**：{content}")

        body = "\n".join(parts)
        blocks.append(
            f"""## 相关记忆 {i}: {topic}

文件：{file_path}
相关分：{score}

{body}
"""
        )

    if not blocks:
        return "未检索到相关历史记忆。"

    return "# Claude Code Memory Context\n\n" + "\n\n".join(blocks)


# ═══════════════════════════════════════════════════════════════
# 索引重建（兼容新旧 Markdown 格式）
# ═══════════════════════════════════════════════════════════════

def _parse_markdown_section(content: str, heading: str) -> str:
    """解析 Markdown 中某个 ## heading 下的文本内容。"""
    # 匹配 ## heading 直到下一个 ## 或文件末尾
    pattern = rf"## {re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, flags=re.S)
    if not match:
        return ""
    return match.group(1).strip()


def _parse_markdown_list(content: str, heading: str) -> list[str]:
    """解析 Markdown 中某个 ## heading 下的列表项（- item）。"""
    text = _parse_markdown_section(content, heading)
    if not text:
        return []

    items: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        # 匹配 "- item" 或 "* item" 或 "1. item"
        m = re.match(r"^[-*]\s+(.+)", line)
        if not m:
            m = re.match(r"^\d+[\.\)]\s+(.+)", line)
        if m:
            item = m.group(1).strip()
            if item and "无明确" not in item and "暂无" not in item:
                items.append(item)
    return items


def rebuild_index() -> dict:
    """扫描 memory/topics 下的 Markdown 文件，重建基础索引。

    兼容新旧两种 Markdown 格式：
    - 新格式含 ## 关键决策 / ## 待办事项 段落
    - 旧格式无这些段落，返回空列表
    """
    ensure_memory_dirs()
    index: dict = {}

    for path in TOPICS_DIR.glob("*.md"):
        if not is_memory_markdown(path):
            continue
        content = path.read_text(encoding="utf-8")

        # 解析一级标题 → topic
        first_heading = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
        topic = first_heading.group(1).strip() if first_heading else path.stem

        # 解析摘要
        summary_text = _parse_markdown_section(content, "摘要")
        if not summary_text:
            summary_text = simple_summary(content)
        summary = simple_summary(summary_text)

        # 解析关键词
        kw_text = _parse_markdown_section(content, "关键词")
        keywords: list[str] = []
        if kw_text and kw_text != "暂无":
            keywords = [k.strip() for k in re.split(r"[,，、\s]+", kw_text) if k.strip()]

        # 解析关键决策
        decisions = _parse_markdown_list(content, "关键决策")

        # 解析待办事项
        todos = _parse_markdown_list(content, "待办事项")

        # 文件时间
        stat = path.stat()
        created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        updated = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        key = slugify_topic(path.stem)
        index[key] = asdict(
            MemoryRecord(
                topic=topic,
                file=str(path.relative_to(PROJECT_ROOT)),
                keywords=keywords,
                summary=summary,
                decisions=decisions,
                todos=todos,
                created_at=created,
                updated_at=updated,
            )
        )

    save_index(index)
    return index
