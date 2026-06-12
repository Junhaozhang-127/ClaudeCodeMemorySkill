# Claude Code 会话记忆 Skill MVP 项目结构说明

> 生成日期：2026-06-03  
> 项目路径：`D:\SmartManufacturingWorkshop\program\Skill\ClaudeMeory`  
> 项目定位：Claude Code 会话记忆 Skill MVP，本地 Markdown 记忆库原型

## 项目概述

本项目是一个轻量级 Claude Code 会话记忆 Skill MVP。它的目标是在 Claude Code 会话结束后，通过 Hook 或手动命令把对话内容沉淀为 Markdown 记忆文件，并维护 `memory/index.json` 主题索引；在新会话或用户新输入到来前，再根据输入内容检索相关记忆，输出可注入 Claude Code 上下文的 Markdown 片段。

当前版本强调可读、可迁移、低依赖和易验证：

- 记忆内容存储为 `memory/topics/*.md`，便于人工查看、编辑和迁移。
- 索引存储为 `memory/index.json`，记录主题、文件路径、关键词、摘要和时间。
- 核心逻辑集中在 `scripts/memory_core.py`，CLI 入口和 Hook 示例保持轻量。
- MVP 使用 Python 标准库和规则匹配，不依赖数据库、向量库或外部模型。

## 目录结构树

```text
ClaudeMeory/
|-- README.md                         # 项目说明、能力介绍、快速开始命令
|-- SKILL.md                          # Claude Code Skill 使用说明与行为规则
|-- requirements.txt                  # Python 依赖声明；当前 MVP 基本为标准库实现
|-- docs/
|   `-- PROJECT_STRUCTURE.md          # 本文档：项目结构与模块职责说明
|-- hooks/
|   |-- post_conversation_example.sh  # 会话结束后保存记忆的 Hook 示例
|   `-- pre_prompt_example.sh         # 用户输入前检索记忆的 Hook 示例
|-- memory/
|   |-- index.json                    # 主题索引文件，维护记忆元数据
|   `-- topics/
|       `-- README.md                 # Markdown 记忆目录说明与命名示例
|-- scripts/
|   |-- __init__.py                   # Python package 标记文件
|   |-- memory_core.py                # 核心逻辑：保存、检索、索引读写、索引重建
|   |-- retrieve_memory.py            # 检索记忆 CLI 入口
|   |-- summarize_session.py          # 保存会话记忆 CLI 入口
|   `-- update_index.py               # 重建索引 CLI 入口
`-- tests/
    `-- test_memory_skill.py          # MVP 核心流程测试
