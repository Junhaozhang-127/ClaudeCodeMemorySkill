<p align="right"><b>中文</b> | <a href="README.md">English</a></p>

# Claude Code Memory Skill

轻量级 Claude Code 本地记忆与会话工作区 — 语义检索、LLM 摘要、会话空间管理、交互式 TUI。

**v0.7.0** — 352 项测试，零失败。

## 为什么需要它

Claude Code 每个会话相互独立。切换会话后，项目背景、Bug 分析、设计方案全部丢失。

本 Skill 将对话保存为结构化记忆，通过语义/混合检索查找历史上下文，管理会话工作区，并提供交互式 TUI 用于会话导航。

## 安装

```bash
git clone https://github.com/Junhaozhang-127/ClaudeCodeMemorySkill.git
cd ClaudeCodeMemorySkill
pip install jieba              # 可选：增强中文分词
```

**要求**: Python 3.7+，核心零依赖。可选 `jieba` 增强中文分词。

## 快速开始

```bash
# 保存记忆（自动识别当前会话）
python scripts/summarize_session.py --topic "项目架构讨论" --text "决定采用微服务架构..."

# 关键词检索
python scripts/retrieve_memory.py --query "架构方案"

# 语义检索（需配置 EMBEDDING_API_KEY）
python scripts/retrieve_memory.py --query "架构" --mode semantic --json

# 混合检索（关键词 + 语义）
python scripts/retrieve_memory.py --query "架构" --mode hybrid

# 检索所有会话
python scripts/retrieve_memory.py --query "架构" --all-sessions

# 检索当前会话 + 链接会话
python scripts/retrieve_memory.py --query "架构" --include-linked-sessions

# 会话管理
python scripts/session_cli.py create --title "项目 Alpha" --use
python scripts/session_cli.py list
python scripts/session_cli.py current
python scripts/session_cli.py tui       # 交互式会话选择器
```

## 核心能力 (v0.7.0)

### 语义与混合检索 (v0.6.0)
三种检索模式：`keyword`（关键词）、`semantic`（语义）、`hybrid`（混合）。Embedding 向量相似度搜索，自动降级。支持 OpenAI-compatible API（设置 `EMBEDDING_API_KEY`）或零配置 Fake Provider。

```bash
python scripts/retrieve_memory.py --query "..." --mode hybrid
```

### LLM 摘要 (v0.6.0)
三种摘要类型：`brief`（简短）、`semantic`（语义）、`memory`（记忆压缩）。长文本自动分块合并。无 LLM Key 时自动降级为规则摘要。

```bash
python scripts/summarize_session.py --topic "..." --text "..." --summary-mode llm
```

### Slash Command 系统 (v0.6.0)
CommandRegistry 管理 5 个 Slash Command：`memory:save`、`memory:retrieve`、`memory:rebuild`、`memory:manage`、`memory:session`。参数校验、结构化结果、编辑距离建议。

```bash
/memory save "架构" --text "决定采用微服务"
/memory retrieve "架构" --mode hybrid --all-sessions
/memory session create --title "书籍审稿" --use
/memory session tui     # 交互式 TUI
```

### 记忆生命周期 (v0.6.0)
MemoryRecord 扩展至 23 字段。状态状态机：`active` → `archived` / `expired` / `merged` / `deleted`。TTL 自动过期、content-hash 去重、质量报告。

```bash
python scripts/memory_maintenance.py detect-duplicates
python -c "from memory_lifecycle import generate_quality_report; print(generate_quality_report())"
```

### 会话工作区管理 (v0.7.0)
每个会话独立目录，含 manifest、memories、links、events。完整生命周期：create、list、rename、archive、soft-delete、restore。

```bash
python scripts/session_cli.py create --title "论文审稿" --use
python scripts/session_cli.py list
python scripts/session_cli.py info --session-id <id>
python scripts/session_cli.py delete --session-id <id>
python scripts/session_cli.py restore --session-id <id>
```

### 会话感知记忆存储 (v0.7.0)
`save_memory` 自动写入当前会话。`retrieve_memory` 默认仅检索当前会话。支持 `--session-id`、`--all-sessions`、`--include-archived-sessions`、`--include-linked-sessions` 过滤。

### 会话链接检索 (v0.7.0)
通过 `links.json` 显式链接会话。`include_linked_sessions=True` 时检索范围扩展至链接会话。

```bash
python scripts/session_cli.py link --to <target_session_id> --reason "相关内容"
python scripts/session_cli.py unlink --to <target_session_id>
python scripts/session_cli.py links
```

### 交互式会话 TUI (v0.7.0)
终端会话选择器，支持键盘导航：↑/↓、Enter、Delete、N、R、A、L、Q。Delete 软删除二次确认。

```bash
python scripts/session_cli.py tui
python scripts/session_cli.py tui --include-archived
```

### 结构化记忆与自动保存
自动抽取摘要、决策、待办事项。轮次计时器自动保存（默认每 10 轮）。同主题智能合并。Hook 脚本支持 bash/bat/ps1。

### 记忆维护
去重、合并、压缩、归档 — 全部 dry-run 保护。

