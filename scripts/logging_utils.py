"""
logging_utils.py — 日志系统

记录写入、检索、索引重建、Hook 调用和维护操作的审计日志。
安全约束：不记录完整原始对话，不记录 API Key / Token / 密码。
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGER_NAME = "claude_memory"
_logger: logging.Logger | None = None


def _sanitize(text: str, max_len: int = 120) -> str:
    """截断并清理文本，防止日志泄露完整对话。"""
    if not text:
        return ""
    text = text.replace("\n", " ").replace("\r", " ")
    if len(text) > max_len:
        text = text[:max_len] + "..."
    return text


def setup_logging(
    log_dir: str | Path = "logs",
    log_file: str = "claude_memory.log",
    level: str = "INFO",
    max_bytes: int = 1_048_576,
    backup_count: int = 3,
) -> logging.Logger:
    """初始化日志系统。

    Args:
        log_dir: 日志目录。
        log_file: 日志文件名。
        level: 日志级别（DEBUG / INFO / WARNING / ERROR）。
        max_bytes: 单个日志文件最大字节数。
        backup_count: 保留的历史日志文件数量。
    """
    global _logger

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    handler = RotatingFileHandler(
        str(log_path / log_file),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    """获取已配置的 logger（未初始化时使用默认配置）。"""
    global _logger
    if _logger is None:
        # 从环境变量读取配置
        level = os.environ.get("CLAUDE_MEMORY_LOG_LEVEL", "INFO")
        return setup_logging(level=level)
    return _logger


def log_save(topic: str, filepath: str, workspace: str = "") -> None:
    """记录记忆保存事件。"""
    get_logger().info(
        "SAVE | workspace=%s | topic=%s | file=%s",
        workspace or "default",
        _sanitize(topic, 80),
        filepath,
    )


def log_retrieve(query: str, top_k: int, hit_count: int, workspace: str = "") -> None:
    """记录检索事件。"""
    get_logger().info(
        "RETRIEVE | workspace=%s | query=%s | top_k=%d | hits=%d",
        workspace or "default",
        _sanitize(query, 100),
        top_k,
        hit_count,
    )


def log_rebuild(scan_count: int, index_count: int, workspace: str = "") -> None:
    """记录索引重建事件。"""
    get_logger().info(
        "REBUILD | workspace=%s | scanned=%d | indexed=%d",
        workspace or "default",
        scan_count,
        index_count,
    )


def log_maintenance(action: str, details: str = "", workspace: str = "") -> None:
    """记录维护操作。"""
    get_logger().info(
        "MAINTENANCE | workspace=%s | action=%s | %s",
        workspace or "default",
        action,
        _sanitize(details, 200),
    )


def log_error(message: str, exc_info: bool = False) -> None:
    """记录错误。"""
    get_logger().error(message, exc_info=exc_info)


def log_warning(message: str) -> None:
    """记录警告。"""
    get_logger().warning(message)
