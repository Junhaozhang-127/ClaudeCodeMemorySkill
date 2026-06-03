# Release Checklist for v0.5.0

## 1. Version Consistency
- [x] plugin.json version is 0.5.0
- [x] version.py is 0.5.0
- [x] CHANGELOG.md contains v0.5.0
- [x] README.md mentions v0.5.0 correctly

## 2. Repository Hygiene
- [x] .gitignore excludes virtual environments
- [x] .gitignore excludes Python caches
- [x] .gitignore excludes temporary memory files
- [x] No secrets or tokens are committed
- [x] No large generated artifacts are committed

## 3. Core Functionality
- [x] Can save a memory entry
- [x] Can update index.json
- [x] Can retrieve relevant memory
- [x] Can work with workspace isolation
- [x] Can handle empty memory library
- [x] Can handle missing index.json
- [x] Can handle corrupted index.json gracefully

## 4. Hook Integration
- [x] Stop hook can call memory save flow
- [x] PrePrompt hook can call memory retrieval flow
- [x] Bash hook tested
- [x] CMD hook tested
- [x] PowerShell hook tested

## 5. CLI Tools
- [x] install.py works
- [x] uninstall.py works
- [x] upgrade.py works
- [x] health_check.py reports status
- [x] memory_stats.py reports memory status
- [x] release_prepare.py works
- [x] run_acceptance.py works

## 6. Tests
- [x] Unit tests pass (78/78)
- [x] Acceptance tests pass (7/7)
- [x] Quick acceptance mode passes
- [x] No unexpected warnings

## 7. Documentation
- [x] README.md is accurate
- [x] SKILL.md is accurate
- [x] HOOK_SETUP.md is accurate
- [x] CAPABILITY_MATRIX.md is accurate
- [x] LIMITATIONS.md exists
- [x] FAQ.md exists

## 8. Known Limitations
- [x] plugin.json is clearly marked as manifest-template
- [x] EmbeddingRetriever stub is documented
- [x] Slash command mapping limitation is documented

## Release Notes Draft

Claude Code Memory Skill v0.5.0 — Release Candidate:

- 结构化会话记忆保存（摘要、关键决策、待办事项自动抽取）
- 多信号混合检索 + score_breakdown 可解释评分
- Workspace 项目隔离，支持环境变量和 CLI 参数
- bash/bat/ps1 Hook 脚本，会话结束自动保存 + 新会话自动检索
- 记忆维护工具：去重、合并、压缩、归档（全 dry-run 保护）
- install/uninstall/upgrade/health_check/release_prepare 配套工具
- 78 项单元测试 + 7 项验收测试全部通过
- 纯本地 Markdown + JSON 存储，零网络依赖