```bash
python scripts/memory_maintenance.py detect-duplicates
python scripts/memory_maintenance.py compact --topic "..." --dry-run
python scripts/memory_maintenance.py archive-old --days 180 --dry-run
```

## 项目结构 (v0.7.0)

```text
ClaudeMeory/
├── scripts/                # 核心 Python（20+ 模块）
│   ├── memory_core.py          # 记忆保存/检索/格式化核心
│   ├── retrieval.py            # Keyword/Hybrid/Semantic 检索器
│   ├── summarizers.py          # RuleBased/LLM 摘要器
│   ├── embedding_provider.py   # EmbeddingProvider ABC + Fake/OpenAI
│   ├── llm_provider.py         # LLMProvider ABC + Fake/OpenAI
│   ├── memory_lifecycle.py     # 生命周期状态机 + 质量报告
│   ├── session_manager.py      # 会话 CRUD + 链接 + 事件
│   ├── session_tui.py          # 交互式会话选择器
│   ├── session_cli.py          # 会话 CLI 入口
│   └── ...
├── commands/               # Slash Command 处理器 (v0.6.0)
│   ├── base.py                 # Command + CommandResult
│   ├── registry.py             # CommandRegistry
│   ├── memory_save.py          # /memory save
│   ├── memory_retrieve.py      # /memory retrieve
│   ├── memory_rebuild.py       # /memory rebuild
│   ├── memory_manage.py        # /memory manage
│   └── memory_session.py       # /memory session (12 动作)
├── hooks/                  # Hook 脚本 (bash/bat/ps1)
├── .claude-plugin/         # Plugin manifest + marketplace
├── memory/                 # 记忆存储
│   ├── index.json              # 主题索引
│   ├── .memory/sessions/       # 会话工作区 (v0.7.0)
│   └── topics/                 # Markdown 记忆文件
├── docs/                   # 文档
│   ├── SESSION_WORKSPACE.md    # 会话工作区指南
│   ├── SMOKE_TEST.md           # 真实 API 手工测试指南
│   ├── releases/               # 发布摘要
│   └── ...
├── tests/                  # 352 项测试，零失败
├── CHANGELOG.md
└── LICENSE
```

## 测试

```bash
python -m pytest -q                        # 352 项测试（0 失败）
python -m pytest tests/test_session_manager.py -v     # 52 项会话测试
python -m pytest tests/test_session_tui.py -v         # 47 项 TUI 测试
python scripts/run_acceptance.py --quick              # 验收测试
```

## 配置

优先级：CLI 参数 > 环境变量 > config.json > 默认值

```bash
# 会话工作区 (v0.7.0)
export SESSION_ENABLED=true

# 检索模式: keyword / semantic / hybrid
export CLAUDE_MEMORY_RETRIEVAL_MODE=hybrid

# Embedding Provider (v0.6.0)
export EMBEDDING_API_KEY=sk-...
export EMBEDDING_API_BASE=https://api.openai.com/v1
export EMBEDDING_MODEL=text-embedding-3-small

# LLM Provider (v0.6.0)
export LLM_API_KEY=sk-...
export LLM_API_BASE=https://api.openai.com/v1
export LLM_MODEL=gpt-4o-mini

# 自动保存
export MEMORY_AUTO_SAVE_INTERVAL=10
```

## 文档索引

| 文档 | 内容 |
|------|------|
| `README.md` | 英文 README |
| `SKILL.md` | Skill 行为规则与 Slash Command |
| `CHANGELOG.md` | v0.1.0 – v0.7.0 变更记录 |
| `docs/SESSION_WORKSPACE.md` | 会话工作区指南 |
| `docs/SMOKE_TEST.md` | 真实 API Provider 手工测试 |
| `docs/CAPABILITY_MATRIX.md` | 40+ 能力状态表 |
| `docs/HOOK_SETUP.md` | Hook 配置 (bash/bat/ps1) |
| `docs/PROJECT_STRUCTURE.md` | 架构与模块说明 |
| `docs/SUMMARIZER_DESIGN.md` | 可插拔摘要器设计 |
| `docs/DEVELOPMENT_ROADMAP.md` | 五阶段开发路线图 |
| `docs/config.example.json` | 配置文件示例 |
| `docs/settings.template.json` | Hook 配置模板 |

## 已知限制

- **Plugin Manifest**：`.claude-plugin/plugin.json` 为 manifest 模板，尚未经过 Claude Code 官方插件运行时验证。
- **真实 API E2E**：Embedding/LLM Provider 使用 Fake Provider 做 CI 测试。真实 API 手工测试见 `docs/SMOKE_TEST.md`，暂未自动化。
- **存储**：本地 Markdown + JSON + JSONL 文件存储，不支持多用户并发数据库。
- **TUI**：通过 controller/renderer 单元测试覆盖；真实终端交互不在 CI 中。

## 安全与隐私

- 所有记忆默认保存在本地，不会上传到任何远程服务。
- 请勿在对话中暴露 API Key、密码、Token 等敏感信息。
- Embedding/LLM API Key 仅通过环境变量配置，不写入文件。
- 日志不记录完整对话原文。

## 仓库说明

仓库名：`ClaudeCodeMemorySkill`（GitHub 显示为 `ClaudeMeory`，历史原因）。

## License

MIT — 详见 `LICENSE`
