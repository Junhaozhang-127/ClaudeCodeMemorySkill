# Claude Code 会话记忆 Skill MVP

一个轻量级 Claude Code 会话记忆系统原型，用于解决 **Claude Code 新会话无法自动加载历史上下文** 的问题。

## 解决的问题

Claude Code 默认每个会话相互独立。当开发者切换会话或重新启动后，之前讨论的项目背景、Bug 分析、设计方案等上下文全部丢失，需要手动复述。

本 Skill 通过在会话结束时自动将对话沉淀为结构化 Markdown 记忆文件，并在新会话开始时根据用户输入检索相关记忆注入上下文，形成**轻量级本地记忆库**。

## 核心能力

- **会话保存**：将对话内容整理为结构化 Markdown 记忆文件（含摘要、关键词、关键决策、待办事项）
- **主题归档**：按主题和日期归档到 `memory/topics/`
- **索引维护**：使用 `memory/index.json` 维护主题索引
- **记忆检索**：新会话时根据用户输入匹配相关记忆
- **上下文注入**：输出可注入 Claude Code 的 Markdown 格式上下文片段
- **索引重建**：从已有 Markdown 文件恢复 `index.json`
- **零数据库依赖**：纯文件存储，Markdown + JSON，人工可读、Git 友好、易于迁移

## 项目结构

```text
ClaudeMeory/
├── README.md                         # 项目说明（本文件）
├── SKILL.md                          # Claude Code Skill 行为规则
├── requirements.txt                  # Python 依赖声明（MVP 仅标准库）
├── .gitignore                        # Git 忽略规则
├── scripts/
│   ├── __init__.py                   # Package 标记
│   ├── memory_core.py                # 核心逻辑（保存、检索、索引、格式化）
│   ├── summarize_session.py          # 保存记忆 CLI 入口
│   ├── retrieve_memory.py            # 检索记忆 CLI 入口
│   └── update_index.py               # 重建索引 CLI 入口
├── hooks/
│   ├── post_conversation_example.sh  # 会话后写入记忆 Hook 示例
│   └── pre_prompt_example.sh         # 用户输入前检索记忆 Hook 示例
├── memory/
│   ├── index.json                    # 主题索引
│   └── topics/                       # Markdown 记忆存储目录
│       └── README.md                 # 目录说明（不会被索引）
├── tests/
│   └── test_memory_skill.py          # 12 项核心流程测试
└── docs/
    ├── PROJECT_STRUCTURE.md          # 项目结构说明文档
    ├── HOOK_SETUP.md                 # Hook 配置指南
    └── DEVELOPMENT_ROADMAP.md        # 后续开发路线
```

## 快速开始

### 环境要求

- Python 3.7+（仅使用标准库，无需 pip install）

### 保存一条记忆

```bash
# 直接传入文本
python scripts/summarize_session.py \
  --topic "Claude Code 记忆机制" \
  --text "用户希望通过 Hook 自动总结对话，并保存为 Markdown 记忆库。"

# 从文件读取
python scripts/summarize_session.py \
  --topic "Bug 修复：登录超时" \
  --file /path/to/conversation.txt
```

### 检索相关记忆

```bash
# Markdown 格式输出（适合注入 Claude Code 上下文）
python scripts/retrieve_memory.py \
  --query "Claude Code 怎么保存历史对话"

# JSON 格式输出（适合程序消费）
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

## MVP 能力边界

### 已实现

- 结构化 Markdown 记忆保存（摘要、关键词、时间戳）
- `index.json` 主题索引读写（含原子写入保护）
- 基于关键词加权匹配的记忆检索
- 检索结果格式化为 Claude Code 可注入上下文
- 从 Markdown 文件重建索引（自动跳过 README.md 等说明文件）
- 会话后写入 / 用户输入前检索的 Hook Shell 示例
- 12 项测试覆盖核心流程和异常路径

### 已知限制

| 限制 | 说明 | 计划解决阶段 |
|------|------|-------------|
| 摘要质量 | 当前为截断式摘要，非语义总结 | 第二阶段 |
| 关键词抽取 | 规则法对中文支持粗糙 | 第二阶段 |
| 检索精度 | 纯关键词匹配，无语义理解 | 第二阶段 / 第四阶段 |
| 记忆合并 | 同主题多次写入可能碎片化 | 第四阶段 |
| 项目隔离 | 所有记忆存在同一目录 | 第四阶段 |
| 并发写入 | 无文件锁保护 | 第四阶段 |
| Hook 接入 | 示例脚本需按实际 Claude Code Hook 规范适配 | 第三阶段 |

## 后续计划

详见 `docs/DEVELOPMENT_ROADMAP.md`，四个阶段：

1. **第一阶段**（当前）：工程化整理、文档完善、测试补全
2. **第二阶段**：接入 LLM 增强摘要和关键词抽取质量
3. **第三阶段**：Claude Code Hook / Skill / Plugin 生态正式接入
4. **第四阶段**：向量检索、记忆合并、项目隔离、日志系统

## 常见问题 (FAQ)

### Q: 中文在终端显示乱码怎么办？

A: 这是终端编码问题，不是文件问题。所有项目文件均为 UTF-8 编码。
- **Windows PowerShell**：执行 `chcp 65001` 切换到 UTF-8 代码页，或在终端设置中启用 UTF-8。
- **Git Bash**：通常默认支持 UTF-8。
- **VS Code 终端**：在设置中确认 `terminal.integrated.defaultEncoding` 为 `utf-8`。

### Q: index.json 损坏了怎么办？

A: 运行 `python scripts/update_index.py` 即可从 `memory/topics/` 下的 Markdown 文件重建索引。`load_index()` 在遇到损坏 JSON 时会自动返回空字典而不会崩溃。

### Q: 为什么检索不到相关记忆？

A: 当前 MVP 使用简单关键词匹配，不是语义搜索。请尝试：
- 使用更精确的关键词
- 检查 `memory/index.json` 是否有对应的条目
- 运行 `python scripts/update_index.py` 确保索引最新
- 如果问题持续，这可能说明该记忆主题尚未被保存

### Q: Hook 示例和正式 Hook 配置有什么区别？

A: `hooks/` 目录下的脚本是**示例模板**，演示了调用逻辑。正式接入需要在 Claude Code 的 `settings.json` 中配置 Hook 事件、环境变量和输入格式。详细说明见 `docs/HOOK_SETUP.md`。

### Q: 记忆文件在哪里？可以手动编辑吗？

A: 在 `memory/topics/` 目录下。所有记忆都是标准 Markdown 文件，可以用任何编辑器打开、修改或删除。修改后建议运行 `python scripts/update_index.py` 更新索引。
