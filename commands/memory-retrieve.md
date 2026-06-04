---
name: memory:retrieve
description: 检索相关历史记忆并注入上下文
---
# /memory retrieve <查询>

检索相关历史记忆并注入当前会话上下文。

## 用法

```
/memory retrieve <查询>
```

## 实现

CLI 映射到 `scripts/retrieve_memory.py`，对查询进行关键词提取和索引匹配，返回最相关的记忆（最多 5 条），按优先级注入上下文：摘要 → 关键决策 → 待办事项 → 原始内容。

## 示例

```
/memory retrieve 登录超时 Bug 修复
```
