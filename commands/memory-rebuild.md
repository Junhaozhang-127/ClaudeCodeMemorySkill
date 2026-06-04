---
name: memory:rebuild
description: 从 Markdown 文件重建 index.json 索引
---
# /memory rebuild

从 `memory/topics/` 目录下的 Markdown 文件重建 `index.json` 索引。

## 用法

```
/memory rebuild
```

## 实现

CLI 映射到 `scripts/update_index.py`，扫描所有记忆 Markdown 文件，重新提取关键词并构建倒排索引。适用于索引损坏、手动增删记忆文件后的修复。

## 示例

```
/memory rebuild
```
