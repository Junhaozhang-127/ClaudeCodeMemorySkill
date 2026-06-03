"""
memory_core.py — Claude Code Memory Skill 核心逻辑

Phase 4 增强：
  - workspace 项目隔离
  - 混合检索 + score_breakdown
  - 索引备份 + 文件锁
  - 路径安全校验
  - Markdown fence 转义
  - 日志集成

保持所有 Phase 1/2/3 接口向后兼容。
"""

from __future__ import annotations

import json
import os
import re
import time
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

# ── Phase 4 模块（项目内导入）────────────────────────────────
try:
    from retrieval import HybridRetriever, KeywordRetriever
    _RETRIEVAL_AVAILABLE = True
except ImportError:
    _RETRIEVAL_AVAILABLE = False

try:
    from logging_utils import log_save, log_retrieve, log_rebuild, log_warning, log_error
    _LOGGING_AVAILABLE = True
except ImportError:
    _LOGGING_AVAILABLE = False
    def _noop(*a, **kw): pass
    log_save = log_retrieve = log_rebuild = log_warning = log_error = _noop


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = PROJECT_ROOT / "memory"
TOPICS_DIR = MEMORY_DIR / "topics"
INDEX_FILE = MEMORY_DIR / "index.json"

# 索引备份最大保留数
_MAX_BACKUPS = 10
# 文件锁超时（秒）
_LOCK_TIMEOUT = 5.0


# ═══════════════════════════════════════════════════════════════
# Workspace 路径解析
# ═══════════════════════════════════════════════════════════════

def _get_env_workspace() -> str:
    """从环境变量读取默认 workspace。"""
    import os
    ws = os.environ.get("CLAUDE_MEMORY_WORKSPACE", "")
    if ws:
        return ws
    md = os.environ.get("CLAUDE_MEMORY_DIR", "")
    if md:
        return md  # 直接路径作为 workspace ID
    return ""


def _resolve_paths(workspace: str = ""):
    """根据 workspace_id 解析记忆目录路径。

    优先级：参数 > 环境变量 CLAUDE_MEMORY_WORKSPACE > 默认 legacy。
    workspace 为空 / "default" 时使用旧 memory/ 路径。
    """
    if not workspace:
        workspace = _get_env_workspace()
    if not workspace or workspace == "default":
        return MEMORY_DIR, TOPICS_DIR, INDEX_FILE
    base = MEMORY_DIR / "workspaces" / workspace
    return base, base / "topics", base / "index.json"


# ═══════════════════════════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════════════════════════

@dataclass
class MemoryRecord:
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
    "因为", "所以", "如果", "然后", "之后", "之前",
    "一些", "所有", "很多", "非常", "比较", "可能", "应该",
    "不是", "没有", "还是", "只是", "就是", "还有",
    "这样", "那样", "这些", "那些", "这里", "那里", "自己",
    "知道", "觉得", "认为", "希望", "想", "要", "会", "能",
}
_EN_STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "can", "shall",
    "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after",
    "this", "that", "these", "those", "it", "its", "he", "she",
    "they", "them", "we", "us", "i", "you", "me", "my", "your",
}
_STOP_WORDS = _CN_STOP_WORDS | _EN_STOP_WORDS


# ═══════════════════════════════════════════════════════════════
# 文件过滤
# ═══════════════════════════════════════════════════════════════

def is_memory_markdown(path: Path) -> bool:
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
# 目录 + 索引 I/O（含备份 + 锁）
# ═══════════════════════════════════════════════════════════════

def ensure_memory_dirs(workspace: str = "") -> None:
    _, topics_dir, index_file = _resolve_paths(workspace)
    topics_dir.mkdir(parents=True, exist_ok=True)
    if not index_file.exists():
        index_file.write_text("{}", encoding="utf-8")


def slugify_topic(topic: str) -> str:
    topic = topic.strip() or "untitled"
    topic = re.sub(r"[\\/:*?\"<>|]+", "_", topic)
    topic = re.sub(r"\s+", "_", topic)
    return topic[:80]


