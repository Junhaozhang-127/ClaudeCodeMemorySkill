"""
config.py — Memory Skill 配置管理

支持 workspace 级隔离、环境变量覆盖、新旧路径兼容。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# 默认记忆根目录（相对于项目根）
_DEFAULT_MEMORY_ROOT = "memory"

# 旧路径（无 workspace 时使用）
_LEGACY_INDEX = Path("memory/index.json")
_LEGACY_TOPICS = Path("memory/topics")


@dataclass
class MemoryConfig:
    """Memory Skill 运行配置。"""

    project_root: Path = field(default_factory=lambda: Path.cwd())
    memory_root: str = _DEFAULT_MEMORY_ROOT

    # workspace_id 为 None 或 "" 或 "default" 时使用旧路径
    workspace_id: str = ""

    # 检索
    top_k: int = 5
    max_chars_per_item: int = 1200

    # 日志
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_file: str = "claude_memory.log"
    log_max_bytes: int = 1_048_576  # 1 MB
    log_backup_count: int = 3

    # 索引备份
    index_backup_max: int = 10

    # 访问统计
    track_access: bool = False

    # 文件锁超时（秒）
    lock_timeout: float = 5.0

    @property
    def is_legacy_mode(self) -> bool:
        """当前是否使用旧路径（无 workspace 隔离）。"""
        return not self.workspace_id or self.workspace_id in ("default",)

    @property
    def memory_dir(self) -> Path:
        """记忆根目录。"""
        return self.project_root / self.memory_root

    @property
    def index_path(self) -> Path:
        """index.json 路径。"""
        if self.is_legacy_mode:
            return self.project_root / _LEGACY_INDEX
        return self.memory_dir / "workspaces" / self.workspace_id / "index.json"

    @property
    def topics_dir(self) -> Path:
        """topics 目录路径。"""
        if self.is_legacy_mode:
            return self.project_root / _LEGACY_TOPICS
        return self.memory_dir / "workspaces" / self.workspace_id / "topics"

    @property
    def backup_dir(self) -> Path:
        """索引备份目录。"""
        base = self.memory_dir if self.is_legacy_mode else (
            self.memory_dir / "workspaces" / self.workspace_id
        )
        return base / "backups"

    @property
    def archive_dir(self) -> Path:
        """归档目录。"""
        base = self.memory_dir if self.is_legacy_mode else (
            self.memory_dir / "workspaces" / self.workspace_id
        )
        return base / "archive"

    @property
    def lock_path(self) -> Path:
        """索引锁文件路径。"""
        p = self.index_path
        return p.with_suffix(p.suffix + ".lock")

    def ensure_dirs(self) -> None:
        """确保所需目录存在。"""
        self.topics_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self.index_path.write_text("{}", encoding="utf-8")


def _load_from_env(cfg: MemoryConfig) -> MemoryConfig:
    """从环境变量覆盖配置。"""
    ws = os.environ.get("CLAUDE_MEMORY_WORKSPACE", "")
    if ws:
        cfg.workspace_id = ws

    md = os.environ.get("CLAUDE_MEMORY_DIR", "")
    if md:
        cfg.memory_root = md

    lv = os.environ.get("CLAUDE_MEMORY_LOG_LEVEL", "")
    if lv:
        cfg.log_level = lv.upper()

    ta = os.environ.get("CLAUDE_MEMORY_TRACK_ACCESS", "")
    if ta.lower() in ("true", "1", "yes"):
        cfg.track_access = True

    return cfg


def get_config(
    project_root: Path | None = None,
    workspace_id: str | None = None,
) -> MemoryConfig:
    """获取运行配置。

    优先级：参数 > 环境变量 > 默认值。
    """
    root = project_root or _resolve_project_root()
    cfg = MemoryConfig(project_root=root)
    if workspace_id is not None:
        cfg.workspace_id = workspace_id
    return _load_from_env(cfg)


def _resolve_project_root() -> Path:
    """尝试自动推断项目根目录。"""
    # 从当前文件位置推断
    return Path(__file__).resolve().parents[1]


def list_workspaces(memory_root: Path) -> list[str]:
    """列出所有已创建的 workspace。"""
    ws_dir = memory_root / "workspaces"
    if not ws_dir.exists():
        return []
    return sorted(
        d.name for d in ws_dir.iterdir()
        if d.is_dir() and (d / "index.json").exists()
    )
