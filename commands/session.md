---
name: memory:session
description: 会话空间管理 — 创建、切换、重命名、归档、删除、恢复、查看会话
---
# /memory session <action>

管理项目会话空间。每个会话拥有独立的记忆、摘要、向量索引和事件日志目录。

## 用法

```
/memory session list    [--include-archived] [--include-deleted]
/memory session create  --title "标题" [--description "描述"] [--tags tag1,tag2] [--use]
/memory session current
/memory session use     --session-id <id> [--allow-archived]
/memory session rename  --session-id <id> --title "新标题"
/memory session archive --session-id <id>
/memory session delete  --session-id <id>
/memory session restore --session-id <id> [--use]
/memory session info    [--session-id <id>]
/memory session link    [--from <source_id>] --to <target_id> [--reason "..."] [--allow-archived]
/memory session unlink  [--from <source_id>] --to <target_id>
/memory session links   [--session-id <id>] [--include-archived]
```

## 实现

Python handler 位于 `commands/memory_session.py`，通过 `CommandRegistry` 分发。
底层 `SessionManager` 位于 `scripts/session_manager.py`。

## 示例

```
/memory session create --title "论文审稿智能体" --description "BOOK Agent review work" --use
/memory session list
/memory session current
/memory session delete --session-id abc123
/memory session restore --session-id abc123 --use
```

## 注意

- delete 是软删除，目录保留，可通过 restore 恢复
- default session 不可 archive/delete
- 仅在 Phase 2 中提供命令层，memory_core 存入时暂不自动写入当前 session（Phase 3 实现）