def load_index(workspace: str = "") -> dict:
    _, _, index_file = _resolve_paths(workspace)
    try:
        return json.loads(index_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        # 尝试从备份恢复
        recovered = _try_restore_from_backup(index_file)
        if recovered is not None:
            log_warning(f"index.json 已损坏，已从备份恢复: {index_file}")
            return recovered
        log_warning(f"index.json 损坏且无可用备份: {index_file}")
        return {}


def _try_restore_from_backup(index_file: Path) -> dict | None:
    """尝试从最近备份恢复索引。"""
    backup_dir = index_file.parent / "backups"
    if not backup_dir.exists():
        return None
    backups = sorted(backup_dir.glob("index_*.json"), reverse=True)
    for bk in backups:
        try:
            data = json.loads(bk.read_text(encoding="utf-8"))
            if data:
                return data
        except json.JSONDecodeError:
            continue
    return None


def _acquire_lock(lock_path: Path, timeout: float = _LOCK_TIMEOUT) -> bool:
    """尝试获取文件锁。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            return True
        except (OSError, FileExistsError):
            time.sleep(0.05)
    return False


def _release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except (FileNotFoundError, OSError):
        pass


def _backup_index(index_file: Path, max_backups: int = _MAX_BACKUPS) -> None:
    """在覆盖前创建索引备份。"""
    if not index_file.exists():
        return
    backup_dir = index_file.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = backup_dir / f"index_{ts}.json"
    try:
        bak.write_text(index_file.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        return  # 备份失败不影响主流程
    # 清理旧备份
    all_baks = sorted(backup_dir.glob("index_*.json"))
    for old in all_baks[:-max_backups]:
        try:
            old.unlink()
        except Exception:
            pass


def save_index(index: dict, workspace: str = "") -> None:
    """原子写入 index.json（含备份 + 锁）。"""
    _, _, index_file = _resolve_paths(workspace)
    ensure_memory_dirs(workspace)

    # 备份
    _backup_index(index_file)

    # 锁
    lock_path = index_file.with_suffix(index_file.suffix + ".lock")
    locked = _acquire_lock(lock_path)
    if not locked:
        log_warning(f"无法获取索引锁，跳过写入: {index_file}")

    tmp_path = index_file.with_name("index.json.tmp")
    json_text = json.dumps(index, ensure_ascii=False, indent=2)
    try:
        tmp_path.write_text(json_text, encoding="utf-8")
        os.replace(tmp_path, index_file)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except FileNotFoundError:
                pass
        raise
    finally:
        if locked:
            _release_lock(lock_path)


# ═══════════════════════════════════════════════════════════════
# 关键词抽取
# ═══════════════════════════════════════════════════════════════

def _extract_keywords_jieba(text: str, topic: str, max_keywords: int = 10) -> list[str]:
    import jieba as _jieba
    candidates: list[str] = []
    for part in re.split(r"[_\s,，。；;:：/\\\-]+", topic):
        part = part.strip()
        if part:
            candidates.append(part)
    candidates.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text))
    for word in _jieba.cut(text):
        word = word.strip()
        if not word or len(word) < 2:
            continue
        if word.lower() in _STOP_WORDS:
            continue
        if re.fullmatch(r"[\d\.\,\;\:\!\?\-]+", word):
            continue
        candidates.append(word)
    seen: set[str] = set()
    result: list[str] = []
    for item in candidates:
        item = item.strip()
        if not item or item in seen or item.lower() in _STOP_WORDS:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= max_keywords:
            break
    return result


def _extract_keywords_regex(text: str, topic: str, max_keywords: int = 10) -> list[str]:
    candidates: list[str] = []
    for part in re.split(r"[_\s,，。；;:：/\\\-]+", topic):
        part = part.strip()
        if part:
            candidates.append(part)
    candidates.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}", text))
    for term in re.findall(r"[一-鿿]{2,8}", text):
        if len(term) >= 2 and term not in _STOP_WORDS:
            candidates.append(term)
    seen: set[str] = set()
    result: list[str] = []
    for item in candidates:
        item = item.strip()
        if not item or item in seen or item.lower() in _STOP_WORDS:
            continue
        seen.add(item)
        result.append(item)
        if len(result) >= max_keywords:
            break
    return result


def extract_keywords(text: str, topic: str = "", max_keywords: int = 10) -> list[str]:
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
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def _get_default_summarizer():
    from summarizers import RuleBasedSummarizer
    return RuleBasedSummarizer(keyword_extractor=extract_keywords)


# ═══════════════════════════════════════════════════════════════
# Markdown fence 转义
# ═══════════════════════════════════════════════════════════════

def _safe_code_fence(text: str) -> str:
    """防止原文中的 ``` 破坏 Markdown 结构。"""
    # 将原文中的连续反引号用更长 fence 包裹，或转义
    if "```" in text:
        # 使用 4 反引号 fence 替代 3 反引号
        return text.replace("```", "`​``")  # zero-width space 防合并
    return text


# ═══════════════════════════════════════════════════════════════
# 记忆保存
# ═══════════════════════════════════════════════════════════════

def save_memory(
    topic: str,
    conversation_text: str,
    append: bool = True,
    summarizer=None,
    workspace: str = "",
) -> Path:
    ensure_memory_dirs(workspace)
    _, topics_dir, index_file = _resolve_paths(workspace)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date_str = datetime.now().strftime("%Y-%m-%d")
    safe_topic = slugify_topic(topic)
    filename = f"{safe_topic}_{date_str}.md"
    filepath = topics_dir / filename

    if summarizer is None:
        summarizer = _get_default_summarizer()
    result = summarizer.summarize(conversation_text, topic)

    summary = result.summary or simple_summary(conversation_text)
    keywords = result.keywords if result.keywords else extract_keywords(conversation_text, topic)
    decisions_lines = _format_list_section(result.decisions, "无明确关键决策。")
    todos_lines = _format_list_section(result.todos, "无明确待办事项。")
    keywords_str = ", ".join(keywords) if keywords else "暂无"

    # 转义原文中的 fence
    safe_text = _safe_code_fence(conversation_text.strip())

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

````text
{safe_text}
````

---

"""

    if filepath.exists() and append:
        with filepath.open("a", encoding="utf-8") as f:
            f.write("\n\n" + block)
    else:
        filepath.write_text(block, encoding="utf-8")

    index = load_index(workspace)
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
    save_index(index, workspace)

    log_save(topic, str(filepath), workspace)
    return filepath


def _format_list_section(items: list[str], fallback: str) -> str:
    if not items:
        return fallback
    return "\n".join(f"- {item}" for item in items)


# ═══════════════════════════════════════════════════════════════
# 检索评分（Phase 2 算法，保留兼容）
# ═══════════════════════════════════════════════════════════════

def score_record(query: str, record: dict) -> int:
    query_lower = query.lower()
    score = 0
    topic = str(record.get("topic", ""))
    topic_lower = topic.lower()
    summary = str(record.get("summary", ""))
    keywords = [str(k).lower() for k in record.get("keywords", [])]
    decisions = [str(d).lower() for d in record.get("decisions", [])]
    todos = [str(t).lower() for t in record.get("todos", [])]

    if topic_lower and topic_lower in query_lower:
        score += 15

    tokens = _tokenize_query(query)
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
        if token in summary.lower():
            score += 2
        for dec in decisions:
            if token in dec:
                score += 3
                break
        for td in todos:
            if token in td:
                score += 3
                break

    if score > 0:
        try:
            updated_str = str(record.get("updated_at", ""))
            if updated_str:
                updated_dt = datetime.strptime(updated_str, "%Y-%m-%d %H:%M:%S")
                days_ago = (datetime.now() - updated_dt).days
                if days_ago <= 7:
                    score += 2
                elif days_ago <= 30:
                    score += 1
        except (ValueError, TypeError):
            pass
    return score


def _tokenize_query(query: str) -> list[str]:
    tokens: list[str] = []
    tokens.extend(re.findall(r"[A-Za-z][A-Za-z0-9_\-]{1,}", query))
    chinese_chars = re.findall(r"[一-鿿]+", query)
    for chunk in chinese_chars:
        for wlen in (4, 3, 2):
            for i in range(len(chunk) - wlen + 1):
                tokens.append(chunk[i:i + wlen])
    return [t.strip() for t in tokens if len(t.strip()) >= 2 and t.strip().lower() not in _STOP_WORDS]


# ═══════════════════════════════════════════════════════════════
# 路径安全校验
# ═══════════════════════════════════════════════════════════════

def _validate_file_path(file_rel: str, workspace: str = ""):
    """校验 index.json 中的 file 字段是否安全。

    防止路径遍历攻击：file 必须 resolve 后位于当前 workspace topics/ 目录下。

    Returns:
        Path: 安全文件路径（文件存在）
        None: 路径在 topics 内但文件不存在
        False: 路径越界（应跳过该记录）
    """
    if not file_rel:
        return None
    _, topics_dir, _ = _resolve_paths(workspace)
    resolved = (PROJECT_ROOT / file_rel).resolve()
    topics_resolved = topics_dir.resolve()
    try:
        resolved.relative_to(topics_resolved)
    except ValueError:
        log_warning(f"路径越界，已跳过: {file_rel}")
        return False
    return resolved if resolved.exists() else None


# ═══════════════════════════════════════════════════════════════
# 记忆检索
# ═══════════════════════════════════════════════════════════════

def _safe_get_list(record: dict, key: str) -> list[str]:
    val = record.get(key, [])
    return val if isinstance(val, list) else []


def retrieve_memory(
    query: str,
    top_k: int = 5,
    workspace: str = "",
    retriever=None,
) -> list[dict]:
    index = load_index(workspace)
    # 将 index key 注入为 id，确保每条记录可追溯和去重
    records = []
    for key, val in index.items():
        val["id"] = key
        records.append(val)

    if retriever is None and _RETRIEVAL_AVAILABLE:
        retriever = HybridRetriever(score_fn=score_record)

    if retriever is not None:
        results = retriever.retrieve(query, records, top_k)
    else:
        # 回退：使用原有 score_record 逻辑
        results = _legacy_retrieve(query, records, top_k)

    # 路径校验 + 读取内容 + 过滤越界记录 + 去重
    validated = []
    seen_ids: set[str] = set()
    for r in results:
        file_rel = r.get("file", "")
        safe_path = _validate_file_path(file_rel, workspace)
        if safe_path is False:
            # 路径越界，跳过该记录
            continue
        content = ""
        if safe_path:
            content = safe_path.read_text(encoding="utf-8")
        r["content"] = content
        if "decisions" not in r:
            r["decisions"] = _safe_get_list(r, "decisions")
        if "todos" not in r:
            r["todos"] = _safe_get_list(r, "todos")
        if "keywords" not in r:
            r["keywords"] = _safe_get_list(r, "keywords")
        if "score_breakdown" not in r:
            r["score_breakdown"] = {"total": r.get("score", 0)}
        if "matched_fields" not in r:
            r["matched_fields"] = []
        # 去重（按 id 字段）
        rid = r.get("id", "")
        if rid and rid in seen_ids:
            continue
        if rid:
            seen_ids.add(rid)
        validated.append(r)

    log_retrieve(query, top_k, len(validated), workspace)
    return validated[:top_k]


def _legacy_retrieve(query: str, records: list[dict], top_k: int) -> list[dict]:
    """回退检索（无 retrieval.py 时使用）。"""
    scored = []
    for record in records:
        score = score_record(query, record)
        if score <= 0:
            continue
        item = dict(record)
        item["score"] = score
        item["score_breakdown"] = {"total": score}
        item["matched_fields"] = []
        scored.append(item)
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


# ═══════════════════════════════════════════════════════════════
# 上下文格式化
# ═══════════════════════════════════════════════════════════════

def format_context(results: Iterable[dict], max_chars_per_item: int = 1200) -> str:
    """格式化检索结果为可注入上下文。

    优先展示：摘要 → 关键决策 → 待办事项 → 内容片段。
    max_chars_per_item 控制每条完整块的近似最大长度。
    """
    blocks = []
    for i, item in enumerate(results, start=1):
        topic = item.get("topic", "未知主题")
        file_path = item.get("file", "")
        score = item.get("score", 0)
        summary = item.get("summary", "")
        decisions = _safe_get_list(item, "decisions")
        todos = _safe_get_list(item, "todos")
        score_breakdown = item.get("score_breakdown", {})
        matched = item.get("matched_fields", [])

        parts: list[str] = []
        remaining = max_chars_per_item

        # 摘要
        if summary:
            snip = summary if len(summary) <= 180 else summary[:177] + "..."
            parts.append(f"**摘要**：{snip}")
            remaining -= len(snip) + 10

        # 关键决策
        if decisions and remaining > 40:
            dec_text = "；".join(decisions[:3])
            if len(dec_text) > 150:
                dec_text = dec_text[:147] + "..."
            parts.append(f"**关键决策**：{dec_text}")
            remaining -= len(dec_text) + 15

        # 待办事项
        if todos and remaining > 40:
            todo_text = "；".join(todos[:3])
            if len(todo_text) > 150:
                todo_text = todo_text[:147] + "..."
            parts.append(f"**待办事项**：{todo_text}")
            remaining -= len(todo_text) + 15

        # score breakdown（精简）
        if score_breakdown and len(score_breakdown) > 1 and remaining > 30:
            bd_str = ", ".join(f"{k}:{v}" for k, v in score_breakdown.items() if v > 0)
            if len(bd_str) > 100:
                bd_str = bd_str[:97] + "..."
            parts.append(f"**评分**：{bd_str}")
            remaining -= len(bd_str) + 12

        # 匹配字段
        if matched and remaining > 20:
            parts.append(f"**命中**：{', '.join(matched[:4])}")
            remaining -= 30

        # 内容补充（低优先级，严格截断）
        if remaining > 60:
            content = item.get("content", "")
            content = re.sub(r"\s*\n\s*\n\s*", " ", content)
            content = re.sub(r"\s+", " ", content)
            if len(content) > remaining - 5:
                content = content[:remaining - 5] + "..."
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
# 索引重建
# ═══════════════════════════════════════════════════════════════

def _parse_markdown_section(content: str, heading: str) -> str:
    pattern = rf"## {re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)"
    match = re.search(pattern, content, flags=re.S)
    return match.group(1).strip() if match else ""


def _parse_markdown_list(content: str, heading: str) -> list[str]:
    text = _parse_markdown_section(content, heading)
    if not text:
        return []
    items: list[str] = []
    for line in text.split("\n"):
        line = line.strip()
        m = re.match(r"^[-*]\s+(.+)", line)
        if not m:
            m = re.match(r"^\d+[\.\)]\s+(.+)", line)
        if m:
            item = m.group(1).strip()
            if item and "无明确" not in item and "暂无" not in item:
                items.append(item)
    return items


def rebuild_index(workspace: str = "") -> dict:
    _, topics_dir, _ = _resolve_paths(workspace)
    ensure_memory_dirs(workspace)
    index: dict = {}
    scan_count = 0

    for path in topics_dir.glob("*.md"):
        if not is_memory_markdown(path):
            continue
        scan_count += 1
        content = path.read_text(encoding="utf-8")

        first_heading = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
        topic = first_heading.group(1).strip() if first_heading else path.stem

        summary_text = _parse_markdown_section(content, "摘要")
        summary = simple_summary(summary_text) if summary_text else simple_summary(content)

        kw_text = _parse_markdown_section(content, "关键词")
        keywords = []
        if kw_text and kw_text != "暂无":
            keywords = [k.strip() for k in re.split(r"[,，、\s]+", kw_text) if k.strip()]

        decisions = _parse_markdown_list(content, "关键决策")
        todos = _parse_markdown_list(content, "待办事项")

        stat = path.stat()
        created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
        updated = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")

        key = slugify_topic(path.stem)
        index[key] = asdict(MemoryRecord(
            topic=topic,
            file=str(path.relative_to(PROJECT_ROOT)),
            keywords=keywords,
            summary=summary,
            decisions=decisions,
            todos=todos,
            created_at=created,
            updated_at=updated,
        ))

    save_index(index, workspace)
    log_rebuild(scan_count, len(index), workspace)
    return index
