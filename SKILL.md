# Claude Code Memory Skill

> **Phase 3**: Hook 正式接入 · Slash Command · Plugin 打包

## Skill 目标

当用户在 Claude Code 中进行多轮项目开发、Bug 修复、需求分析或测试复盘时，本 Skill 负责将对话沉淀为可检索的结构化 Markdown 记忆库，并在新会话中根据用户输入自动检索并注入相关历史上下文。

**Phase 3 新增**：Hook 自动化触发、Slash Command 手动调用、Plugin 一键安装。

## 适用场景

当用户出现以下意图时，应优先使用本 Skill：

- 继续之前的项目讨论
- 查找历史 Bug 修复记录
- 复用之前的提示词、方案或任务清单
- 追踪某个项目的需求变化
- 在新会话中恢复之前 Claude Code 的工作上下文

## Slash Commands

本 Skill 提供以下对话内命令（以 `/` 开头）：

### `/memory save <主题>`

保存当前对话为结构化 Markdown 记忆。

```bash
python scripts/summarize_session.py --topic "<主题>" --text "<对话内容>"
```

### `/memory retrieve <查询>`

检索与查询相关的历史记忆，注入当前上下文。

```bash
python scripts/retrieve_memory.py --query "<查询>" --top-k 5
```

### `/memory rebuild`

从已有 Markdown 文件重建 `memory/index.json` 索引。

```bash
python scripts/update_index.py
```

### 使用示例

```
/memory save Claude Code 记忆系统架构
/memory retrieve 登录超时 Bug 修复
/memory rebuild
```

## 何时写入记忆

在以下时机自动或手动触发：

- **自动**：Hook 事件 `Stop` 触发 → 调用 `post_conversation.sh`
- **手动**：用户使用 `/memory save <主题>` 命令
- **手动**：用户明确说"记住这个"或"保存这条记忆"
- **阶段完成**：方案确定、Bug 修复完成、需求确认后

## 何时检索记忆

在以下时机自动或手动触发：

- **自动**：Hook 事件 `PrePrompt` 触发 → 调用 `pre_prompt.sh`
- **手动**：用户使用 `/memory retrieve <查询>` 命令
- **手动**：用户在新会话中提到"之前讨论过"、"上次的"

## 写入记忆格式

每条记忆包含结构化字段：

```markdown
# 主题名称

> 更新时间：YYYY-MM-DD HH:MM:SS

## 摘要
结构化摘要（规则抽取，不超过 500 字）

## 关键词
关键词1, 关键词2, 关键词3

## 关键决策
- 决策1
- 决策2
（无决策时显示"无明确关键决策。"）

## 待办事项
- 待办1
- 待办2
（无待办时显示"无明确待办事项。"）

## 原始对话摘录
对话原文（低优先级补充）
```

## 检索注入规则

将检索结果注入 Claude Code 上下文时，遵循**严格优先级**：

1. **首先注入摘要**
2. **其次注入关键决策**（最多 3 条）
3. **然后注入待办事项**（最多 3 条）
4. **最后补充原始内容**（空间充裕时）

## 输出限制

- **不要**把全部历史原文无脑注入上下文
- **不要**在无匹配时强行编造历史记忆
- **优先注入**：摘要 → 关键决策 → 待办事项 → 原始内容
- 最多选择最相关的 5 条记忆
- 每条记忆最大 1200 字符
- 如果记忆与当前问题冲突，说明"历史记录可能过期"

## 失败降级策略

| 异常情况 | 处理方式 |
|----------|----------|
| `index.json` 损坏 | `load_index()` 返回空字典，不崩溃 |
| 检索无匹配 | 返回"未检索到相关历史记忆。"，正常回答 |
| Markdown 文件被删除 | 跳过，用 `update_index.py` 重建 |
| jieba 未安装 | 自动回退到正则规则法 |
| Python 脚本失败 | 不阻塞 Claude Code 正常响应，静默降级 |
| Hook 未配置 | Skill 仍可通过 `/memory` 命令和 CLI 手动使用 |
| 决策/待办为空 | 显示占位文本，不虚构内容 |

## 安全注意事项

- 记忆文件仅存储在本地 `memory/` 目录，不会上传
- 敏感信息（API Key、密码等）不应写入记忆
- `index.json` 使用原子写入防止损坏
- 索引重建自动跳过 README.md、隐藏文件
- 摘要器为本地规则实现，不发送数据到外部 API

## 不应该做什么

- **不要**在每次对话微小时都触发写入，只在阶段性成果时保存
- **不要**把 `README.md` 当成记忆文件
- **不要**假设检索结果一定准确（关键词匹配 ≠ 语义搜索）
- **不要**用记忆完全替代用户输入
- **不要**在无法抽取时强行编造决策/待办
