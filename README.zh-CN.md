<p align="right"><b>中文</b> | <a href="README.md">English</a></p>

# Claude Code Memory Skill

面向 Claude Code 的生产级本地记忆系统与会话工作区管理器。将短暂的聊天会话转化为持久、可检索、可管理的知识库。

**v0.7.0** — 352 项测试，零失败。MIT 协议。

---

## 目录

1. [解决了什么问题](#解决了什么问题)
2. [架构概览](#架构概览)
3. [安装](#安装)
4. [快速开始](#快速开始)
5. [功能指南](#功能指南)
   - [记忆持久化与自动保存](#1-记忆持久化与自动保存)
   - [检索 — 关键词、语义与混合](#2-检索--关键词语义与混合)
   - [LLM 摘要](#3-llm-摘要)
   - [Slash Command 系统](#4-slash-command-系统)
   - [记忆生命周期管理](#5-记忆生命周期管理)
   - [会话工作区管理](#6-会话工作区管理)
   - [会话链接检索](#7-会话链接检索)
   - [交互式会话 TUI](#8-交互式会话-tui)
6. [项目结构](#项目结构)
7. [配置参考](#配置参考)
8. [测试](#测试)
9. [文档索引](#文档索引)
10. [已知限制](#已知限制)
11. [安全与隐私](#安全与隐私)

---

## 解决了什么问题

### 问题一：会话隔离

Claude Code 每个会话从零开始。切换会话后，项目背景、Bug 根因、架构决策和待办事项全部丢失，只能手动复述。

**解决方案**：每次会话自动保存为结构化 Markdown 记忆。新会话的第一个 prompt 触发检索，自动将最相关的 5 条历史记忆注入 Claude 上下文。

### 问题二：关键词搜不到"意思相近但用词不同"的内容

你记得讨论过"多用户记忆隔离"，但关键词搜"隔离"无结果——因为原始讨论用的是"workspace separation"。

**解决方案**：基于 Embedding 的语义检索理解含义而非字面。查询"记忆隔离"能找到"workspace separation"讨论。无 API Key 时自动降级为关键词检索并记录日志，不崩溃。

### 问题三：记忆太多太杂

记忆库不断增长，不同项目的记忆混在一起变成噪音。需要按项目上下文组织记忆。

**解决方案**：会话工作区管理器为每个项目提供独立的记忆空间。记忆存入正确的会话，检索时只从你关心的会话中搜索。相关会话可以链接起来。

### 问题四：记忆腐化

旧记忆堆积。你不知道哪些还相关、哪些已过时、哪些是重复的。

**解决方案**：内置生命周期管理 — TTL 自动过期、content-hash 精确去重、相似度近似去重检测、质量报告、归档/合并/压缩工具。

---

## 架构概览

```
┌────────────────────────────────────────────────────────────┐
│                    Claude Code Session                      │
│                                                             │
│  /memory save ───┐               ┌── /memory retrieve       │
│  /memory manage ─┤               ├── /memory session        │
│  Hook: Stop ─────┘               └── Hook: PrePrompt ───────│
└──────────┬──────────────────────────────┬───────────────────┘
           │ save                          │ retrieve + 注入
           ▼                               ▼
┌─────────────────────────────────────────────────────────────┐
│                   CommandRegistry 层                          │
│  commands/memory_save.py    commands/memory_retrieve.py      │
│  commands/memory_manage.py  commands/memory_session.py       │
└──────────┬──────────────────────────────┬───────────────────┘
           │                              │
           ▼                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      核心引擎                                │
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────────┐  │
│  │ memory_core  │  │ retrieval.py  │  │ summarizers.py   │  │
│  │ 保存/检索    │  │ Keyword/Hybrid│  │ RuleBased/LLM    │  │
│  │ 格式化/索引  │  │ Semantic      │  │ SummaryResult    │  │
│  └──────┬───────┘  └───────┬───────┘  └────────┬─────────┘  │
│         │                  │                    │            │
│  ┌──────┴──────────────────┴────────────────────┴─────────┐  │
│  │              可插拔 Provider                             │  │
│  │  embedding_provider.py  │  llm_provider.py              │  │
│  │  Fake ↔ OpenAI-compatible API                            │  │
│  └─────────────────────────────────────────────────────────┘  │
└──────────┬───────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────┐
│                  会话工作区层                                 │
│  session_manager.py   session_tui.py   session_cli.py       │
│                                                              │
│  .memory/sessions/                                           │
│    index.json          ← 全局会话注册表                       │
│    current.json        ← 当前会话指针                         │
│    <session_id>/                                             │
│      manifest.json     ← 会话元数据                           │
│      memories.jsonl    ← 记忆记录镜像                         │
│      links.json        ← 链接会话图                           │
│      events.jsonl      ← 操作审计日志                         │
└─────────────────────────────────────────────────────────────┘
```

系统分层设计：**Command 处理器**接收用户输入 → **核心引擎**处理保存/检索/摘要 → **会话工作区**按上下文组织 → **可插拔 Provider** 处理 embedding/LLM（未配置时自动降级为规则方案）。

---

## 安装

```bash
git clone https://github.com/Junhaozhang-127/ClaudeCodeMemorySkill.git
cd ClaudeCodeMemorySkill

# 零强制依赖 — Python 3.7+ 标准库即可运行
pip install jieba              # 可选：增强中文分词
pip install httpx              # 可选：OpenAI API 更快 HTTP 客户端
```

**要求**：Python 3.7+。所有核心功能仅需标准库。

---

## 快速开始

### 保存与检索（30 秒）

```bash
# 1. 保存第一条记忆
python scripts/summarize_session.py \
  --topic "架构决策" \
  --text "决定使用 Redis 做缓存。关键约束：单实例最大 256MB。"

# 2. 检索回来
python scripts/retrieve_memory.py --query "缓存架构" --json

# 3. 查看记忆库状态
python scripts/memory_stats.py
```

### 创建会话工作区

```bash
# 创建工作区并切换
python scripts/session_cli.py create --title "我的项目" --use

# 此后所有保存自动归属此会话
python scripts/summarize_session.py --topic "Bug #42" --text "根因：worker pool 竞态条件"

# 列出所有会话
python scripts/session_cli.py list

# 打开交互式会话选择器
python scripts/session_cli.py tui
```

---

## 功能指南

### 1. 记忆持久化与自动保存

每次对话被提炼为结构化 Markdown，包含五个语义段落：

| 段落 | 内容 | 抽取方式 |
|------|------|----------|
| **摘要** | 精炼概述，前 3-5 句 | 句子分割 + 长度控制 |
| **关键词** | 10 个最显著术语 | jieba 分词 + 正则回退，停用词过滤 |
| **关键决策** | 架构选择、已确认方案 | 触发词匹配（决定/采用/确认/finalize） |
| **待办事项** | 行动项、待修复问题 | 触发词匹配（需要/TODO/FIXME/implement） |
| **原始对话** | 完整对话摘录 | 原文，代码块转义 |

**自动保存行为**：轮次计数器追踪对话轮数。每 N 轮（默认 10），hook `auto_save.sh` 触发 `summarize_session.py`。可配置间隔：

```bash
export MEMORY_AUTO_SAVE_INTERVAL=5   # 每 5 轮自动保存
export MEMORY_AUTO_SAVE_INTERVAL=0   # 禁用轮次自动保存
```

`plugin.json` 中注册了三个 Hook 事件：

| Hook 事件 | 触发时机 | 行为 |
|-----------|---------|------|
| `UserPromptSubmit` (auto_save) | 每 N 轮 | 保存当前对话 |
| `UserPromptSubmit` (pre_prompt) | 每次响应前 | 检索并注入相关记忆 |
| `Stop` (post_conversation) | 会话结束 | 最后保存所有未保存内容 |

**智能合并**：同一主题再次保存不产生重复文件。追加到已有 Markdown，合并 keywords/decisions/todos 并去重，保留原始 `created_at`，刷新 `updated_at`。

### 2. 检索 — 关键词、语义与混合

三种检索后端，通过 `--mode` 选择：

| 模式 | 机制 | 适用场景 | 依赖 |
|------|------|---------|------|
| `keyword` | 多字段加权 Token 匹配（主题 ≥ 关键词 > 决策 ≥ 待办 > 摘要）+ 时间衰减 | 精确术语查找，快速，零依赖 | 无 |
| `semantic` | Embedding 向量余弦相似度 | 查找概念相关但用词不同的内容 | `EMBEDDING_API_KEY` 或 Fake |
| `hybrid` | keyword (40%) + semantic (60%) 加权合并 | 兼顾精确与召回 | `EMBEDDING_API_KEY` 或 Fake |

**评分明细**：每条结果包含 `score_breakdown`，精确展示各字段贡献的分数。检索决策可审计。

**优雅降级**：未设置 `EMBEDDING_API_KEY` 时请求 `semantic` 或 `hybrid` 模式，系统自动降级为 `keyword` 并记录日志警告。不崩溃，不报错。

**会话感知检索** (v0.7.0)：默认只搜索当前会话的记忆。可扩展范围：

```python
# 仅当前会话（默认）
retrieve_memory("架构")

# 指定会话
retrieve_memory("架构", session_id="abc123")

# 所有活跃会话
retrieve_memory("架构", all_sessions=True)

# 当前会话 + 链接会话
retrieve_memory("架构", include_linked_sessions=True)
```

### 3. LLM 摘要

两个摘要器实现 `BaseSummarizer` 接口：

| 摘要器 | 机制 | 质量 | 依赖 |
|--------|------|------|------|
| `RuleBasedSummarizer` | 句子分割 + 触发词提取 | 结构化但机制化 | 无 |
| `LLMSummarizer` | LLM API (OpenAI-compatible) | 上下文感知、语义化 | `LLM_API_KEY` |

三种摘要类型：

| 类型 | 产出 | 使用场景 |
|------|------|---------|
| `brief` | 2-3 句话要点 | 列表预览、快速浏览 |
| `semantic` | 目标、约束、决策、结论 | 深度理解讨论内容 |
| `memory` | 可复用事实、用户偏好、项目状态、待办线索 | 记忆压缩供未来检索 |

**长文本处理**：超过约 4000 字符的文本在句子边界自动分割，逐块摘要后合并去重。结果标记 `partial: True` 和 `mode: llm_chunked`。

**降级链**：`LLMSummarizer` + API Key → `LLMSummarizer` + FakeProvider → `RuleBasedSummarizer`。降级结果带 `mode: rule_fallback` 元数据。系统不因缺少 API Key 而崩溃。

### 4. Slash Command 系统

`CommandRegistry` 管理 5 个 Slash Command，每个含参数校验、结构化 `CommandResult` 和编辑距离拼写建议：

```
/memory save       <主题> --text <内容> [--session-id <id>] [--summary-mode rule|llm|auto]
/memory retrieve   <查询> [--mode keyword|semantic|hybrid] [--session-id <id>] [--all-sessions] [--include-linked-sessions]
/memory rebuild    [--workspace <名称>]
/memory manage     <动作>   动作: quality / dedup / expire / merge / archive
/memory session    <动作>   动作: list / create / current / use / rename / archive / delete / restore / info / link / unlink / links / tui
```

命令通过两条路径可发现：`commands/*.md` frontmatter（Claude Code 自动发现）和 `plugin.json` `commands` 段（manifest 声明）。两条路径共存。

**命令流转**：
```
用户输入 "/memory retrieve 架构"
  → Claude Code 读取 commands/memory-retrieve.md frontmatter
  → 分发到 CommandRegistry.get("memory:retrieve")
  → 根据 args_schema 验证参数
  → 调用 handler → memory_core.retrieve_memory()
  → 返回结构化 CommandResult
```

### 5. 记忆生命周期管理

每条记忆记录包含 23 个元数据字段，含生命周期状态：

```
MemoryRecord:
  核心:    topic, file, keywords, summary, created_at, updated_at
  抽取:    decisions, todos
  v0.6.0:  memory_id, tags, source, last_accessed_at, access_count,
           confidence, importance, status, expires_at, merged_into,
           content_hash, embedding_hash, embedding_model, ttl_days,
           lifecycle_reason
  v0.7.0:  session_id, session_title
```

**状态状态机**：

```
active ──→ archived ──→ expired
  │            │
  ├── merged ──┘
  └── deleted
```

所有状态变更记录 reason 和 timestamp。`lifecycle_reason` 字段记录变更原因。

**质量报告** (`memory:manage quality`)：返回诊断摘要：

```json
{
  "total": 41,
  "active": 38, "archived": 0, "expired": 0, "merged": 2, "deleted": 1,
  "duplicate_candidates": 3,
  "near_duplicate_candidates": 5,
  "expired_candidates": 12,
  "low_quality_count": 7,
  "recommended_actions": [
    "过期 12 条: 运行 /memory manage expire --apply",
    "重复 3 对: 运行 /memory manage dedup"
  ]
}
```

**维护工具**：

| 命令 | 功能 |
|------|------|
| `detect-duplicates` | 基于关键词 Jaccard 相似度检测重复记忆对 |
| `merge --topic` | 合并 2+ 重复记录为一条，备份原始文件 |
| `compact --topic` | 裁剪旧对话块，保留摘要 + 最近 N 个块 |
| `archive-old --days` | 将超 N 天的记忆移至 `memory/archive/` |

所有破坏性操作默认 `--dry-run`。加 `--apply` 执行。

### 6. 会话工作区管理

每个会话是 `.memory/sessions/` 下的独立目录：

```
.memory/sessions/
├── index.json               # 全局注册表: {"version":"0.7.0","sessions":[...]}
├── current.json             # 指针: {"current_session_id":"abc123"}
├── default/                 # 自动创建的默认会话
│   ├── manifest.json        # SessionManifest 元数据
│   ├── memories.jsonl       # 记忆记录（追加式 JSON lines）
│   ├── summaries.jsonl      # 摘要记录
│   ├── embeddings.jsonl     # Embedding 向量
│   ├── links.json           # 链接会话图
│   ├── events.jsonl         # 审计日志
│   └── trash/               # 软删除暂存
└── <session_id>/            # 用户创建的会话（同上）
```

**会话生命周期**（通过 `/memory session` 12 个操作）：

| 操作 | 示例 | 行为 |
|------|------|------|
| `create` | `create --title "书籍审稿" --use` | 创建目录和全部文件，可选立即切换 |
| `list` | `list --include-archived` | 列出会话及状态/记忆数/链接数 |
| `current` | `current` | 显示当前会话 ID、标题、路径 |
| `use` | `use --session-id abc123` | 切换当前会话（写 `current.json`） |
| `rename` | `rename --session-id abc123 --title "新名"` | 更新 manifest + index |
| `archive` | `archive --session-id abc123` | status=archived（默认会话受保护） |
| `delete` | `delete --session-id abc123` | 软删除 — 只改状态，目录保留 |
| `restore` | `restore --session-id abc123 --use` | 恢复 deleted→active，可选切换 |
| `info` | `info --session-id abc123` | 完整 manifest + 文件状态 + 事件数 |
| `link` | `link --to abc123 --reason "相关"` | 链接当前会话到目标 |
| `unlink` | `unlink --to abc123` | 取消链接 |
| `links` | `links --session-id abc123` | 列出已链接会话 |

**默认会话保护**：`default` 会话（session_id=`"default"`）首次初始化时自动创建。不可归档或删除。如损坏，`ensure_default_session()` 强制恢复。

**软删除**：`delete_session()` 设置 `status = "deleted"` 并记录事件。目录和文件完整保留。`restore_session()` 恢复为 `active`。无显式用户操作不会物理删除。

**事件审计追踪**：对会话的每次操作追加一行 JSON 到 `events.jsonl`：

```json
{"event_id":"uuid","event_type":"session_linked","session_id":"abc","timestamp":"...","details":{"target_session_id":"xyz","reason":"相关项目"}}
```

### 7. 会话链接检索

会话可被显式链接形成检索图。当使用 `include_linked_sessions=True` 查询时，系统不仅搜索当前会话，还包括所有已链接的会话。

**用例**：有"书籍审稿"会话和"格式修复"会话，内容相关。链接它们：

```bash
/memory session link --to <格式修复会话ID> --reason "共享稿件处理流程"
```

之后从"书籍审稿"检索时加 `--include-linked-sessions`，"格式修复"的结果也会出现 — 每条标记 `[linked]`。

**链接数据模型** (`links.json`)：

```json
{
  "version": "0.7.0",
  "linked_sessions": [
    {
      "session_id": "abc123",
      "title": "格式修复",
      "linked_at": "2026-06-25 12:00:00",
      "link_type": "manual",
      "reason": "共享稿件处理流程"
    }
  ],
  "updated_at": "2026-06-25 12:00:00"
}
```

**检索范围总结**：

| 参数 | 搜索范围 |
|------|---------|
| *(默认)* | 仅当前会话 |
| `session_id=X` | 仅会话 X |
| `all_sessions=True` | 所有活跃会话（覆盖 linked） |
| `include_linked_sessions=True` | 当前 + 链接会话 |
| `include_archived_sessions=True` | 扩展至包含已归档 |

### 8. 交互式会话 TUI

通过 `python scripts/session_cli.py tui` 或 `/memory session tui` 启动。

```
——————————————————————————————————————————————————————————————————————————
Session Workspace Manager — v0.7.0

Current: Project Alpha / abc123

UP/DOWN:move ENTER:use DEL:delete N:new R:rename A:archive L:links V:archived D:deleted H:help Q:quit

> * Project Alpha         active    mem: 42   linked:  2   [default]
  ○ Book Review Phase 5   active    mem: 31   linked:  1
  ○ Format Fixer Dev      active    mem: 15   linked:  0
  ○ Old Migration Test    archived  mem:  3   linked:  0

Message: 已切换到 Project Alpha
——————————————————————————————————————————————————————————————————————————
```

**键盘控制**：

| 键 | 行为 | 说明 |
|----|------|------|
| ↑/↓ | 导航列表 | 有界；不会越界 |
| Enter | 切换到选中会话 | 阻止 archived/deleted；显示消息 |
| Delete | 软删除 | 二次按下确认；默认会话阻止 |
| N | 新建会话 | 输入标题；Enter 确认，Esc 取消 |
| R | 重命名选中 | 预填当前标题；原地编辑 |
| A | 归档选中 | 默认会话阻止 |
| L | 显示链接会话 | 展示链接会话 ID 和标题 |
| V | 切换归档显示 | 显示/隐藏列表中已归档会话 |
| D | 切换删除显示 | 显示/隐藏列表中已删除会话 |
| H / ? | 帮助 | 列出所有快捷键 |
| Q / Esc | 退出 | 未按 Enter 则会话不变 |

**架构**：TUI 分三层解耦 — `SessionTUIState`（数据）、`SessionTUIController`（业务逻辑）、`SessionTUIRenderer`（纯文本输出）。Controller 和 Renderer 零终端 I/O 依赖，可完全单元测试（47 项）。跨平台输入在 Windows 上用 `msvcrt`，在 Unix 上用 `termios`。

---

## 项目结构

```
ClaudeMeory/
│
├── scripts/                         # 核心引擎（22 个模块）
│   │
│   ├── memory_core.py               # 中心模块: save_memory, retrieve_memory, format_context,
│   │                                  rebuild_index, MemoryRecord 数据结构（25 字段）
│   │
│   ├── retrieval.py                 # BaseRetriever 抽象, KeywordRetriever（多字段加权）,
│   │                                  SemanticRetriever（embedding 余弦相似度）,
│   │                                  HybridRetriever（关键词+语义合并，3 种模式）
│   │
│   ├── summarizers.py               # BaseSummarizer 抽象, SummaryResult, EnhancedSummaryResult,
│   │                                  RuleBasedSummarizer（触发词提取）,
│   │                                  LLMSummarizer（3 种摘要类型，分块合并流水线）
│   │
│   ├── embedding_provider.py        # EmbeddingProvider 抽象, FakeEmbeddingProvider（ngram
│   │                                  确定性向量）, OpenAIEmbeddingProvider（urllib 实现）
│   │
│   ├── embedding_cache.py           # JSON 文件 embedding 缓存，SHA256 content-hash 键,
│   │                                  模型变更自动失效
│   │
│   ├── llm_provider.py              # LLMProvider 抽象, FakeLLMProvider（规则提取测试用）,
│   │                                  OpenAILLMProvider（urllib 实现）
│   │
│   ├── memory_lifecycle.py          # 状态状态机（5 状态, 8 转换）, TTL 自动过期,
│   │                                  generate_quality_report
│   │
│   ├── memory_maintenance.py        # CLI: detect-duplicates（Jaccard）, merge, compact, archive-old
│   │
│   ├── session_manager.py           # SessionManager（约 800 行）: CRUD, link, unlink, events,
│   │                                  SessionManifest/SessionIndex/CurrentSession/SessionEvent
│   │
│   ├── session_tui.py               # 交互式 TUI: SessionTUIState, SessionTUIController,
│   │                                  SessionTUIRenderer, 跨平台按键输入
│   │
│   ├── session_cli.py               # argparse CLI: 12 个子命令
│   │
│   ├── config.py                    # MemoryConfig 数据类, config.json 读写,
│   │                                  环境变量覆盖链 (CLI > env > config > default)
│   │
│   ├── logging_utils.py             # Rotating 文件日志，脱敏（不记录完整对话）
│   ├── workspace_manager.py         # 项目级 workspace 隔离
│   ├── memory_stats.py              # 记忆库统计
│   ├── version.py                   # 版本信息 + 能力状态
│   ├── health_check.py              # 系统健康检查
│   ├── install.py / uninstall.py    # 安装管理
│   ├── upgrade.py                   # Legacy → workspace 迁移
│   ├── release_prepare.py           # 发布前清理
│   ├── run_acceptance.py            # 验收测试
│   ├── turn_counter.py              # 轮次自动保存计数器
│   ├── auto_save_memory.py          # 自动保存编排器
│   └── summarize_session.py         # CLI: 从 --text 或 --file 保存记忆
│       retrieve_memory.py           # CLI: 按 --query 检索记忆
│       update_index.py              # CLI: 从 Markdown 重建 index.json
│
├── commands/                        # Slash Command 处理器 (v0.6.0)
│   ├── base.py                      # Command + CommandResult 数据结构
│   ├── registry.py                  # CommandRegistry: 注册/查找/分发/编辑距离建议
│   ├── memory_save.py               # /memory save handler（会话感知）
│   ├── memory_retrieve.py           # /memory retrieve handler（会话+链接感知）
│   ├── memory_rebuild.py            # /memory rebuild handler
│   ├── memory_manage.py             # /memory manage handler
│   ├── memory_session.py            # /memory session handler（12 动作）
│   ├── memory-save.md               # Slash Command 声明（YAML frontmatter）
│   ├── memory-retrieve.md           # Slash Command 声明
│   ├── memory-rebuild.md            # Slash Command 声明
│   └── session.md                   # Slash Command 声明
│
├── hooks/                           # 跨平台 Hook 脚本 (bash/bat/ps1)
├── .claude-plugin/                  # Claude Code 插件元数据
│   ├── plugin.json                  # Manifest
│   └── marketplace.json             # 自建市场条目
│
├── memory/                          # 存储（gitignore 排除）
│   ├── index.json                   # 主主题索引
│   └── .memory/sessions/            # 会话工作区 (v0.7.0)
│
├── docs/                            # 文档（12 份）
│   ├── SESSION_WORKSPACE.md         # 会话工作区完整指南
│   ├── SMOKE_TEST.md                # 真实 API Provider 手动验证
│   └── releases/                    # 版本发布摘要
│
├── tests/                           # 352 项测试，零失败
│   ├── test_memory_skill.py         # v0.6.0 核心: 153 项
│   ├── test_session_manager.py      # Phase 1: 52 项
│   ├── test_session_commands.py     # Phase 2: 38 项
│   ├── test_memory_session_integration.py # Phase 3: 33 项
│   ├── test_linked_session_retrieval.py   # Phase 4: 29 项
│   └── test_session_tui.py          # Phase 5: 47 项
│
├── SKILL.md / CHANGELOG.md / LICENSE
└── README.md / README.zh-CN.md
```

---

## 配置参考

**优先级链**：CLI 参数 > 环境变量 > `config.json` > 内置默认值

### 核心设置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CLAUDE_MEMORY_WORKSPACE` | `""` | 项目隔离的 workspace 名称 |
| `CLAUDE_MEMORY_DIR` | `memory` | 记忆存储根目录 |
| `MEMORY_AUTO_SAVE_INTERVAL` | `10` | 每 N 轮自动保存（0=禁用） |
| `CLAUDE_MEMORY_LOG_LEVEL` | `INFO` | 日志级别 |

### 检索设置 (v0.6.0)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CLAUDE_MEMORY_RETRIEVAL_MODE` | `hybrid` | 默认模式: keyword / semantic / hybrid |

### Embedding Provider (v0.6.0)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `EMBEDDING_API_KEY` | `""` | OpenAI-compatible API key（不设=FakeProvider） |
| `EMBEDDING_API_BASE` | `https://api.openai.com/v1` | API 基础 URL |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 模型名 |

### LLM Provider (v0.6.0)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LLM_API_KEY` | `""` | OpenAI-compatible API key（不设=FakeProvider） |
| `LLM_API_BASE` | `https://api.openai.com/v1` | API 基础 URL |
| `LLM_MODEL` | `gpt-4o-mini` | 模型名 |

### 会话设置 (v0.7.0)

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SESSION_ENABLED` | `true` | 启用会话工作区 |
| `SESSION_ROOT` | `.memory/sessions` | 会话目录根路径 |

---

## 测试

```bash
# 全部测试 (352 项, 0 失败)
python -m pytest -q

# 按阶段
python -m pytest tests/test_memory_skill.py -v            # v0.6.0 核心: 153 项
python -m pytest tests/test_session_manager.py -v          # Phase 1: 52 项
python -m pytest tests/test_session_commands.py -v         # Phase 2: 38 项
python -m pytest tests/test_memory_session_integration.py -v # Phase 3: 33 项
python -m pytest tests/test_linked_session_retrieval.py -v   # Phase 4: 29 项
python -m pytest tests/test_session_tui.py -v              # Phase 5: 47 项

# 按功能
python -m pytest -v -k "Embedding or Semantic or HybridMode"  # 检索
python -m pytest -v -k "LLM or Summarizer"                    # 摘要
python -m pytest -v -k "Command"                              # 命令
python -m pytest -v -k "Lifecycle or Dedup or Quality"        # 生命周期
python -m pytest -v -k "Session"                              # 会话

# 验收测试
python scripts/run_acceptance.py --quick
```

---

## 已知限制

- **插件运行时**：`.claude-plugin/plugin.json` 尚未经过 Claude Code 实时插件运行时验证。结构正确但生产加载未测试。
- **API 测试**：Embedding/LLM Provider 使用确定性 `FakeProvider` 做 CI 测试。真实 API 行为记录在 `docs/SMOKE_TEST.md` 供手动验证。
- **存储模型**：本地文件存储（Markdown + JSON + JSONL）。不支持多用户并发。适合单用户本地使用。
- **TUI 覆盖**：控制器和渲染器已完全单元测试。实际终端渲染和按键输入不在 CI 中，依赖终端能力检测。
- **无自动推荐**：会话需要手动链接。系统不会基于内容相似度自动推荐相关会话。

---

## 安全与隐私

- **本地优先**：所有记忆存于磁盘。除非显式配置远程 API Provider，否则数据不离开本机。
- **API Key 仅环境变量**：`EMBEDDING_API_KEY` 和 `LLM_API_KEY` 仅从环境变量读取。绝不写入配置文件、日志或提交 git。
- **日志脱敏**：日志系统截断内容、剥离路径。绝不记录完整对话原文。
- **路径穿越防护**：`_validate_file_path()` 拒绝含 `..` 或绝对路径的索引条目。
- **原子写入**：`index.json`、`manifest.json`、`links.json` 均使用临时文件 + `os.replace()` 实现崩溃安全写入。

---

## 仓库

GitHub: [`Junhaozhang-127/ClaudeCodeMemorySkill`](https://github.com/Junhaozhang-127/ClaudeCodeMemorySkill)（显示名称 `ClaudeMeory` 为历史原因）。

## License

MIT — 详见 [`LICENSE`](LICENSE)