```

## 模块说明表

| 路径 | 类型 | 主要用途 | 当前评价 |
|---|---|---|---|
| `README.md` | 项目说明 | 介绍项目目标、核心能力、目录结构、快速命令和 MVP 设计 | 覆盖了基本使用路径，适合作为快速入口；当前中文内容在控制台读取时出现乱码，建议后续统一 UTF-8 编码和显示校验 |
| `SKILL.md` | Skill 文档 | 描述 Skill 目标、适用场景、写入规则、检索规则、Hook 建议和输出约束 | 结构接近 Claude Code Skill 说明文档，但可补充更明确的触发条件、输入输出格式、Hook 配置示例和失败处理策略 |
| `requirements.txt` | 依赖声明 | 声明运行依赖 | MVP 以标准库为主，保持轻量；如后续加入 pytest、jieba、向量库等，应在此维护 |
| `scripts/__init__.py` | 包标记 | 标识 `scripts/` 可作为 Python 包处理 | 简单合理 |
| `scripts/memory_core.py` | 核心模块 | 实现记忆目录初始化、主题 slug、摘要、关键词、索引读写、记忆保存、检索评分、上下文格式化、索引重建 | 职责集中但清晰，是 MVP 的核心能力层；后续可按摘要、检索、存储拆分子模块 |
| `scripts/summarize_session.py` | CLI 入口 | 接收 `--topic`、`--text` 或 `--file`，调用 `save_memory()` 保存记忆 | 职责单一，适合 Hook 调用 |
| `scripts/retrieve_memory.py` | CLI 入口 | 接收 `--query`、`--top-k`、`--json`，调用检索并输出上下文 | 职责单一，输出可供 Hook 注入或人工调试 |
| `scripts/update_index.py` | CLI 入口 | 调用 `rebuild_index()` 从已有 Markdown 重建 `index.json` | 职责单一，适合作为维护命令 |
| `hooks/post_conversation_example.sh` | Hook 示例 | 会话后接收主题和对话文件路径，调用保存入口 | 易理解，但仍是 example，需要按 Claude Code 实际 Hook 事件参数适配 |
| `hooks/pre_prompt_example.sh` | Hook 示例 | 用户输入前接收 query，调用检索入口 | 易接入，适合验证检索链路 |
| `memory/index.json` | 索引文件 | 维护主题到记忆文件的映射和元数据 | 当前为空 `{}`，保存记忆后会被写入；适合 MVP，但并发写入和索引损坏恢复需增强 |
| `memory/topics/` | 记忆目录 | 存储按主题归档的 Markdown 记忆文件 | 适合作为本地轻量记忆库；建议后续区分说明文件和真实记忆文件，避免重建索引时误扫说明文档 |
| `memory/topics/README.md` | 目录说明 | 说明 topics 目录用途和文件命名示例 | 有助于人工维护；需注意 `rebuild_index()` 当前扫描 `*.md`，可能把该 README 当成记忆文件 |
| `tests/test_memory_skill.py` | 测试 | 覆盖保存、检索、上下文格式化的 Happy Path | 能验证 MVP 主流程，但缺少异常、边界、索引重建、CLI 和 Hook 层测试 |

## 核心脚本函数说明

### `scripts/memory_core.py`

`memory_core.py` 是当前项目的能力核心，向 CLI 和 Hook 示例提供稳定函数接口。

| 函数/对象 | 作用 | 数据流说明 |
|---|---|---|
| `PROJECT_ROOT`、`MEMORY_DIR`、`TOPICS_DIR`、`INDEX_FILE` | 定义项目根目录、记忆目录、Markdown 目录和索引文件路径 | 所有读写操作都基于这些路径，避免从当前工作目录推断 |
| `MemoryRecord` | 单条记忆索引记录的数据结构 | 字段包括 `topic`、`file`、`keywords`、`summary`、`created_at`、`updated_at` |
| `ensure_memory_dirs()` | 确保 `memory/topics/` 和 `memory/index.json` 存在 | 写入、读取索引前都会间接依赖它 |
| `slugify_topic(topic)` | 将主题转换为安全文件名片段 | 替换非法路径字符、压缩空白、限制长度 |
| `extract_keywords(text, topic, max_keywords=10)` | 从主题和正文中提取关键词 | 当前使用规则法：主题切分、英文技术 token、中文片段提取、去重和截断 |
| `simple_summary(text, max_chars=300)` | 生成简易摘要 | 当前只是标准化空白并截取前 300 字符 |
| `load_index()` | 读取 `memory/index.json` | 文件不存在会初始化；JSON 损坏时返回空字典 |
| `save_index(index)` | 写入 `memory/index.json` | 使用 `ensure_ascii=False` 和缩进输出，便于人工阅读 |
| `save_memory(topic, conversation_text, append=True)` | 保存会话记忆并更新索引 | 生成摘要和关键词，组装 Markdown，写入 `memory/topics/`，再更新 `index.json` |
| `score_record(query, record)` | 计算 query 与索引记录的相关性分数 | 根据主题、摘要、关键词命中进行加权评分 |
| `retrieve_memory(query, top_k=5)` | 检索相关记忆 | 遍历索引、评分、读取命中的 Markdown 全文、按分数排序并返回 top-k |
| `format_context(results, max_chars_per_item=1200)` | 格式化检索结果 | 输出 Claude Code 可注入的 Markdown 上下文片段；无结果时输出提示 |
| `rebuild_index()` | 从 `memory/topics/*.md` 重建索引 | 读取 Markdown 标题、摘要、关键词和文件时间，覆盖写入 `index.json` |

### `scripts/summarize_session.py`

保存记忆入口。它只负责参数解析和内容来源选择：

- `--topic`：必填，作为记忆主题和文件名来源。
- `--text`：直接传入对话内容。
- `--file`：从文本文件读取对话内容。
- `--no-append`：同主题同日期文件存在时覆盖而不是追加。

核心调用关系：

```text
argparse 解析参数
-> 从 --text 或 --file 获取 conversation_text
-> memory_core.save_memory(topic, conversation_text, append=...)
-> 打印保存路径
```

### `scripts/retrieve_memory.py`

检索记忆入口。它只负责查询参数和输出格式：

- `--query`：必填，用户当前输入或检索问题。
- `--top-k`：最多返回多少条，默认 5。
- `--json`：输出原始 JSON 结果，便于程序消费。

核心调用关系：

```text
argparse 解析参数
-> memory_core.retrieve_memory(query, top_k)
-> JSON 输出或 memory_core.format_context(results)
```

### `scripts/update_index.py`

索引重建入口，无额外参数：

```text
memory_core.rebuild_index()
-> 打印重建后的主题数量
```

## 三个核心流程说明

### A. 记忆写入流程

```text
用户对话内容
  |
  v
Hook 触发
  |
  v
hooks/post_conversation_example.sh
  |
  | 传入: <主题> <conversation.txt>
  v
scripts/summarize_session.py
  |
  | 解析 --topic / --file 或 --text
  v
memory_core.save_memory()
  |
  |-- ensure_memory_dirs()
  |-- slugify_topic()
  |-- simple_summary()
  |-- extract_keywords()
  |-- 组装 Markdown 内容块
  |-- 写入或追加 memory/topics/<topic>_<date>.md
  |-- load_index()
  |-- 更新 MemoryRecord
  `-- save_index()
  |
  v
生成 Markdown 文件
  |
  v
更新 memory/index.json
```

### B. 记忆检索流程

```text
用户新输入
  |
  v
Hook 或手动触发
  |
  v
hooks/pre_prompt_example.sh
  |
  | 传入: "<用户当前输入>"
  v
scripts/retrieve_memory.py
  |
  | 解析 --query / --top-k / --json
  v
memory_core.retrieve_memory()
  |
  |-- load_index()
  |-- 遍历 index.json 中的记录
  |-- score_record() 逐条评分
  |-- 过滤 score <= 0 的记录
  |-- 读取匹配的 Markdown 文件内容
  |-- 按 score 降序排序
  `-- 返回 top-k 结果
  |
  v
memory_core.format_context()
  |
  v
输出可注入 Claude Code 的上下文
```

### C. 索引重建流程

```text
已有 Markdown 文件
memory/topics/*.md
  |
  v
scripts/update_index.py
  |
  v
memory_core.rebuild_index()
  |
  |-- ensure_memory_dirs()
  |-- 扫描 memory/topics/*.md
  |-- 解析一级标题作为 topic
  |-- 解析 "## 摘要" 段落作为 summary
  |-- extract_keywords() 重新提取关键词
  |-- 读取文件创建/修改时间
  |-- 构造 MemoryRecord
  `-- save_index() 覆盖写入 index.json
  |
  v
重建 memory/index.json
```

## 当前 MVP 能力边界

### 已具备能力

- 可以把一次会话文本保存为结构化 Markdown 记忆。
- 可以按主题和日期生成记忆文件名。
- 可以维护 `index.json` 主题索引。
- 可以基于关键词和摘要进行简单相关性检索。
- 可以把检索结果格式化为 Claude Code 可注入上下文。
- 可以从已有 Markdown 文件重建索引。
- 提供了会话后写入和用户输入前检索的 Hook 示例。
- 提供了一个覆盖保存、检索、格式化的 MVP 测试。

### 主要限制

- 摘要质量有限：`simple_summary()` 当前是截断式摘要，不是真正的语义总结。
- 关键词抽取粗糙：规则法对中文主题、技术实体和长上下文的表现有限。
- 检索能力有限：当前是关键词加权匹配，不支持语义相似度、时间衰减或多字段排序优化。
- 记忆合并能力缺失：同主题多次写入可能产生追加内容过长或碎片化。
- 项目隔离缺失：所有记忆默认写入同一个 `memory/` 目录。
- 并发写入保护缺失：多进程同时写入 `index.json` 可能产生竞争。
- Hook 仍是示例：需要根据 Claude Code 实际 Hook 事件、环境变量和输入格式做生产化适配。
- 测试覆盖不足：当前主要覆盖 Happy Path，缺少索引损坏、空查询、无匹配、重复主题、重建索引和 CLI 参数测试。
- 编码显示问题：当前若干中文 README、注释或文档在 PowerShell 读取时显示乱码；需要后续确认文件真实编码并统一为 UTF-8。

## 项目结构专业性评价

| 评价维度 | 结论 | 说明 |
|---|---|---|
| 目录命名是否清晰 | 较清晰 | `scripts/`、`hooks/`、`memory/`、`tests/`、`docs/` 分层明确，符合 MVP 项目习惯 |
| 脚本职责是否单一 | 较好 | 三个 CLI 脚本分别负责保存、检索、重建；核心逻辑集中在 `memory_core.py` |
| Skill 文档是否明确 | 基本明确 | 有目标、场景、写入/检索规则和约束；建议补充机器可执行的 Hook 配置和更严格的输入输出约定 |
| Hook 示例是否易接入 | 易于理解 | Shell 示例直观，但还不是 Claude Code Hook 的完整生产配置 |
| `memory/` 是否适合作为本地记忆库 | 适合 MVP | Markdown + JSON 可读性和可迁移性强；后续需要项目隔离、索引保护和清理机制 |
| 测试是否覆盖 MVP 核心流程 | 基本覆盖 | 已覆盖保存到检索再到上下文输出；还需增加边界和异常场景 |
| 是否适合扩展为正式 Skill 或 Plugin | 适合 | 当前边界清晰、依赖轻、接口简单，便于逐步替换摘要、关键词和检索算法 |

## 后续优化路线

### 第一阶段：保持 MVP 简洁，只做结构整理和文档完善

- 统一所有 Markdown、Python 注释和 Shell 注释的 UTF-8 编码，解决中文显示乱码。
- 完善 `README.md`，补充真实使用场景、命令输出示例和常见问题。
- 完善 `SKILL.md`，明确触发条件、记忆写入格式、检索注入规则、失败降级策略。
- 为 Hook 增加 Claude Code `settings.json` 配置示例，但仍保留 example 脚本。
- 增加 `.gitignore`，避免测试生成的记忆文件、缓存和临时文件被误提交。
- 增加基础测试：空输入、无匹配、重复主题、索引损坏、索引重建。

### 第二阶段：增强摘要质量、关键词抽取和检索能力

- 将 `simple_summary()` 替换为可插拔摘要器，支持 Claude、OpenAI 或本地模型。
- 将 “关键决策” 和 “待办事项” 从占位内容改为结构化抽取结果。
- 改进关键词抽取：支持中文分词、技术实体识别、停用词过滤和权重排序。
- 改进检索评分：加入标题匹配、关键词匹配、摘要匹配、正文片段匹配和时间衰减。
- 限制注入上下文长度，优先输出摘要、决策和待办，而不是完整原文。

### 第三阶段：接入 Claude Code Hook、Skill 或 Plugin 生态

- 根据 Claude Code Hook 规范提供可直接复制的配置示例。
- 将保存和检索命令封装为更稳定的 Skill 操作说明。
- 增加手动检索命令或 slash command 风格入口。
- 提供安装说明、初始化命令和目录权限检查。
- 若扩展为 Plugin，补充 manifest、版本、权限、配置项和发布流程。

### 第四阶段：可选增加向量检索、记忆合并、项目级隔离和日志系统

- 增加 embedding 和向量检索，提高语义召回能力。
- 支持按项目、仓库或 workspace 隔离记忆目录。
- 增加记忆合并和去重策略，避免同主题记忆碎片化。
- 增加记忆过期、归档和时间衰减机制。
- 增加日志系统，记录写入、检索、索引重建和异常信息。
- 增加文件锁或原子写入，降低并发写入 `index.json` 的风险。
- 可选增加 Web UI 或 TUI，用于浏览、搜索、编辑和删除记忆。

## 使用命令示例

### 保存记忆

```bash
python scripts/summarize_session.py \
  --topic "Claude Code 记忆机制" \
  --text "用户希望通过 Hook 自动总结对话，并保存为 Markdown 记忆库。"
```

从文件保存：

```bash
python scripts/summarize_session.py \
  --topic "登录 Bug 修复" \
  --file /path/to/conversation.txt
```

同主题同日期文件存在时覆盖而不是追加：

```bash
python scripts/summarize_session.py \
  --topic "项目初始化" \
  --text "本轮完成项目初始化讨论。" \
  --no-append
```

### 检索记忆

```bash
python scripts/retrieve_memory.py \
  --query "Claude Code 怎么保存历史对话"
```

限制返回数量：

```bash
python scripts/retrieve_memory.py \
  --query "登录超时问题" \
  --top-k 3
```

输出 JSON：

```bash
python scripts/retrieve_memory.py \
  --query "记忆机制" \
  --json
```

### 重建索引

```bash
python scripts/update_index.py
```

### 运行测试

```bash
python tests/test_memory_skill.py
```

### Hook 示例调用

会话结束后写入记忆：

```bash
bash hooks/post_conversation_example.sh "AI 记忆系统设计" conversation.txt
```

用户输入前检索记忆：

```bash
bash hooks/pre_prompt_example.sh "如何实现会话记忆持久化"
```

### 查看记忆库

```bash
cat memory/index.json | python -m json.tool
ls memory/topics/
cat "memory/topics/Claude_Code_记忆机制_2026-06-03.md"
```

## 结论

当前项目结构已经具备专业 MVP 的基本形态：核心能力、CLI 入口、Hook 示例、记忆存储和测试目录分层明确，适合继续演进为正式 Claude Code Skill。短期最值得优先处理的是文档编码、Hook 配置示例、测试覆盖和索引重建时跳过说明文件；中期再替换摘要、关键词和检索算法；长期可扩展为具备项目隔离、向量检索、记忆合并和日志审计能力的本地记忆系统。
