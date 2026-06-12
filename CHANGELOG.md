# Changelog

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
