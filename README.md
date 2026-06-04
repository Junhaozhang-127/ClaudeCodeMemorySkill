<style>
  .lang-radio {
    position: absolute;
    opacity: 0;
    pointer-events: none;
  }
  .lang-bar {
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
    border-bottom: 2px solid #d1d5db;
    padding-bottom: 8px;
  }
  .lang-label {
    cursor: pointer;
    padding: 4px 14px;
    border-radius: 4px 4px 0 0;
    color: #6b7280;
    font-weight: 500;
    font-size: 14px;
  }
  .lang-label:hover {
    color: #374151;
    background: #f3f4f6;
  }
  #lang-en:checked ~ .lang-bar .label-en {
    color: #2563eb;
    border-bottom: 2px solid #2563eb;
    margin-bottom: -10px;
  }
  #lang-zh:checked ~ .lang-bar .label-zh {
    color: #2563eb;
    border-bottom: 2px solid #2563eb;
    margin-bottom: -10px;
  }
  .content-zh {
    display: none;
  }
  #lang-zh:checked ~ .content-en {
    display: none;
  }
  #lang-zh:checked ~ .content-zh {
    display: block;
  }
</style>

<input type="radio" name="lang-switch" id="lang-en" class="lang-radio" checked>
<input type="radio" name="lang-switch" id="lang-zh" class="lang-radio">

<div class="lang-bar">
  <label for="lang-en" class="lang-label label-en">English</label>
  <label for="lang-zh" class="lang-label label-zh">中文</label>
</div>

<div class="content-en">

# Claude Code Memory Skill

Lightweight local memory bank for Claude Code — automatically saves sessions as structured Markdown and retrieves historical context in new sessions.

## Why You Need It

Each Claude Code session is isolated. When you switch sessions, all prior project context, bug analyses, and design decisions are lost, forcing you to manually repeat yourself.

This skill automatically distills conversations into structured memories (summaries, key decisions, TODOs) at session end, and auto-retrieves relevant context based on your input in new sessions.

## Installation

```bash
git clone https://github.com/Junhaozhang-127/ClaudeMeory.git
cd ClaudeMeory
python scripts/install.py --interactive
```

On first run, you'll be prompted to choose a memory storage path — press Enter for the default.

**Requirements**: Python 3.7+, zero core dependencies. Optional: `pip install jieba` for enhanced Chinese word segmentation.

## Quick Start

```bash
# Save a memory
python scripts/summarize_session.py --topic "Architecture Discussion" --text "Decided to use microservices..."

# Retrieve relevant memories
python scripts/retrieve_memory.py --query "architecture plan"

# View JSON output (with score breakdown)
python scripts/retrieve_memory.py --query "architecture" --json

# Rebuild index
python scripts/update_index.py
```

## Core Capabilities

### Structured Memory
Automatically extracts summaries, key decisions, and TODOs from conversations into structured Markdown memory files.

### Hybrid Retrieval
Multi-signal weighted scoring (topic > keywords > decisions > TODOs > summary), returning interpretable `score_breakdown` results.

### Workspace Isolation
Memory directories are isolated per project — different projects never interfere.

```bash
python scripts/workspace_manager.py init --workspace my-project
python scripts/summarize_session.py --workspace my-project --topic "..." --text "..."
```

### Hook Automation
Auto-save at session end, auto-retrieve at session start. Supports bash / Windows CMD / PowerShell.

See `docs/HOOK_SETUP.md` for details.

### Memory Maintenance
Deduplication, merging, compaction, archiving — all with dry-run protection.

```bash
python scripts/memory_maintenance.py detect-duplicates
python scripts/memory_maintenance.py compact --topic "..." --dry-run
python scripts/memory_maintenance.py archive-old --days 180 --dry-run
```

### Release Tools

| Command | Purpose |
|---------|---------|
| `install.py` | Installation & initialization |
| `uninstall.py` | Safe uninstallation |
| `upgrade.py` | Upgrade & migration |
| `health_check.py` | System health diagnostics |
| `memory_stats.py` | Memory bank statistics |
| `release_prepare.py` | Pre-release cleanup |
| `run_acceptance.py` | Acceptance tests |

## Project Structure

