"""
turn_counter.py — 对话轮次计数器

管理自动保存轮次状态：
  - 跟踪当前 session 的对话轮数
  - 达到设定间隔时触发自动保存
  - 支持 session 切换自动重置

状态文件: memory/.turn_state.json
格式: {"session_id": "...", "turn_count": N, "last_auto_save": "ISO8601"}
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

DEFAULT_INTERVAL = 10
STATE_FILE_NAME = ".turn_state.json"


def _get_state_path(memory_dir: Path) -> Path:
    return memory_dir / STATE_FILE_NAME


@dataclass
class TurnState:
    session_id: str = ""
    turn_count: int = 0
    last_auto_save: str = ""
    total_saves: int = 0


def load_state(memory_dir: Path) -> TurnState:
    """从状态文件加载轮次状态。文件不存在或损坏时返回初始状态。"""
    path = _get_state_path(memory_dir)
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return TurnState(
                session_id=data.get("session_id", ""),
                turn_count=data.get("turn_count", 0),
                last_auto_save=data.get("last_auto_save", ""),
                total_saves=data.get("total_saves", 0),
            )
    except (json.JSONDecodeError, OSError):
        pass
    return TurnState()


def save_state(memory_dir: Path, state: TurnState) -> None:
    """原子写入轮次状态。"""
    path = _get_state_path(memory_dir)
    memory_dir.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    data = asdict(state)
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        if tmp.exists():
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
        raise


def get_interval() -> int:
    """获取自动保存间隔（优先级：环境变量 > 默认 10）。"""
    env_val = os.environ.get("MEMORY_AUTO_SAVE_INTERVAL", "")
    if env_val:
        try:
            ival = int(env_val)
            if ival < 1:
                return DEFAULT_INTERVAL
            return ival
        except ValueError:
            pass
    return DEFAULT_INTERVAL


def should_auto_save(
    session_id: str = "",
    transcript_path: str = "",
    memory_dir: str = "",
    interval: int | None = None,
) -> tuple[bool, TurnState]:
    """检查是否应触发自动保存。

    每次调用将递增轮次计数。当轮次达到 interval 的整数倍时返回 True。

    Args:
        session_id: 当前会话 ID（用于区分不同会话，新会话自动重置计数）
        transcript_path: transcript 文件路径（用于日志/验证）
        memory_dir: 记忆目录路径（默认 "memory"）
        interval: 自动保存间隔（默认从环境变量读取或 10）

    Returns:
        (should_save, state): 是否应保存 + 更新后的状态
    """
    if interval is None:
        interval = get_interval()

    md = Path(memory_dir) if memory_dir else Path("memory")
    state = load_state(md)

    # 新会话 -> 重置计数
    if session_id and state.session_id != session_id:
        state.session_id = session_id
        state.turn_count = 0

    # 递增
    state.turn_count += 1

    should_save = (state.turn_count % interval) == 0

    if should_save:
        state.last_auto_save = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state.total_saves += 1

    save_state(md, state)

    return should_save, state


def reset_turn_count(memory_dir: str = "") -> None:
    """手动重置轮次计数（用于测试或手动干预）。"""
    md = Path(memory_dir) if memory_dir else Path("memory")
    state = load_state(md)
    state.turn_count = 0
    save_state(md, state)


def get_turn_count(memory_dir: str = "") -> int:
    """获取当前轮次计数（不递增）。"""
    md = Path(memory_dir) if memory_dir else Path("memory")
    return load_state(md).turn_count
