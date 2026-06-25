"""
config.py — Memory Skill 配置管理

支持 workspace 级隔离、环境变量覆盖、config.json 持久化、新旧路径兼容。

优先级：CLI 参数 > 环境变量 > config.json > 默认值
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

_DEFAULT_MEMORY_ROOT = "memory"
_LEGACY_INDEX = Path("memory/index.json")
_LEGACY_TOPICS = Path("memory/topics")

# 配置文件名（位于项目根目录）
_CONFIG_FILE = "config.json"


@dataclass
class MemoryConfig:
    """Memory Skill 运行配置。"""

    project_root: Path = field(default_factory=lambda: Path.cwd())
    memory_root: str = _DEFAULT_MEMORY_ROOT
    workspace_id: str = ""
    top_k: int = 5
    max_chars_per_item: int = 1200
    log_level: str = "INFO"
    log_dir: str = "logs"
    log_file: str = "claude_memory.log"
    log_max_bytes: int = 1_048_576
    log_backup_count: int = 3
    index_backup_max: int = 10
    track_access: bool = False
    lock_timeout: float = 5.0
    auto_save_interval: int = 10
    # v0.6.0: embedding + LLM 配置
    embedding_provider: str = "auto"      # "auto" / "openai" / "fake"
    embedding_model: str = ""             # 空则使用 provider 默认值
    embedding_dimension: int = 1536       # fake 模式下可调
    llm_provider: str = "auto"            # "auto" / "openai" / "fake"
    llm_model: str = ""                   # 空则使用 provider 默认值
    llm_api_base: str = ""                # 空则使用 provider 默认值
    retrieval_mode: str = "hybrid"        # "keyword" / "semantic" / "hybrid"
    summary_mode: str = "rule"            # "rule" / "llm" / "auto"
    # v0.6.0: memory lifecycle
    default_ttl_days: int = 365           # 默认 TTL（天），0=永不过期
    short_term_ttl_days: int = 30         # 短期记忆 TTL
    auto_expire_enabled: bool = False     # 是否在 save 时自动检查过期

    @property
    def is_legacy_mode(self) -> bool:
        return not self.workspace_id or self.workspace_id in ("default",)

    @property
    def memory_dir(self) -> Path:
        """记忆根目录（可能是绝对路径或相对于 project_root）。"""
        p = Path(self.memory_root)
        if p.is_absolute():
            return p
        return self.project_root / p

    @property
    def index_path(self) -> Path:
        if self.is_legacy_mode:
            return self.memory_dir / "index.json"
        return self.memory_dir / "workspaces" / self.workspace_id / "index.json"

    @property
    def topics_dir(self) -> Path:
        if self.is_legacy_mode:
            return self.memory_dir / "topics"
        return self.memory_dir / "workspaces" / self.workspace_id / "topics"

    @property
    def backup_dir(self) -> Path:
        base = self.memory_dir if self.is_legacy_mode else (
            self.memory_dir / "workspaces" / self.workspace_id
        )
        return base / "backups"

    @property
    def archive_dir(self) -> Path:
        base = self.memory_dir if self.is_legacy_mode else (
            self.memory_dir / "workspaces" / self.workspace_id
        )
        return base / "archive"

    @property
    def lock_path(self) -> Path:
        return self.index_path.with_suffix(self.index_path.suffix + ".lock")

    @property
    def config_file_path(self) -> Path:
        return self.project_root / _CONFIG_FILE

    def ensure_dirs(self) -> None:
        self.topics_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_path.exists():
            self.index_path.write_text("{}", encoding="utf-8")


# ═══════════════════════════════════════════════════════════════
# config.json 读写
# ═══════════════════════════════════════════════════════════════

def load_config_file(project_root: Path) -> dict:
    """从 config.json 读取配置。"""
    path = project_root / _CONFIG_FILE
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def save_config_file(cfg: MemoryConfig) -> None:
    """将当前配置保存到 config.json。"""
    data = {
        "memory_dir": cfg.memory_root,
        "workspace": cfg.workspace_id,
        "log_level": cfg.log_level,
        "track_access": cfg.track_access,
        "max_context_chars": cfg.max_chars_per_item,
        "top_k": cfg.top_k,
        "retriever": "hybrid",
        "enable_embedding": False,
    }
    path = cfg.config_file_path
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_first_run(project_root: Path | None = None) -> bool:
    """检测是否为首次运行（无 config.json 且无环境变量配置）。"""
    root = project_root or _resolve_project_root()
    has_config_file = (root / _CONFIG_FILE).exists()
    has_env_dir = bool(os.environ.get("CLAUDE_MEMORY_DIR", ""))
    has_env_ws = bool(os.environ.get("CLAUDE_MEMORY_WORKSPACE", ""))
    return not has_config_file and not has_env_dir and not has_env_ws


# ═══════════════════════════════════════════════════════════════
# 配置加载（优先级链）
# ═══════════════════════════════════════════════════════════════

def _apply_config_file(cfg: MemoryConfig, data: dict) -> MemoryConfig:
    """将 config.json 数据应用到配置（最低优先级）。"""
    if "memory_dir" in data and data["memory_dir"]:
        cfg.memory_root = data["memory_dir"]
    if "workspace" in data and data["workspace"]:
        cfg.workspace_id = data["workspace"]
    if "log_level" in data:
        cfg.log_level = data["log_level"].upper()
    if "track_access" in data:
        cfg.track_access = bool(data["track_access"])
    if "max_context_chars" in data:
        cfg.max_chars_per_item = int(data["max_context_chars"])
    if "top_k" in data:
        cfg.top_k = int(data["top_k"])
    return cfg


def _apply_env_vars(cfg: MemoryConfig) -> MemoryConfig:
    """从环境变量覆盖配置（中等优先级）。"""
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

    优先级：CLI 参数 > 环境变量 > config.json > 默认值
    """
    root = project_root or _resolve_project_root()
    cfg = MemoryConfig(project_root=root)

    # 1. config.json（最低）
    file_data = load_config_file(root)
    if file_data:
        cfg = _apply_config_file(cfg, file_data)

    # 2. 环境变量（覆盖 config.json）
    cfg = _apply_env_vars(cfg)

    # 3. CLI 参数（最高优先级）
    if workspace_id is not None:
        cfg.workspace_id = workspace_id

    return cfg


def _resolve_project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def list_workspaces(memory_root: Path) -> list[str]:
    ws_dir = memory_root / "workspaces"
    if not ws_dir.exists():
        return []
    return sorted(
        d.name for d in ws_dir.iterdir()
        if d.is_dir() and (d / "index.json").exists()
    )
