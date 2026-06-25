# Session Workspace Manager (v0.7.0)

## 1. 会话空间是什么

会话空间是 v0.7.0 引入的新概念。每个用户会话拥有独立的目录，用于存放该会话相关的记忆、摘要、向量索引、链接关系和事件日志。

这使得用户可以：
- 为不同项目创建独立的会话工作区
- 在会话间切换而不丢失上下文
- 追踪每个会话的操作历史
- 后续阶段支持跨会话语义检索和链接

## 2. Phase 1 目录结构

```text
.memory/sessions/
  index.json              # SessionIndex — 全局会话索引
  current.json            # CurrentSession — 当前会话指针
  <session_id>/
    manifest.json          # SessionManifest — 会话元数据
    memories.jsonl         # 记忆记录 (Phase 3 接入)
    summaries.jsonl        # 摘要记录
    embeddings.jsonl       # 向量记录
    links.json             # 会话链接图
    events.jsonl           # 事件日志
    trash/                 # 软删除暂存
```

## 3. Phase 2 命令用法

```text
/memory session list    [--include-archived] [--include-deleted]
/memory session create  --title "标题" [--description "描述"] [--tags tag1,tag2] [--use]
/memory session current
/memory session use     --session-id <id> [--allow-archived]
/memory session rename  --session-id <id> --title "新标题"
/memory session archive --session-id <id>
/memory session delete  --session-id <id>
/memory session restore --session-id <id> [--use]
/memory session info    [--session-id <id>]
```

## 4. 常用示例

```bash
# 创建论文审稿工作区并立即切换
/memory session create --title "论文审稿智能体" --description "BOOK Agent review" --use

# 创建开发项目工作区
/memory session create --title "ClaudeMeory Dev" --tags "dev,plugin,memory"

# 列出所有活跃会话
/memory session list

# 切换回默认会话
/memory session use --session-id default

# 归档已完成项目的会话
/memory session archive --session-id abc123

# 恢复误删除的会话
/memory session restore --session-id abc123 --use

# 查看会话详细信息
/memory session info --session-id abc123
```

## 5. 软删除说明

- `delete` 不执行物理删除，目录和文件完整保留
- `manifest.status` 改为 `deleted`
- 默认 `list` 不显示已删除会话
- `include_deleted=True` 可查看
- `restore` 可恢复为 `active`
- 删除当前会话后自动回退到 `default`

## 6. Default Session 说明

- `session_id = "default"`，`title = "Default Session"`
- 首次初始化时自动创建
- 不可永久删除或归档
- 当前会话被删除/缺失时自动回退

## 7. Current Session 说明

- `current.json` 存储当前会话指针
- `set_current_session()` 切换并记录事件
- 不能切换到已删除的会话
- 可通过 `--allow-archived` 切换到归档会话
- 持久化到磁盘，跨进程可用

## 8. Phase 3: memory_core session-aware 接入 ✅

### save_memory session 行为

```python
# 默认写入当前会话
save_memory("topic", "content")

# 指定目标会话
save_memory("topic", "content", session_id="abc123")

# 写入归档会话（需显式允许）
save_memory("topic", "content", session_id="abc123", allow_archived=True)
```

- 旧 memory 记录无 `session_id` 时自动归入 `default`
- 写入后同步更新 `SessionManifest.memory_count`
- 镜像写入 `.memory/sessions/<id>/memories.jsonl`

### retrieve_memory session 行为

```python
# 默认只检索当前会话
retrieve_memory("query")

# 检索指定会话
retrieve_memory("query", session_id="abc123")

# 检索所有活跃会话
retrieve_memory("query", all_sessions=True)

# 包含已归档会话
retrieve_memory("query", all_sessions=True, include_archived_sessions=True)
```

### Command 参数

```bash
/memory save "主题" --text "内容" [--session-id <id>]
/memory retrieve "查询" [--session-id <id>] [--all-sessions] [--include-archived-sessions]
```

### CLI 入口

```bash
python scripts/session_cli.py create --title "Paper Review" --use
python scripts/summarize_session.py --topic "记忆" --text "内容" --session-id <id>
python scripts/retrieve_memory.py --query "查询" --session-id <id>
python scripts/retrieve_memory.py --query "查询" --all-sessions
```

## 9. Phase 4 计划: Linked Session 检索

- 支持手动和自动链接近似语义会话
- `links.json` 记录会话之间的引用关系
- `retrieve_memory()` 支持 `include_linked` 跨会话检索

## 10. Phase 5 计划: TUI 交互

- 终端内交互式会话选择
- 上下键导航，Enter 确认
- Delete 键软删除
- 实时预览会话内容
