# Claude Code 会话记忆 Skill MVP

一个轻量级 Claude Code 会话记忆系统原型，用于解决 **Claude Code 新会话无法自动加载历史上下文** 的问题。

## 解决的问题

Claude Code 默认每个会话相互独立。当开发者切换会话或重新启动后，之前讨论的项目背景、Bug 分析、设计方案等上下文全部丢失，需要手动复述。

本 Skill 通过在会话结束时自动将对话沉淀为结构化 Markdown 记忆文件，并在新会话开始时根据用户输入检索相关记忆注入上下文，形成**轻量级本地记忆库**。

## 核心能力

- **结构化摘要**：基于规则从对话中抽取摘要、关键决策、待办事项（可插拔架构，支持未来接入 LLM）
- **中文关键词增强**：优先使用 jieba 分词 + 停用词过滤；无 jieba 时自动回退到正则规则法
- **会话保存**：将对话内容整理为结构化 Markdown 记忆文件
- **主题归档**：按主题和日期归档到 `memory/topics/`
- **索引维护**：使用 `memory/index.json` 维护主题索引（含 decisions、todos 字段）
- **优化检索**：多字段加权评分（主题 > 关键词 > 决策/待办 > 摘要），含时间衰减
- **上下文注入**：优先输出摘要、关键决策、待办事项，原始对话作为低优先级补充
- **索引重建**：从 Markdown 文件恢复 `index.json`，兼容新旧 Markdown 格式
- **零数据库依赖**：纯文件存储，Markdown + JSON，人工可读、Git 友好、易于迁移
- **Hook 自动化**：会话结束自动保存、用户输入前自动检索（支持 bash/bat/ps1）
- **Slash Command**：`/memory save`、`/memory retrieve`、`/memory rebuild` 对话内命令
- **Plugin 打包**：`plugin.json` 清单，一键安装脚本 `install.sh`
- **Workspace 隔离**：按项目/workpace 隔离记忆目录，不同项目互不干扰
- **混合检索**：多信号加权 + score_breakdown 可解释评分
- **记忆维护**：去重、合并、压缩、归档（dry-run 安全模式）
- **安全增强**：路径防遍历、Markdown fence 转义、索引备份 + 文件锁

## 项目结构

```text
ClaudeMeory/
├── README.md                         # 项目说明（本文件）
├── SKILL.md                          # Claude Code Skill 行为规则
├── requirements.txt                  # Python 依赖声明（核心仅标准库，jieba 可选）
├── .gitignore                        # Git 忽略规则
├── scripts/
│   ├── __init__.py                   # Package 标记
│   ├── memory_core.py                # 核心逻辑（保存、检索、索引、格式化）
│   ├── summarizers.py                # 可插拔摘要器模块
│   ├── summarize_session.py          # 保存记忆 CLI 入口
│   ├── retrieve_memory.py            # 检索记忆 CLI 入口
│   └── update_index.py               # 重建索引 CLI 入口
├── hooks/
│   ├── post_conversation.sh           # 会话后写入 Hook (bash)
│   ├── pre_prompt.sh                  # 用户输入前检索 Hook (bash)
│   ├── post_conversation.bat          # Windows CMD 版本
│   ├── pre_prompt.bat                 # Windows CMD 版本
│   ├── post_conversation.ps1          # PowerShell 版本
│   ├── pre_prompt.ps1                 # PowerShell 版本
│   ├── post_conversation_example.sh   # 旧版示例（保留兼容）
│   └── pre_prompt_example.sh          # 旧版示例（保留兼容）
├── memory/
│   ├── index.json                    # 主题索引
│   └── topics/                       # Markdown 记忆存储目录
│       └── README.md                 # 目录说明（不会被索引）
├── tests/
│   └── test_memory_skill.py          # 49 项测试（核心 + CLI）
└── docs/
    ├── PROJECT_STRUCTURE.md          # 项目结构说明文档
    ├── HOOK_SETUP.md                 # Hook 配置指南
    ├── DEVELOPMENT_ROADMAP.md        # 后续开发路线
    └── SUMMARIZER_DESIGN.md          # 摘要器架构设计文档
```

## 快速开始

### 环境要求

- Python 3.7+（核心仅使用标准库）

### 可选依赖

```bash
# 增强中文关键词抽取（不安装时自动回退到正则规则法）
pip install jieba
```

### 保存一条记忆

```bash
# 直接传入文本
python scripts/summarize_session.py \
  --topic "Claude Code 记忆机制" \
  --text "团队决定使用 jieba 做中文分词增强，确定采用可插拔摘要器架构。下一步需要补充单元测试。"

# 从文件读取
python scripts/summarize_session.py \
  --topic "Bug 修复：登录超时" \
  --file /path/to/conversation.txt
```

生成的 Markdown 文件包含：摘要、关键词、关键决策、待办事项、原始对话摘录。

### 检索相关记忆

```bash
# Markdown 格式输出（优先展示摘要、决策、待办）
python scripts/retrieve_memory.py \
  --query "Claude Code 怎么保存历史对话"

# JSON 格式输出（含 decisions、todos 字段）
python scripts/retrieve_memory.py \
  --query "登录问题" \
  --top-k 3 \
  --json
```

