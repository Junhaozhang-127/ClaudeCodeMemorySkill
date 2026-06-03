# 能力矩阵

| 能力 | 状态 | 依赖 | CLI 入口 | 文档 | 测试 |
|------|------|------|----------|------|------|
| **存储** |||||
| Markdown 记忆保存 | ✅ 已实现 | stdlib | `summarize_session.py` | README | ✅ |
| JSON 索引管理 | ✅ 已实现 | stdlib | `update_index.py` | README | ✅ |
| 原子写入 | ✅ 已实现 | stdlib | — | README | ✅ |
| 索引备份 | ✅ 已实现 | stdlib | — | SECURITY | ✅ |
| **摘要** |||||
| 规则摘要器 | ✅ 已实现 | stdlib | — | SUMMARIZER_DESIGN | ✅ |
| 关键决策抽取 | ✅ 已实现 | stdlib | — | SUMMARIZER_DESIGN | ✅ |
| 待办事项抽取 | ✅ 已实现 | stdlib | — | SUMMARIZER_DESIGN | ✅ |
| 可插拔架构 | ✅ 已实现 | stdlib | — | SUMMARIZER_DESIGN | ✅ |
| LLM 摘要器 | ⏳ 未来 | LLM API | — | SUMMARIZER_DESIGN | ❌ |
| **关键词** |||||
| 正则规则法 | ✅ 已实现 | stdlib | — | — | ✅ |
| jieba 分词增强 | ✅ 可选 | jieba | — | README | ✅ |
| 停用词过滤 | ✅ 已实现 | stdlib | — | — | ✅ |
| **检索** |||||
| 关键词检索 | ✅ 已实现 | stdlib | `retrieve_memory.py` | RETRIEVAL_DESIGN | ✅ |
| 混合检索 | ✅ 已实现 | stdlib | `retrieve_memory.py` | RETRIEVAL_DESIGN | ✅ |
| score_breakdown | ✅ 已实现 | stdlib | `--json` | RETRIEVAL_DESIGN | ✅ |
| 向量检索 | ❌ Stub | sentence-transformers | — | RETRIEVAL_DESIGN | ❌ |
| **Workspace** |||||
| 项目隔离 | ✅ 已实现 | stdlib | `--workspace` | WORKSPACE_GUIDE | ✅ |
| 环境变量解析 | ✅ 已实现 | stdlib | — | CONFIGURATION | ✅ |
| Legacy 兼容 | ✅ 已实现 | stdlib | — | — | ✅ |
| **维护** |||||
| 重复检测 | ✅ 已实现 | stdlib | `memory_maintenance.py` | MAINTENANCE | ✅ |
| 记忆合并 | ✅ 已实现 | stdlib | `memory_maintenance.py` | MAINTENANCE | ✅ |
| 主题压缩 | ✅ 已实现 | stdlib | `memory_maintenance.py` | MAINTENANCE | ✅ |
| 归档旧记忆 | ✅ 已实现 | stdlib | `memory_maintenance.py` | MAINTENANCE | ✅ |
| **安全** |||||
| 路径防遍历 | ✅ 已实现 | stdlib | — | SECURITY | ✅ |
| Markdown 转义 | ✅ 已实现 | stdlib | — | SECURITY | ✅ |
| 日志安全过滤 | ✅ 已实现 | stdlib | — | SECURITY | ✅ |
| 文件锁 | ✅ 已实现 | stdlib | — | SECURITY | ✅ |
| **生态接入** |||||
| Hook 脚本 (bash) | ✅ 已实现 | bash | `hooks/*.sh` | HOOK_SETUP | ✅ |
| Hook 脚本 (bat) | ✅ 已实现 | cmd | `hooks/*.bat` | HOOK_SETUP | ✅ |
| Hook 脚本 (ps1) | ✅ 已实现 | pwsh | `hooks/*.ps1` | HOOK_SETUP | ✅ |
| Slash Command | ⚠️ Manifest 声明 | — | SKILL.md | SKILL.md | — |
| Plugin Manifest | ⚠️ 模板 | — | `plugin.json` | README | ✅ |
| Plugin 官方认证 | ❌ 未验证 | — | — | — | — |
| **工具** |||||
| 安装 | ✅ 已实现 | stdlib | `install.py` | INSTALLATION | ✅ |
| 卸载 | ✅ 已实现 | stdlib | `uninstall.py` | INSTALLATION | ✅ |
| 升级/迁移 | ✅ 已实现 | stdlib | `upgrade.py` | INSTALLATION | ✅ |
| 健康检查 | ✅ 已实现 | stdlib | `health_check.py` | HEALTH_CHECK | ✅ |
| 记忆统计 | ✅ 已实现 | stdlib | `memory_stats.py` | — | ✅ |
| 发布清理 | ✅ 已实现 | stdlib | `release_prepare.py` | RELEASE_CHECKLIST | ✅ |
| 验收测试 | ✅ 已实现 | stdlib | `run_acceptance.py` | RELEASE_CHECKLIST | ✅ |
| 配置校验 | ✅ 已实现 | stdlib | `config.py` | CONFIGURATION | ✅ |

**状态说明**: ✅ 已实现 | ⚠️ 可选/stub | ❌ 未实现/stub | ⏳ 未来计划
