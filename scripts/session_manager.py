"""
session_manager.py — Session Workspace Manager (v0.7.0 Phase 1)

提供会话空间管理核心能力:
  - SessionStatus: 会话状态枚举
  - SessionManifest: 会话元数据
  - SessionIndex: 会话索引 (index.json)
  - CurrentSession: 当前会话 (current.json)
  - SessionManager: 统一管理器

目录结构:
  .memory/sessions/
    index.json          # 全局会话索引
    current.json        # 当前会话指针
    <session_id>/
      manifest.json     # 会话元数据
      memories.jsonl    # 记忆记录 (Phase 3 接入)
      summaries.jsonl   # 摘要记录
      embeddings.jsonl  # 向量记录
      links.json        # 会话链接图
      events.jsonl      # 事件日志
      trash/            # 软删除暂存
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

# ═══════════════════════════════════════════════════════════════
# 路径解析
# ═══════════════════════════════════════════════════════════════

_PROGRAM_ROOT = Path(__file__).resolve().parents[3]  # scripts → ClaudeMeory → Skill → program/
_DEFAULT_SESSION_ROOT = _PROGRAM_ROOT / "Meory" / "memory" / "sessions"


def _resolve_session_root(custom_root: str | Path | None = None) -> Path:
    """解析会话根目录路径。"""
    if custom_root:
        p = Path(custom_root)
        if p.is_absolute():
            return p
        return _PROGRAM_ROOT / p
    try:
        from config import get_config
        cfg = get_config()
        if cfg.session_root:
            r = Path(cfg.session_root)
            return r if r.is_absolute() else _PROGRAM_ROOT / r
    except ImportError:
        pass
    return _DEFAULT_SESSION_ROOT


# ═══════════════════════════════════════════════════════════════
# SessionStatus
# ═══════════════════════════════════════════════════════════════

class SessionStatus:
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

    ALL = (ACTIVE, ARCHIVED, DELETED)
    VISIBLE_DEFAULT = (ACTIVE,)

    @classmethod
    def is_valid(cls, status: str) -> bool:
        return status in cls.ALL


# ═══════════════════════════════════════════════════════════════
# SessionManifest
# ═══════════════════════════════════════════════════════════════

@dataclass
class SessionManifest:
    session_id: str
    title: str
    description: str = ""
    tags: list[str] = field(default_factory=list)
    status: str = SessionStatus.ACTIVE
    created_at: str = ""
    updated_at: str = ""
    last_accessed_at: str = ""
    memory_count: int = 0
    summary_count: int = 0
    linked_session_ids: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SessionManifest:
        defaults = {
            "description": "",
            "tags": [],
            "status": SessionStatus.ACTIVE,
            "created_at": "",
            "updated_at": "",
            "last_accessed_at": "",
            "memory_count": 0,
            "summary_count": 0,
            "linked_session_ids": [],
            "metadata": {},
        }
        for k, v in defaults.items():
            data.setdefault(k, v)
        return cls(
            session_id=data["session_id"],
            title=data["title"],
            description=data["description"],
            tags=data["tags"],
            status=data["status"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            last_accessed_at=data["last_accessed_at"],
            memory_count=data["memory_count"],
            summary_count=data["summary_count"],
            linked_session_ids=data["linked_session_ids"],
            metadata=data["metadata"],
        )


# ═══════════════════════════════════════════════════════════════
# SessionIndex
# ═══════════════════════════════════════════════════════════════

@dataclass
class SessionIndex:
    """会话索引 (.memory/sessions/index.json)。"""
    version: str = "0.7.0"
    sessions: list[SessionManifest] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "sessions": [s.to_dict() for s in self.sessions],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> SessionIndex:
        sessions = []
        for s in data.get("sessions", []):
            try:
                sessions.append(SessionManifest.from_dict(s))
            except (KeyError, TypeError):
                # 跳过损坏的 session 条目
                continue
        return cls(
            version=data.get("version", "0.7.0"),
            sessions=sessions,
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )


# ═══════════════════════════════════════════════════════════════
# CurrentSession
# ═══════════════════════════════════════════════════════════════

@dataclass
class CurrentSession:
    current_session_id: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> CurrentSession:
        return cls(
            current_session_id=data.get("current_session_id", ""),
            updated_at=data.get("updated_at", ""),
        )


# ═══════════════════════════════════════════════════════════════
# SessionEvent
# ═══════════════════════════════════════════════════════════════

@dataclass
class SessionEvent:
    event_id: str
    event_type: str
    session_id: str
    timestamp: str
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════
# SessionManager
# ═══════════════════════════════════════════════════════════════

class SessionManager:
    """会话空间管理器。

    管理 .memory/sessions/ 目录下的所有会话，提供创建、列表、重命名、
    归档、软删除、恢复、当前会话切换等功能。
    """

    DEFAULT_SESSION_ID = "default"
    INDEX_FILE = "index.json"
    CURRENT_FILE = "current.json"
    MANIFEST_FILE = "manifest.json"
    EVENTS_FILE = "events.jsonl"

    def __init__(self, session_root: str | Path | None = None):
        self._root = _resolve_session_root(session_root)
        self._ensure_initialized()

    # ── 路径 ─────────────────────────────────────────────────

    @property
    def root(self) -> Path:
        return self._root

    def _index_path(self) -> Path:
        return self._root / self.INDEX_FILE

    def _current_path(self) -> Path:
        return self._root / self.CURRENT_FILE

    def get_session_path(self, session_id: str) -> Path:
        return self._root / session_id

    # ── 初始化 ───────────────────────────────────────────────

    def _ensure_initialized(self) -> None:
        """确保 sessions/ 目录和索引存在，自动创建 default session。"""
        self._root.mkdir(parents=True, exist_ok=True)
        try:
            self._load_index()
        except FileNotFoundError:
            self._init_index()
        except json.JSONDecodeError:
            # 损坏的 index.json → 备份并从目录重建
            self._backup_corrupt(self._index_path())
            self._init_index()

        # 确保 default session 存在
        self.ensure_default_session()

    def _init_index(self) -> SessionIndex:
        now = _now()
        idx = SessionIndex(created_at=now, updated_at=now)
        self._save_index(idx)
        return idx

    def _backup_corrupt(self, path: Path) -> None:
        if not path.exists():
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        corrupt_path = path.with_name(f"{path.stem}.corrupt.{ts}.json")
        try:
            shutil.copy2(str(path), str(corrupt_path))
        except OSError:
            pass

    # ── 索引 I/O ─────────────────────────────────────────────

    def _load_index(self) -> SessionIndex:
        path = self._index_path()
        if not path.exists():
            raise FileNotFoundError(path)
        raw = path.read_text(encoding="utf-8")
        if not raw.strip():
            return self._init_index()
        data = json.loads(raw)
        return SessionIndex.from_dict(data)

    def _save_index(self, idx: SessionIndex) -> None:
        idx.updated_at = _now()
        path = self._index_path()
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(
                json.dumps(idx.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, path)
        except Exception:
            if tmp.exists():
                try:
                    tmp.unlink()
                except FileNotFoundError:
                    pass
            raise

    # ── 当前会话 ─────────────────────────────────────────────

    def _load_current(self) -> CurrentSession:
        path = self._current_path()
        if not path.exists():
            return CurrentSession()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return CurrentSession.from_dict(data)
        except (json.JSONDecodeError, FileNotFoundError):
            return CurrentSession()

    def _save_current(self, curr: CurrentSession) -> None:
        curr.updated_at = _now()
        path = self._current_path()
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(
                json.dumps(curr.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, path)
        except Exception:
            if tmp.exists():
                try:
                    tmp.unlink()
                except FileNotFoundError:
                    pass
            raise

    def set_current_session(self, session_id: str) -> SessionManifest:
        manifest = self.get_session(session_id)
        if manifest is None:
            raise ValueError(f"会话不存在: {session_id}")
        if manifest.status == SessionStatus.DELETED:
            raise ValueError(f"不能切换到已删除的会话: {session_id}")
        curr = CurrentSession(current_session_id=session_id)
        self._save_current(curr)
        self._log_event(session_id, "set_current",
                        {"previous": self._load_current().current_session_id})
        # 更新 last_accessed_at
        manifest.last_accessed_at = _now()
        self._update_manifest_in_index(manifest)
        return manifest

    def get_current_session(self) -> SessionManifest:
        curr = self._load_current()
        if curr.current_session_id:
            manifest = self.get_session(curr.current_session_id)
            if manifest and manifest.status != SessionStatus.DELETED:
                return manifest
        # 回退到 default
        return self.ensure_default_session()

    # ── 会话 CRUD ────────────────────────────────────────────

    def create_session(
        self, title: str, description: str = "", tags: list[str] | None = None,
    ) -> SessionManifest:
        session_id = _generate_session_id()
        now = _now()
        manifest = SessionManifest(
            session_id=session_id,
            title=title,
            description=description or "",
            tags=tags or [],
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            last_accessed_at=now,
        )
        # 创建会话目录和文件
        self._create_session_files(manifest)
        # 更新索引
        idx = self._load_index()
        idx.sessions.append(manifest)
        self._save_index(idx)
        # 记事件
        self._log_event(session_id, "create", {"title": title, "description": description})
        return manifest

    def list_sessions(
        self, include_archived: bool = False, include_deleted: bool = False,
    ) -> list[SessionManifest]:
        idx = self._load_index()
        allowed = set(SessionStatus.VISIBLE_DEFAULT)
        if include_archived:
            allowed.add(SessionStatus.ARCHIVED)
        if include_deleted:
            allowed.add(SessionStatus.DELETED)
        return [s for s in idx.sessions if s.status in allowed]

    def get_session(self, session_id: str) -> SessionManifest | None:
        idx = self._load_index()
        for s in idx.sessions:
            if s.session_id == session_id:
                return s
        return None

    def rename_session(self, session_id: str, title: str) -> SessionManifest:
        manifest = self._require_active(session_id)
        old = manifest.title
        manifest.title = title
        manifest.updated_at = _now()
        self._save_manifest(manifest)
        self._update_manifest_in_index(manifest)
        self._log_event(session_id, "rename", {"old_title": old, "new_title": title})
        return manifest

    def archive_session(self, session_id: str) -> SessionManifest:
        manifest = self._require_active(session_id)
        if session_id == self.DEFAULT_SESSION_ID:
            raise ValueError("不能归档 default session")
        manifest.status = SessionStatus.ARCHIVED
        manifest.updated_at = _now()
        self._save_manifest(manifest)
        self._update_manifest_in_index(manifest)
        self._log_event(session_id, "archive", {})
        return manifest

    def delete_session(self, session_id: str) -> SessionManifest:
        manifest = self._require_not_deleted(session_id)
        if session_id == self.DEFAULT_SESSION_ID:
            raise ValueError("不能删除 default session")
        manifest.status = SessionStatus.DELETED
        manifest.updated_at = _now()
        self._save_manifest(manifest)
        self._update_manifest_in_index(manifest)
        self._log_event(session_id, "delete", {})
        # 如果删除的是当前会话，回退到 default
        curr = self._load_current()
        if curr.current_session_id == session_id:
            default = self.ensure_default_session()
            self.set_current_session(default.session_id)
        return manifest

    def restore_session(self, session_id: str) -> SessionManifest:
        manifest = self.get_session(session_id)
        if manifest is None:
            raise ValueError(f"会话不存在: {session_id}")
        if manifest.status != SessionStatus.DELETED:
            raise ValueError(f"只能恢复已删除的会话，当前状态: {manifest.status}")
        manifest.status = SessionStatus.ACTIVE
        manifest.updated_at = _now()
        self._save_manifest(manifest)
        self._update_manifest_in_index(manifest)
        self._log_event(session_id, "restore", {})
        return manifest

    def ensure_default_session(self) -> SessionManifest:
        existing = self.get_session(self.DEFAULT_SESSION_ID)
        if existing:
            if existing.status == SessionStatus.DELETED:
                # default session 被软删除 — 强制恢复
                existing.status = SessionStatus.ACTIVE
                existing.updated_at = _now()
                self._save_manifest(existing)
                self._update_manifest_in_index(existing)
                self._log_event(self.DEFAULT_SESSION_ID, "restore",
                                {"reason": "default session forcibly restored"})
            return existing
        # 创建 default session
        now = _now()
        manifest = SessionManifest(
            session_id=self.DEFAULT_SESSION_ID,
            title="Default Session",
            description="Auto-generated default session workspace",
            status=SessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            last_accessed_at=now,
        )
        self._create_session_files(manifest)
        idx = self._load_index()
        idx.sessions.append(manifest)
        self._save_index(idx)
        self._log_event(self.DEFAULT_SESSION_ID, "create",
                        {"title": "Default Session", "reason": "auto-created default"})
        return manifest

    # ── 内部方法 ─────────────────────────────────────────────

    def _require_active(self, session_id: str) -> SessionManifest:
        manifest = self.get_session(session_id)
        if manifest is None:
            raise ValueError(f"会话不存在: {session_id}")
        if manifest.status != SessionStatus.ACTIVE:
            raise ValueError(f"会话未激活: {session_id} ({manifest.status})")
        return manifest

    def _require_not_deleted(self, session_id: str) -> SessionManifest:
        manifest = self.get_session(session_id)
        if manifest is None:
            raise ValueError(f"会话不存在: {session_id}")
        if manifest.status == SessionStatus.DELETED:
            raise ValueError(f"会话已删除: {session_id}")
        return manifest

    # ── 会话链接 ─────────────────────────────────────────────

    LINK_FILE = "links.json"

    def _load_links(self, session_id: str) -> dict:
        path = self.get_session_path(session_id) / self.LINK_FILE
        if not path.exists():
            return {"version": "0.7.0", "linked_sessions": [],
                    "updated_at": _now()}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {"version": "0.7.0", "linked_sessions": [],
                        "updated_at": _now()}
            # 兼容旧格式：linked_sessions 是字符串列表或混合
            if data.get("linked_sessions"):
                normalized = []
                for entry in data["linked_sessions"]:
                    if isinstance(entry, str):
                        normalized.append({
                            "session_id": entry,
                            "linked_at": data.get("updated_at", _now()),
                            "link_type": "manual",
                            "reason": "legacy",
                        })
                    elif isinstance(entry, dict):
                        normalized.append(entry)
                data["linked_sessions"] = normalized
            return data
        except (json.JSONDecodeError, OSError):
            return {"version": "0.7.0", "linked_sessions": [],
                    "updated_at": _now()}

    def _save_links(self, session_id: str, data: dict) -> None:
        data["updated_at"] = _now()
        path = self.get_session_path(session_id) / self.LINK_FILE
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, path)
        except Exception:
            if tmp.exists():
                try:
                    tmp.unlink()
                except FileNotFoundError:
                    pass
            raise

    def link_session(
        self,
        source_session_id: str,
        target_session_id: str,
        reason: str = "",
        allow_archived: bool = False,
    ) -> dict:
        source = self._require_not_deleted(source_session_id)
        target = self.get_session(target_session_id)
        if target is None:
            raise ValueError(f"目标会话不存在: {target_session_id}")
        if target.session_id == source.session_id:
            raise ValueError("不能链接自己")
        if target.status == SessionStatus.DELETED:
            raise ValueError(f"不能链接已删除的会话: {target_session_id}")
        if target.status == SessionStatus.ARCHIVED and not allow_archived:
            raise ValueError(f"不能链接已归档会话: {target_session_id}。"
                            "使用 allow_archived=True 允许。")

        links = self._load_links(source_session_id)
        existing_ids = {l.get("session_id", "") for l in links["linked_sessions"]}
        if target_session_id in existing_ids:
            return {"ok": True, "already_linked": True,
                    "source": source_session_id, "target": target_session_id,
                    "message": f"会话已链接: {target_session_id}"}

        links["linked_sessions"].append({
            "session_id": target_session_id,
            "title": target.title,
            "linked_at": _now(),
            "link_type": "manual",
            "reason": reason or "user requested",
        })
        self._save_links(source_session_id, links)

        # 同步 manifest
        if target_session_id not in source.linked_session_ids:
            source.linked_session_ids.append(target_session_id)
            source.updated_at = _now()
            self._save_manifest(source)
            self._update_manifest_in_index(source)

        self._log_event(source_session_id, "session_linked", {
            "target_session_id": target_session_id,
            "target_title": target.title,
            "reason": reason,
        })
        return {"ok": True, "already_linked": False,
                "source": source_session_id, "target": target_session_id,
                "target_title": target.title}

    def unlink_session(
        self, source_session_id: str, target_session_id: str,
    ) -> dict:
        source = self._require_not_deleted(source_session_id)

        links = self._load_links(source_session_id)
        before = len(links["linked_sessions"])
        links["linked_sessions"] = [
            l for l in links["linked_sessions"]
            if l.get("session_id") != target_session_id
        ]
        after = len(links["linked_sessions"])

        if before == after:
            return {"ok": True, "already_unlinked": True,
                    "source": source_session_id, "target": target_session_id,
                    "message": f"链接不存在: {target_session_id}"}

        self._save_links(source_session_id, links)

        # 同步 manifest
        if target_session_id in source.linked_session_ids:
            source.linked_session_ids.remove(target_session_id)
            source.updated_at = _now()
            self._save_manifest(source)
            self._update_manifest_in_index(source)

        self._log_event(source_session_id, "session_unlinked", {
            "target_session_id": target_session_id,
        })
        return {"ok": True, "already_unlinked": False,
                "source": source_session_id, "target": target_session_id}

    def get_linked_session_ids(
        self, session_id: str,
        include_archived: bool = False,
        include_deleted: bool = False,
    ) -> list[str]:
        links = self._load_links(session_id)
        ids = []
        for entry in links["linked_sessions"]:
            sid = entry.get("session_id", "")
            if not sid:
                continue
            manifest = self.get_session(sid)
            if manifest is None:
                continue
            if manifest.status == SessionStatus.DELETED and not include_deleted:
                continue
            if manifest.status == SessionStatus.ARCHIVED and not include_archived:
                continue
            ids.append(sid)
        return ids

    def list_linked_sessions(
        self, session_id: str,
        include_archived: bool = False,
        include_deleted: bool = False,
    ) -> list[SessionManifest]:
        ids = self.get_linked_session_ids(
            session_id,
            include_archived=include_archived,
            include_deleted=include_deleted,
        )
        manifests = []
        for sid in ids:
            m = self.get_session(sid)
            if m:
                manifests.append(m)
        return manifests

    def _create_session_files(self, manifest: SessionManifest) -> None:
        session_dir = self.get_session_path(manifest.session_id)
        session_dir.mkdir(parents=True, exist_ok=True)
        trash_dir = session_dir / "trash"
        trash_dir.mkdir(parents=True, exist_ok=True)

        # manifest.json
        (session_dir / self.MANIFEST_FILE).write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # memories.jsonl
        (session_dir / "memories.jsonl").write_text("", encoding="utf-8")
        # summaries.jsonl
        (session_dir / "summaries.jsonl").write_text("", encoding="utf-8")
        # embeddings.jsonl
        (session_dir / "embeddings.jsonl").write_text("", encoding="utf-8")
        # links.json
        links = {
            "version": "0.7.0",
            "linked_sessions": [],
            "updated_at": manifest.created_at,
        }
        (session_dir / "links.json").write_text(
            json.dumps(links, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # events.jsonl
        (session_dir / self.EVENTS_FILE).write_text("", encoding="utf-8")

    def _save_manifest(self, manifest: SessionManifest) -> None:
        path = self.get_session_path(manifest.session_id) / self.MANIFEST_FILE
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(
                json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(tmp, path)
        except Exception:
            if tmp.exists():
                try:
                    tmp.unlink()
                except FileNotFoundError:
                    pass
            raise

    def _update_manifest_in_index(self, manifest: SessionManifest) -> None:
        idx = self._load_index()
        for i, s in enumerate(idx.sessions):
            if s.session_id == manifest.session_id:
                idx.sessions[i] = manifest
                break
        self._save_index(idx)

    def _log_event(
        self, session_id: str, event_type: str, details: dict,
    ) -> None:
        event = SessionEvent(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            session_id=session_id,
            timestamp=_now(),
            details=details,
        )
        path = self.get_session_path(session_id) / self.EVENTS_FILE
        try:
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except (OSError, FileNotFoundError):
            pass


# ═══════════════════════════════════════════════════════════════
# 辅助函数
# ═══════════════════════════════════════════════════════════════

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _generate_session_id() -> str:
    return hashlib.sha256(
        (str(uuid.uuid4()) + str(datetime.now().timestamp())).encode("utf-8")
    ).hexdigest()[:12]


# ═══════════════════════════════════════════════════════════════
# 便捷工厂
# ═══════════════════════════════════════════════════════════════

_global_manager: SessionManager | None = None


def get_session_manager(
    session_root: str | Path | None = None,
) -> SessionManager:
    """获取全局 SessionManager 实例（懒加载）。"""
    global _global_manager
    if _global_manager is None or session_root is not None:
        _global_manager = SessionManager(session_root=session_root)
    return _global_manager
