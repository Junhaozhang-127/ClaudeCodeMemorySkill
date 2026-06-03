"""
memory_maintenance.py — 记忆维护命令

提供：
  - detect-duplicates: 检测可能重复的记忆
  - merge: 合并同主题/高相似记忆
  - compact: 压缩过长 Markdown
  - archive-old: 归档旧记忆

所有破坏性操作默认 dry-run，需 --apply 才生效。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 与 memory_core 保持一致的 slug 函数
def _slugify(topic: str) -> str:
    topic = topic.strip() or "untitled"
    topic = re.sub(r"[\\/:*?\"<>|]+", "_", topic)
    topic = re.sub(r"\s+", "_", topic)
    return topic[:80]


def _load_index(index_path: Path) -> dict:
    try:
        return json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def _save_index(index: dict, index_path: Path) -> None:
    index_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ═══════════════════════════════════════════════════════════════
# 相似度检测
# ═══════════════════════════════════════════════════════════════

def _jaccard(a: Iterable[str], b: Iterable[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def detect_duplicates(index: dict, threshold: float = 0.5) -> list[tuple[str, str, float]]:
    """检测可能重复的记忆条目。

    使用关键词 Jaccard 相似度 + 主题重叠度。
    返回 [(key_a, key_b, similarity), ...]。
    """
    keys = list(index.keys())
    pairs = []
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            ra = index[keys[i]]
            rb = index[keys[j]]
            kw_sim = _jaccard(
                ra.get("keywords", []), rb.get("keywords", [])
            )
            topic_a = set(re.split(r"[_\s]+", str(ra.get("topic", ""))))
            topic_b = set(re.split(r"[_\s]+", str(rb.get("topic", ""))))
            topic_sim = _jaccard(topic_a, topic_b)
            sim = max(kw_sim, topic_sim)
            if sim >= threshold:
                pairs.append((keys[i], keys[j], round(sim, 3)))
    pairs.sort(key=lambda x: x[2], reverse=True)
    return pairs


# ═══════════════════════════════════════════════════════════════
# 记忆合并
# ═══════════════════════════════════════════════════════════════

def merge_memories(
    index: dict,
    topics_dir: Path,
    topic_keys: list[str],
    apply: bool = False,
) -> dict | None:
    """合并多条记忆为一条。

    Args:
        index: 当前索引。
        topics_dir: topics 目录。
        topic_keys: 要合并的索引 key 列表。
        apply: False 时为 dry-run，只预览。

    Returns:
        apply=False 时返回预览信息字典；apply=True 时返回 None。
    """
    if len(topic_keys) < 2:
        print("至少需要 2 条记忆才能合并。")
        return None

    records = [index[k] for k in topic_keys if k in index]
    if len(records) < 2:
        print("在索引中未找到足够的记录。")
        return None

    # 收集信息
    all_topics = [r["topic"] for r in records]
    all_decisions: list[str] = []
    all_todos: list[str] = []
    all_keywords: list[str] = []
    all_files = [r["file"] for r in records]
    latest_updated = max(r.get("updated_at", "") for r in records)

    for r in records:
        all_decisions.extend(r.get("decisions", []))
        all_todos.extend(r.get("todos", []))
        all_keywords.extend(r.get("keywords", []))

    # 去重
    seen_d = set()
    unique_decisions = [d for d in all_decisions if not (d in seen_d or seen_d.add(d))]
    seen_t = set()
    unique_todos = [t for t in all_todos if not (t in seen_t or seen_t.add(t))]
    seen_k = set()
    unique_keywords = [k for k in all_keywords if not (k in seen_k or seen_k.add(k))][:10]

    primary = records[0]

    preview = {
        "sources": all_files,
        "merged_topic": primary["topic"],
        "decisions_count": len(unique_decisions),
        "todos_count": len(unique_todos),
        "keywords_count": len(unique_keywords),
        "latest_updated": latest_updated,
        "files_to_backup": all_files,
    }

    if not apply:
        return preview

    # 实际合并
    import os
    archive_dir = topics_dir.parent / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # 备份原文件
    for f in all_files[1:]:
        src = PROJECT_ROOT / f
        if src.exists():
            dst = archive_dir / src.name
            os.replace(str(src), str(dst))

    # 更新索引
    merged_key = topic_keys[0]
    index[merged_key] = {
        "topic": primary["topic"],
        "file": all_files[0],
        "keywords": unique_keywords,
        "summary": primary.get("summary", ""),
        "decisions": unique_decisions[:5],
        "todos": unique_todos[:8],
        "created_at": primary.get("created_at", ""),
        "updated_at": latest_updated,
        "_merged_from": all_files[1:],
    }
    for k in topic_keys[1:]:
        index.pop(k, None)

    _save_index(index, topics_dir.parent / "index.json")
    print(f"合并完成：{len(topic_keys)} 条 -> 1 条 ({primary['topic']})")
    print(f"备份文件已移至: {archive_dir}")
    return None


# ═══════════════════════════════════════════════════════════════
# 主题压缩
# ═══════════════════════════════════════════════════════════════

def compact_topic(
    markdown_path: Path,
    max_blocks: int = 3,
    apply: bool = False,
) -> str | None:
    """压缩过长 Markdown 记忆文件。

    保留：摘要、关键决策、待办、最近 N 个对话块。
    """
    if not markdown_path.exists():
        print(f"文件不存在: {markdown_path}")
        return None

    content = markdown_path.read_text(encoding="utf-8")
    blocks = content.split("\n---\n")
    if len(blocks) <= max_blocks:
        return "无需压缩（已足够精简）。"

    # 保留：头部块 + 最后 (max_blocks - 1) 个块
    kept = [blocks[0]] + blocks[-(max_blocks - 1):] if max_blocks > 1 else [blocks[0]]
    new_content = "\n---\n".join(kept)
    if not new_content.endswith("\n---\n"):
        new_content = new_content.rstrip() + "\n\n---\n"

    preview = (
        f"文件: {markdown_path}\n"
        f"原始块数: {len(blocks)}\n"
        f"压缩后块数: {len(kept)}\n"
        f"原始大小: {len(content)} 字符\n"
        f"压缩后大小: {len(new_content)} 字符"
    )

    if not apply:
        return preview

    # 备份 + 写入
    bak = markdown_path.with_suffix(markdown_path.suffix + ".bak")
    markdown_path.replace(bak)
    markdown_path.write_text(new_content, encoding="utf-8")
    print(f"压缩完成。备份: {bak}")
    return None


# ═══════════════════════════════════════════════════════════════
# 归档旧记忆
# ═══════════════════════════════════════════════════════════════

def archive_old(
    index: dict,
    topics_dir: Path,
    days: int = 180,
    apply: bool = False,
) -> dict | None:
    """将超过指定天数的记忆归档。

    Returns:
        apply=False 时返回预览信息；apply=True 时返回 None。
    """
    cutoff = datetime.now()
    to_archive: list[str] = []

    for key, record in index.items():
        updated = record.get("updated_at", "")
        if not updated:
            continue
        try:
            dt = datetime.strptime(updated, "%Y-%m-%d %H:%M:%S")
            if (cutoff - dt).days > days:
                to_archive.append(key)
        except ValueError:
            continue

    preview = {
        "cutoff_days": days,
        "to_archive_count": len(to_archive),
        "to_archive_keys": to_archive,
        "remaining_count": len(index) - len(to_archive),
    }

    if not apply:
        return preview

    # 实际归档
    import os
    archive_dir = topics_dir.parent / "archive"
    archive_topics = archive_dir / "topics"
    archive_topics.mkdir(parents=True, exist_ok=True)

    for key in to_archive:
        record = index.pop(key, None)
        if not record:
            continue
        src = PROJECT_ROOT / record.get("file", "")
        if src.exists():
            os.replace(str(src), str(archive_topics / src.name))

    index_path = topics_dir.parent / "index.json"
    _save_index(index, index_path)
    print(f"归档完成：{len(to_archive)} 条记忆移至 {archive_dir}")
    return None


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(description="Memory maintenance commands")
    sub = parser.add_subparsers(dest="command")

    # detect-duplicates
    dup = sub.add_parser("detect-duplicates")
    dup.add_argument("--workspace", default="")
    dup.add_argument("--threshold", type=float, default=0.5)

    # merge
    mg = sub.add_parser("merge")
    mg.add_argument("--workspace", default="")
    mg.add_argument("--topic", required=True)
    mg.add_argument("--dry-run", action="store_true", default=True)
    mg.add_argument("--apply", action="store_true")

    # compact
    cp = sub.add_parser("compact")
    cp.add_argument("--workspace", default="")
    cp.add_argument("--topic", required=True)
    cp.add_argument("--dry-run", action="store_true", default=True)
    cp.add_argument("--apply", action="store_true")

    # archive-old
    ao = sub.add_parser("archive-old")
    ao.add_argument("--workspace", default="")
    ao.add_argument("--days", type=int, default=180)
    ao.add_argument("--dry-run", action="store_true", default=True)
    ao.add_argument("--apply", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # resolve paths
    if args.workspace and args.workspace != "default":
        mem_root = PROJECT_ROOT / "memory"
        base = mem_root / "workspaces" / args.workspace
        idx_path = base / "index.json"
        top_dir = base / "topics"
    else:
        idx_path = PROJECT_ROOT / "memory" / "index.json"
        top_dir = PROJECT_ROOT / "memory" / "topics"

    index = _load_index(idx_path)

    if args.command == "detect-duplicates":
        pairs = detect_duplicates(index, args.threshold)
        if pairs:
            print(f"发现 {len(pairs)} 对可能重复的记忆：")
            for a, b, sim in pairs:
                ia = index.get(a, {}).get("topic", a)
                ib = index.get(b, {}).get("topic", b)
                print(f"  [{sim:.2f}] {ia}  <->  {ib}")
        else:
            print("未发现重复记忆。")

    elif args.command == "merge":
        # 使用 slugified topic 做匹配，兼容中文和空格
        slug = _slugify(args.topic)
        keys = [k for k in index
                if slug in k
                or slug in _slugify(index[k].get("topic", ""))
                or args.topic in index[k].get("topic", "")]
        if len(keys) < 2:
            print(f"未找到多条可合并的记忆（topic 匹配: {args.topic}）")
            return
        apply = args.apply and not args.dry_run
        result = merge_memories(index, top_dir, keys, apply=apply)
        if result:
            print("\n[Dry-run 预览]")
            print(json.dumps(result, ensure_ascii=False, indent=2))

    elif args.command == "compact":
        # 使用 slugified topic + 原 topic 双模式 glob
        slug = _slugify(args.topic)
        found = list(top_dir.glob(f"*{slug}*.md"))
        if not found:
            # 回退：尝试原 topic 前 20 字符匹配
            found = list(top_dir.glob(f"*{args.topic[:20]}*.md"))
        if not found:
            print(f"未找到匹配的 Markdown 文件（topic: {args.topic}）")
            return
        apply = args.apply and not args.dry_run
        result = compact_topic(found[0], apply=apply)
        if result:
            print(result)

    elif args.command == "archive-old":
        apply = args.apply and not args.dry_run
        result = archive_old(index, top_dir, days=args.days, apply=apply)
        if result:
            print("\n[Dry-run 预览]")
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