### 重建索引

手动编辑或批量导入 Markdown 文件后：

```bash
python scripts/update_index.py
```

### 运行测试

```bash
python tests/test_memory_skill.py
```

## Markdown 记忆文件格式

```markdown
# 主题名称

> 更新时间：2026-06-03 20:01:00

## 摘要
这里是结构化摘要。

## 关键词
关键词1, 关键词2, 关键词3

## 关键决策
- 决策1：采用 jieba 分词
- 决策2：使用可插拔摘要器架构

## 待办事项
- 补充单元测试
- 优化检索评分

## 原始对话摘录
```text
原始对话内容...
```
---
```

## index.json 格式

```json
{
  "topic_slug": {
    "topic": "原始主题名称",
    "file": "memory/topics/topic_slug_2026-06-03.md",
    "keywords": ["关键词1", "关键词2"],
    "summary": "摘要文本",
    "decisions": ["决策1", "决策2"],
    "todos": ["待办1", "待办2"],
    "created_at": "2026-06-03 20:01:00",
    "updated_at": "2026-06-03 20:01:00"
  }
}
```

## MVP 能力边界

### 已实现（Phase 1 + Phase 2）

- 基于规则的本地摘要器（摘要、关键决策、待办事项抽取）
- jieba 中文分词 + 停用词过滤（自动回退机制）
- 可插拔摘要器架构（`BaseSummarizer` 抽象基类）
- 多字段加权检索评分（主题/关键词/决策/待办/摘要 + 时间衰减）
- 结构化 Markdown 记忆保存
- `index.json` 主题索引（含 decisions/todos 字段）
- 原子写入索引保护
- 新旧 Markdown 格式兼容的索引重建
- 检索结果优先展示结构化信息（摘要→决策→待办→内容）
- Hook Shell 示例
- 49 项测试覆盖核心流程和 CLI

### 已知限制

| 限制 | 说明 | 计划解决阶段 |
|------|------|-------------|
| 摘要非语义 | 当前为规则法截取/触发词匹配，非 LLM 语义理解 | 第三/四阶段 |
| 检索非语义 | 关键词匹配，无向量相似度 | 第四阶段 |
| 记忆合并 | 同主题多次写入可能碎片化 | 第四阶段 |
| 项目隔离 | 所有记忆存在同一目录 | 第四阶段 |
| 并发写入 | 无文件锁保护 | 第四阶段 |
| Hook 接入 | 示例脚本需按实际 Claude Code Hook 规范适配 | 第三阶段 |
| 决策/待办抽取 | 依赖触发词表，可能漏检或误检 | 第三阶段（LLM 增强） |

## Plugin 安装

### 一键安装

```bash
git clone https://github.com/Junhaozhang-127/ClaudeMeory.git
cd ClaudeMeory
bash install.sh --with-jieba
```

### Hook 配置

将 `docs/settings.template.json` 中的 Hook 配置合并到 Claude Code 的 `settings.json`。

### Slash Commands

```
/memory save <主题>      — 保存当前对话记忆
/memory retrieve <查询>  — 检索相关历史记忆
/memory rebuild           — 重建记忆索引
```

## 后续计划

详见 `docs/DEVELOPMENT_ROADMAP.md`，四个阶段：

1. **第一阶段**（已完成 ✅）：工程化整理、文档完善、测试补全
2. **第二阶段**（已完成 ✅）：规则摘要器、中文关键词增强、决策/待办抽取、检索评分优化
3. **第三阶段**（已完成 ✅）：Claude Code Hook / Skill / Plugin 生态正式接入
4. **第四阶段**：向量检索、记忆合并、项目隔离、日志系统

## 常见问题 (FAQ)

### Q: 中文在终端显示乱码怎么办？

A: 终端编码问题，所有项目文件均为 UTF-8 编码。Windows PowerShell 执行 `chcp 65001` 切换 UTF-8 代码页，或使用 Git Bash / VS Code 终端。

### Q: index.json 损坏了怎么办？

A: 运行 `python scripts/update_index.py` 即可从 Markdown 文件重建索引。`load_index()` 在遇到损坏 JSON 时自动返回空字典而不会崩溃。

### Q: 为什么检索不到相关记忆？

A: 当前使用关键词加权匹配，非语义搜索。请尝试使用更精确的关键词，检查 `memory/index.json` 是否有对应条目，或运行 `python scripts/update_index.py` 确保索引最新。

### Q: jieba 是什么？必须安装吗？

A: jieba 是一个中文分词库，用于增强中文关键词抽取质量。**非必须安装**——没有 jieba 时系统自动回退到正则规则法，所有核心功能正常工作。

### Q: "关键决策"和"待办事项"有时候不准怎么办？

A: 当前使用关键词触发词表进行规则匹配，不是 LLM 语义理解。如果对话中没有明确的决策/待办触发词，这些字段会显示"无明确关键决策"或"无明确待办事项"。后续版本将支持 LLM 摘要器以提升准确性。

### Q: 如何自定义摘要器？

A: 实现 `summarizers.BaseSummarizer` 的 `summarize()` 方法，然后传入 `save_memory(summarizer=your_summarizer)`。详见 `docs/SUMMARIZER_DESIGN.md`。