```text
ClaudeMeory/
├── scripts/          # Core Python scripts
├── hooks/            # Hook scripts (bash/bat/ps1)
├── memory/           # Memory storage directory
│   ├── index.json    # Topic index
│   └── topics/       # Markdown memory files
├── docs/             # Documentation
│   ├── CAPABILITY_MATRIX.md    # Capability matrix
│   ├── DEVELOPMENT_ROADMAP.md  # Development roadmap
│   ├── HOOK_SETUP.md           # Hook configuration guide
│   ├── PROJECT_STRUCTURE.md    # Architecture overview
│   └── SUMMARIZER_DESIGN.md    # Summarizer design
├── tests/            # Tests (78 items)
├── plugin.json       # Plugin Manifest
├── install.sh        # One-click install
├── CHANGELOG.md      # Changelog
└── LICENSE           # MIT
```

## Testing

```bash
python tests/test_memory_skill.py        # 78 unit tests
python scripts/run_acceptance.py --quick # 7 acceptance tests
```

## Configuration

Priority: CLI arguments > environment variables > config.json > defaults

```bash
# Environment variables
export CLAUDE_MEMORY_WORKSPACE=my-project
export CLAUDE_MEMORY_DIR=/path/to/memories

# Or use config.json
python scripts/install.py --interactive  # Interactive generation
```

## Documentation Index

| Document | Content |
|----------|---------|
| `SKILL.md` | Skill behavior rules & slash commands |
| `CHANGELOG.md` | Phase 1–5 changelog |
| `docs/CAPABILITY_MATRIX.md` | 40+ capability status table |
| `docs/HOOK_SETUP.md` | Hook configuration (bash/bat/ps1) |
| `docs/PROJECT_STRUCTURE.md` | Architecture & module overview |
| `docs/SUMMARIZER_DESIGN.md` | Pluggable summarizer design |
| `docs/DEVELOPMENT_ROADMAP.md` | Five-phase roadmap |
| `docs/settings.template.json` | Hook config template |
| `docs/config.example.json` | Config file example |

## Known Limitations

- **Plugin Manifest**: `plugin.json` is currently a manifest template, not yet validated against the official Claude Code plugin runtime.
- **Slash Commands**: Currently mapped declaratively to CLI scripts via SKILL.md / plugin.json, not a full official `commands/` directory implementation.
- **EmbeddingRetriever**: Currently a stub — does not provide true semantic vector retrieval. Retrieval primarily relies on keyword + multi-field weighted scoring.
- **Storage**: Local Markdown + JSON file storage, no multi-user concurrent database.

See `LIMITATIONS.md` for details.

## Security & Privacy

- All memories are stored locally by default and never uploaded to any remote service.
- Never expose API keys, passwords, tokens, or other sensitive information in conversations.
- Use `scripts/memory_maintenance.py` to maintain or clean up memories.
- Logs do not record full conversation transcripts.

## Repository Note

The current repository name is `ClaudeMeory` (for historical reasons). The project display name is **Claude Code Memory Skill**.

## License

MIT — see `LICENSE`

</div>

<div class="content-zh">

# Claude Code Memory Skill

轻量级 Claude Code 本地记忆库 — 自动保存会话为结构化 Markdown，新会话中检索历史上下文。

## 为什么需要它

Claude Code 每个会话相互独立。切换会话后，之前的项目背景、Bug 分析、设计方案全部丢失，需要手动复述。

本 Skill 在会话结束时自动将对话沉淀为结构化记忆（摘要、关键决策、待办事项），并在新会话中根据输入自动检索相关历史，注入上下文。

## 安装

```bash
git clone https://github.com/Junhaozhang-127/ClaudeMeory.git
cd ClaudeMeory
python scripts/install.py --interactive
```

首次运行会提示选择记忆存储路径，直接回车使用默认路径。

**要求**: Python 3.7+，核心零依赖。可选 `pip install jieba` 增强中文分词。

## 快速开始

```bash
# 保存一条记忆
python scripts/summarize_session.py --topic "项目架构讨论" --text "决定采用微服务架构..."

# 检索相关记忆
python scripts/retrieve_memory.py --query "架构方案"

# 查看 JSON 输出（含评分明细）
python scripts/retrieve_memory.py --query "架构" --json

# 重建索引
python scripts/update_index.py
```

## 核心能力

### 结构化记忆
自动从对话中抽取摘要、关键决策和待办事项，生成 Markdown 记忆文件。

### 混合检索
多信号加权评分（主题 > 关键词 > 决策 > 待办 > 摘要），返回 score_breakdown 可解释结果。

