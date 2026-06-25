# Changelog

## v0.7.0 — Session Workspace Manager (2026-06-25)

**新增**
- Session Workspace Core: `SessionManager` (create/list/use/rename/archive/delete/restore), `SessionManifest`, `SessionIndex`, `CurrentSession`, `SessionEvent`
- Session CLI (`scripts/session_cli.py`) + Slash Command (`/memory session`): 12 actions (list/create/current/use/rename/archive/delete/restore/info/link/unlink/links/tui)
- `memory_core` session-aware integration: `save_memory` auto-detects current session, `retrieve_memory` supports `session_id`/`all_sessions`/`include_linked_sessions`/`include_archived_sessions` filters
- Linked Session Retrieval: explicit `link_session`/`unlink_session`, `links.json` data model, `include_linked_sessions=True` retrieval scope
- Interactive Session TUI: `session_cli.py tui`, keyboard navigation (arrow keys/Enter/Delete/N/R/A/L), soft-delete confirmation, non-TTY fallback
- Session directory structure: `.memory/sessions/<id>/` with `manifest.json`, `memories.jsonl`, `links.json`, `events.jsonl`
- `MemoryRecord` extended with `session_id`/`session_title`

**向后兼容**
- Existing memories without `session_id` default to `"default"` session
- Existing `save_memory`/`retrieve_memory`/`format_context` signatures unchanged
- Existing v0.6.0 commands (save/retrieve/rebuild/manage) remain available
- `config.example.json` synchronized with new session config keys

**测试**
- 352 passed / 0 failed / 3 skipped (v0.6.0: 153 → v0.7.0: +199 tests across 5 phases)

---

## v0.6.0 — 语义检索 + LLM 摘要 + 命令系统升级 + 记忆生命周期 (2026-06-25)

**新增 (Task 1: EmbeddingRetriever)**
- `scripts/embedding_provider.py` — `EmbeddingProvider` ABC + `FakeEmbeddingProvider` (ngram-based) + `OpenAIEmbeddingProvider`
- `scripts/embedding_cache.py` — JSON-file-based embedding 缓存，支持模型切换自动失效
- `retrieval.SemanticRetriever` — 完整 embedding 语义检索实现（替代旧 stub）
- `HybridRetriever` 三种模式: `keyword` / `semantic` / `hybrid`
- Cosine similarity + 可配置降级: provider 不可用时自动 keyword fallback

**新增 (Task 2: LLM 摘要器)**
- `scripts/llm_provider.py` — `LLMProvider` ABC + `FakeLLMProvider` + `OpenAILLMProvider`
- `summarizers.LLMSummarizer` — 3 类摘要 (`brief` / `semantic` / `memory`), chunk-merge 长文本处理, 无 LLM 时 fallback 到 `RuleBasedSummarizer`
- `summarizers.EnhancedSummaryResult` — 含 entities, key_points, open_questions, metadata

**新增 (Task 3: Slash Command 升级)**
- `commands/base.py` — `Command` + `CommandResult` 数据结构
- `commands/registry.py` — `CommandRegistry` 注册/查找/分发, 编辑距离建议
- `commands/memory_save.py` — `/memory save` 命令处理器 (支持 rule/llm/auto 摘要模式)
- `commands/memory_retrieve.py` — `/memory retrieve` 命令处理器 (支持 keyword/semantic/hybrid 检索)
- `commands/memory_manage.py` — `/memory manage` 命令处理器 (quality/dedup/expire/merge/archive)

**新增 (Task 4: 记忆质量增强)**
- `scripts/memory_lifecycle.py` — 状态机 (active/archived/expired/merged/deleted), TTL 过期, 质量报告
- `MemoryRecord` 扩展字段: `status`, `content_hash`, `ttl_days`, `tags`, `access_count`, `merged_into` 等 15 个新字段
- `retrieve_memory()` 支持 `tags` 过滤 + `include_expired` 参数
- `generate_quality_report()` — 记忆质量报告含去重/过期/低质量检测 + 推荐动作

**配置增强**
- `config.MemoryConfig` 新增: `embedding_provider`, `llm_provider`, `retrieval_mode`, `summary_mode`, `default_ttl_days` 等
- `config.example.json` 新增所有新配置项

**测试**
- 59 项新增测试覆盖所有 4 项任务
- FakeProvider 确保测试无需网络/API key
- 145/148 测试通过 (3 预存失败: `plugin.json` 路径变更)

**向后兼容**
- 旧 `index.json` 记录兼容读取（缺失字段默认填充）
- `save_memory()`, `retrieve_memory()`, `format_context()` 签名向后兼容
- `EmbeddingRetriever` 别名兼容
- 降级: LLM/Embedding 不可用时自动 fallback 到规则实现

---

## v0.5.2 — 记忆更新与时间记录增强 (2026-06-12)

