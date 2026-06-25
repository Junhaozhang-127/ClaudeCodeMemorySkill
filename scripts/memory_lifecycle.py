"""
memory_lifecycle.py — 记忆生命周期管理 (v0.6.0)

提供:
  - transition_status: 状态变更（含 reason + timestamp）
  - auto_expire: 基于 TTL 的自动过期
  - generate_quality_report: 记忆质量报告
  - ttl_for_type: 按记忆类型推荐 TTL
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

# 默认 TTL 配置（天）
DEFAULT_TTL = 365
SHORT_TERM_TTL = 30

VALID_STATUSES = ("active", "archived", "expired", "merged", "deleted")
VALID_TRANSITIONS = {
    "active": ("archived", "expired", "merged", "deleted"),
    "archived": ("active", "expired", "merged", "deleted"),
    "expired": ("active", "archived", "deleted"),
    "merged": (),  # terminal
    "deleted": ("active",),  # 可恢复
}


def transition_status(
    index: dict,
    key: str,
    new_status: str,
    reason: str = "",
    merged_into: str = "",
) -> bool:
    """变更记忆状态。

    Args:
        index: 索引字典（原地修改）。
        key: 索引键。
        new_status: 目标状态。
        reason: 变更原因。
        merged_into: 当 new_status="merged" 时的目标键。

    Returns:
        True 如果变更成功。
    """
    if new_status not in VALID_STATUSES:
        return False
    if key not in index:
        return False

    record = index[key]
    old_status = record.get("status", "active")

    if old_status != new_status:
        allowed = VALID_TRANSITIONS.get(old_status, ())
        if new_status not in allowed and old_status != "active":
            # 只对非 active→any 做严格检查
            return False

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    record["status"] = new_status
    record["lifecycle_reason"] = reason
    record["lifecycle_changed_at"] = now

    if new_status == "merged" and merged_into:
        record["merged_into"] = merged_into
    if new_status == "archived":
        record["archived_at"] = now
    if new_status == "expired":
        record["expired_at"] = now
    if new_status == "deleted":
        record["deleted_at"] = now

    return True


def auto_expire(
    index: dict,
    days: int = 0,
    apply: bool = False,
) -> tuple[int, dict]:
    """自动过期记忆。

    Args:
        index: 索引字典。
        days: TTL 天数（0 时使用每条记忆自身的 ttl）。
        apply: True 时实际修改状态。

    Returns:
        (expired_count, updated_index)
    """
    index = dict(index)  # shallow copy
    expired = 0
    now = datetime.now()

    for key, record in list(index.items()):
        if record.get("status", "active") != "active":
            continue

        # 确定 TTL
        ttl = days
        if ttl <= 0:
            ttl = record.get("ttl_days", DEFAULT_TTL)
        if ttl <= 0:
            continue  # TTL=0 表示永不过期

        updated_str = record.get("updated_at", "")
        if not updated_str:
            continue

        try:
            updated_dt = datetime.strptime(updated_str, "%Y-%m-%d %H:%M:%S")
            if (now - updated_dt).days > ttl:
                if apply:
                    transition_status(index, key, "expired",
                                     reason=f"TTL expired ({ttl}d)")
                expired += 1
        except (ValueError, TypeError):
            pass

    return expired, index


def content_hash(text: str) -> str:
    """计算内容 hash（16 位 hex）。"""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def generate_quality_report(workspace: str = "") -> dict:
    """生成记忆质量报告。

    Returns:
        dict with keys: total, active, archived, expired, merged, deleted,
                       duplicate_candidates, near_duplicate_candidates,
                       conflict_candidates, expired_candidates,
                       low_quality_count, recommended_actions
    """
    try:
        from memory_core import load_index, _resolve_paths
    except ImportError:
        return _empty_report()

    try:
        from memory_maintenance import detect_duplicates
        _maintenance_available = True
    except ImportError:
        _maintenance_available = False

    _, topics_dir, _ = _resolve_paths(workspace)
    index = load_index(workspace)

    report = {
        "total": len(index),
        "active": 0, "archived": 0, "expired": 0,
        "merged": 0, "deleted": 0,
        "duplicate_candidates": 0,
        "near_duplicate_candidates": 0,
        "conflict_candidates": 0,
        "expired_candidates": 0,
        "low_quality_count": 0,
        "recommended_actions": [],
    }

    for key, rec in index.items():
        status = rec.get("status", "active")
        report[status] = report.get(status, 0) + 1

        # 低质量检测
        has_summary = bool(rec.get("summary", "").strip())
        has_keywords = bool(rec.get("keywords", []))
        if not has_summary or not has_keywords:
            report["low_quality_count"] += 1

        # 过期候选
        updated = rec.get("updated_at", "")
        if updated and status == "active":
            try:
                dt = datetime.strptime(updated, "%Y-%m-%d %H:%M:%S")
                ttl = rec.get("ttl_days", DEFAULT_TTL)
                if ttl > 0 and (datetime.now() - dt).days > ttl:
                    report["expired_candidates"] += 1
            except ValueError:
                pass

    # 去重检测
    if _maintenance_available and len(index) >= 2:
        pairs = detect_duplicates(index, threshold=0.7)
        report["duplicate_candidates"] = len(pairs)
        near_pairs = detect_duplicates(index, threshold=0.4)
        report["near_duplicate_candidates"] = max(0, len(near_pairs) - len(pairs))

    # 推荐清理动作
    if report["expired_candidates"] > 0:
        report["recommended_actions"].append(
            f"过期 {report['expired_candidates']} 条: 运行 /memory manage expire --apply"
        )
    if report["duplicate_candidates"] > 0:
        report["recommended_actions"].append(
            f"重复 {report['duplicate_candidates']} 对: 运行 /memory manage dedup"
        )
    if report["low_quality_count"] > 0:
        report["recommended_actions"].append(
            f"低质量 {report['low_quality_count']} 条: 缺少摘要或关键词"
        )

    return report


def _empty_report() -> dict:
    return {
        "total": 0, "active": 0, "archived": 0, "expired": 0,
        "merged": 0, "deleted": 0,
        "duplicate_candidates": 0, "near_duplicate_candidates": 0,
        "conflict_candidates": 0, "expired_candidates": 0,
        "low_quality_count": 0,
        "recommended_actions": [],
    }
