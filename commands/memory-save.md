---
name: memory:save
description: 保存当前对话为结构化 Markdown 记忆
---
# /memory save <主题>

保存当前对话为结构化 Markdown 记忆。

## 用法

```
/memory save <主题>
```

## 实现

CLI 映射到 `scripts/summarize_session.py`，将对话内容抽取为结构化摘要，包含关键决策和待办事项，写入 `memory/topics/` 目录并更新索引。

## 示例

```
/memory save Claude Code 记忆系统架构设计
```