**新增**
- 记忆 Markdown 文件新增 `创建时间` 字段，与 `更新时间` 并列记录，方便追溯记忆生命周期
- 智能更新与合并：同一主题再次保存时，自动复用已有文件、合并 keywords/decisions/todos（去重）、保留原始 `created_at`、刷新 `updated_at`
- `rebuild_index` 增强：索引键改为基于主题名（而非文件名），同一主题的多日文件自动合并；支持从 Markdown blockquote 解析 `创建时间` / `更新时间`，回退到文件 stat
- 新增 `_merge_unique()` 合并辅助函数，`_parse_markdown_meta()` 元数据解析函数

**修复**
- `auto_save.sh` Hook 路径从相对路径 `../hooks/auto_save.sh` 改为绝对路径，与 `pre_prompt.sh`、`post_conversation.sh` 保持一致

**影响范围**: `scripts/memory_core.py`, `.claude-plugin/plugin.json`

---

## v0.5.1 — Hook 可靠性增强 (2026-06-12)

**修复**
- Hook 命令路径：`${CLAUDE_PROJECT_DIR}` → `${PLUGIN_DIR}`，确保插件安装在任意位置均可正确解析 Hook 脚本
- Python 解释器检测增强（所有 Hook 脚本）：不再仅检查 PATH 存在性（`command -v` / `Get-Command`），改为实际执行 `python -c "import sys; print(sys.executable)"` 验证解释器真实可用，防止 Windows Store 存根等假阳性
- Batch 脚本（`.bat`）新增 Python 检测逻辑，此前完全缺失

**影响范围**: `plugin.json`, `hooks/*.sh`, `hooks/*.ps1`, `hooks/*.bat`, `install.sh`

---

## Phase 5 (v0.5.0) — 发布前增强与长期可用性

**新增**
- 项目版本化 (`scripts/version.py`)
- 安装/卸载/升级脚本 (`install.py`, `uninstall.py`, `upgrade.py`)
- 健康检查工具 (`health_check.py`)
- 配置校验系统 (config.json 支持 + `config.py` 增强)
- 发布前清理工具 (`release_prepare.py`)
- 验收测试套件 (`run_acceptance.py`)
- 记忆统计命令 (`memory_stats.py`)
- 能力矩阵文档 (`docs/CAPABILITY_MATRIX.md`)
- 安装/配置/健康检查/发布清单文档

**已知限制**
- EmbeddingRetriever 为 stub，未实现实际向量检索
- Plugin manifest 为模板，未经 Claude Code 官方运行时验证

---

## Phase 4.1 — P1 修复

**修复**
- 环境变量 `CLAUDE_MEMORY_WORKSPACE` 在 CLI 中生效
- `EmbeddingRetriever` 明确抛出 `NotImplementedError`
- 中文 topic 维护命令匹配修复（slugify glob）
- 检索结果按 `id` 去重
- 文档准确性更新

---

## Phase 4 (v0.4.0) — 高级能力增强

**新增**
- Workspace 项目隔离 (`config.py`, `workspace_manager.py`)
- 混合检索架构 (`retrieval.py`: HybridRetriever + score_breakdown)
- 记忆维护命令 (`memory_maintenance.py`: dedup/merge/compact/archive)
- 日志系统 (`logging_utils.py`)
- 安全增强：路径防遍历、Markdown fence 转义、索引备份+锁

**已知限制**
- EmbeddingRetriever 为 stub
- 记忆合并基于关键词 Jaccard 相似度

---

## Phase 3 (v0.3.0) — Claude Code 生态接入

**新增**
- Production Hook 脚本 (bash/bat/ps1)
- Slash Command 声明 (`/memory save/retrieve/rebuild`)
- Plugin Manifest (`plugin.json`)
- 一键安装脚本 (`install.sh`)
- `settings.template.json` Hook 配置模板
- Phase 3.1: PowerShell/Batch Hook 稳定性修复

**修复**
- PowerShell Hook UTF-8 编码 + 参数传递
- Batch Hook 超时修复
- Slash Command 实现状态明确标注

---

## Phase 2 (v0.2.0) — 摘要与关键词增强

**新增**
- 可插拔摘要器 (`summarizers.py`: BaseSummarizer + RuleBasedSummarizer)
- 关键决策/待办事项自动抽取
- 中文关键词增强 (jieba + 停用词过滤 + 回退)
- 多字段加权检索评分
- `format_context` 优先级输出
- `index.json` decisions/todos 元数据扩展

**修复**
- P1: 触发词 `\b` 边界修复
- P1: CLI subprocess 测试隔离

---

## Phase 1 (v0.1.0) — 工程化完善

**新增**
- Markdown 本地记忆库 + `index.json` 索引
- 核心接口: `save_memory`, `retrieve_memory`, `rebuild_index`, `format_context`
- 原子写入 + 索引备份
- `.gitignore`, `README.md`, `SKILL.md`, `HOOK_SETUP.md`
- 单元测试 + CLI 验证
- 测试隔离 (temp dir)

**修复**
- `rebuild_index()` 跳过 README.md
- 索引原子写入安全
- Python 3.7 兼容 (`missing_ok`)
- Windows UTF-8 stdout