### Workspace 隔离
按项目隔离记忆目录，不同项目互不干扰。

```bash
python scripts/workspace_manager.py init --workspace my-project
python scripts/summarize_session.py --workspace my-project --topic "..." --text "..."
```

### Hook 自动化
会话结束时自动保存、新会话开始时自动检索。支持 bash / Windows CMD / PowerShell。

详见 `docs/HOOK_SETUP.md`。

### 记忆维护
去重、合并、压缩、归档 — 全部 dry-run 保护。

```bash
python scripts/memory_maintenance.py detect-duplicates
python scripts/memory_maintenance.py compact --topic "..." --dry-run
python scripts/memory_maintenance.py archive-old --days 180 --dry-run
```

### 发布工具

| 命令 | 用途 |
|------|------|
| `install.py` | 安装与初始化 |
| `uninstall.py` | 安全卸载 |
| `upgrade.py` | 升级与迁移 |
| `health_check.py` | 系统健康诊断 |
| `memory_stats.py` | 记忆库统计 |
| `release_prepare.py` | 发布前清理 |
| `run_acceptance.py` | 验收测试 |

## 项目结构

```text
ClaudeMeory/
├── scripts/          # 核心 Python 脚本
├── hooks/            # Hook 脚本 (bash/bat/ps1)
├── memory/           # 记忆存储目录
│   ├── index.json    # 主题索引
│   └── topics/       # Markdown 记忆文件
├── docs/             # 文档
│   ├── CAPABILITY_MATRIX.md    # 能力矩阵
│   ├── DEVELOPMENT_ROADMAP.md  # 开发路线图
│   ├── HOOK_SETUP.md           # Hook 配置指南
│   ├── PROJECT_STRUCTURE.md    # 架构说明
│   └── SUMMARIZER_DESIGN.md    # 摘要器设计
├── tests/            # 测试 (78 项)
├── plugin.json       # Plugin Manifest
├── install.sh        # 一键安装
├── CHANGELOG.md      # 变更记录
└── LICENSE           # MIT
```

## 测试

```bash
python tests/test_memory_skill.py        # 78 项单元测试
python scripts/run_acceptance.py --quick # 7 项验收测试
```

## 配置

优先级：CLI 参数 > 环境变量 > config.json > 默认值

```bash
# 环境变量
export CLAUDE_MEMORY_WORKSPACE=my-project
export CLAUDE_MEMORY_DIR=/path/to/memories

# 或使用 config.json
python scripts/install.py --interactive  # 交互式生成
```

## 文档索引

| 文档 | 内容 |
|------|------|
| `SKILL.md` | Skill 行为规则与 Slash Command |
| `CHANGELOG.md` | Phase 1–5 变更记录 |
| `docs/CAPABILITY_MATRIX.md` | 40+ 能力状态表 |
| `docs/HOOK_SETUP.md` | Hook 配置 (bash/bat/ps1) |
| `docs/PROJECT_STRUCTURE.md` | 架构与模块说明 |
| `docs/SUMMARIZER_DESIGN.md` | 可插拔摘要器设计 |
| `docs/DEVELOPMENT_ROADMAP.md` | 五阶段路线图 |
| `docs/settings.template.json` | Hook 配置模板 |
| `docs/config.example.json` | 配置文件示例 |

## 已知限制

- **Plugin Manifest**：`plugin.json` 当前是 manifest-template，未经过 Claude Code 官方插件运行时验证
- **Slash Command**：当前通过 SKILL.md / plugin.json 声明式映射到 CLI 脚本，不是完整官方 commands 目录实现
- **EmbeddingRetriever**：当前为 stub，不提供真正的语义向量检索。检索主要依赖关键词 + 多字段加权评分
- **存储**：本地 Markdown + JSON 文件存储，不提供多用户并发数据库

详见 `LIMITATIONS.md`。

## 安全与隐私

- 所有记忆默认保存在本地，不会上传到任何远程服务
- 请勿在对话中暴露 API Key、密码、Token 等敏感信息
- 可通过 `scripts/memory_maintenance.py` 维护或清理记忆
- 日志不记录完整对话原文

## 仓库说明

当前仓库名为 `ClaudeMeory`（历史原因）。项目显示名称统一为 **Claude Code Memory Skill**。

## License

MIT — 详见 `LICENSE`

</div>
