# 常见问题 (FAQ)

## 1. ClaudeMeory 和 Claude Code Memory Skill 是什么关系？

`ClaudeMeory` 是 GitHub 仓库名（历史原因）。项目显示名称为 **Claude Code Memory Skill**。

## 2. 这个项目是不是官方 Claude Code Plugin？

不是。`plugin.json` 是 **manifest-template**（清单模板），未经过 Claude Code 官方插件运行时验证。项目的核心能力通过独立 CLI 脚本和 Hook 脚本实现。

## 3. 为什么使用 Markdown 和 JSON，而不是数据库？

- **人工可读**：任何编辑器都能直接打开、修改记忆文件
- **零依赖**：不需要安装任何数据库
- **Git 友好**：可以纳入版本控制
- **易迁移**：复制目录即可迁移到其他机器

## 4. 会不会把我的记忆上传到云端？

不会。所有记忆默认保存在本地磁盘，项目核心代码不发起任何网络请求。

## 5. 如何清理旧记忆？

```bash
# 预览 180 天前的旧记忆
python scripts/memory_maintenance.py archive-old --days 180 --dry-run

# 执行归档（移动非删除）
python scripts/memory_maintenance.py archive-old --days 180 --apply

# 检测并合并重复记忆
python scripts/memory_maintenance.py detect-duplicates
python scripts/memory_maintenance.py merge --topic "主题" --dry-run
```

## 6. 如何按 workspace 隔离项目记忆？

```bash
python scripts/workspace_manager.py init --workspace my-project
python scripts/summarize_session.py --workspace my-project --topic "..." --text "..."
python scripts/retrieve_memory.py --workspace my-project --query "..."
```

或通过环境变量：`export CLAUDE_MEMORY_WORKSPACE=my-project`

## 7. 为什么检索结果有时不够准确？

当前使用关键词 + 多字段加权评分，不是语义理解。准确率受限于：
- 关键词匹配精度
- jieba 是否安装（中文分词增强）
- 对话中是否有明确的术语和关键词

未来版本可接入向量检索提高召回率。

## 8. EmbeddingRetriever 是否已经可用？

不可用。`EmbeddingRetriever` 当前是 stub，调用时抛出 `NotImplementedError`。请使用默认的 `HybridRetriever`。

## 9. Windows 下 Hook 如何配置？

```bash
# Git Bash
bash hooks/post_conversation.sh "主题" --text "内容"
bash hooks/pre_prompt.sh "查询文本"

# CMD
hooks\post_conversation.bat "主题" "C:\path\to\file.txt"
hooks\pre_prompt.bat "查询文本"

# PowerShell
.\hooks\post_conversation.ps1 -Topic "主题" -Text "内容"
.\hooks\pre_prompt.ps1 -Query "查询文本"
```

详见 `docs/HOOK_SETUP.md`。

## 10. 如何确认安装成功？

```bash
# 健康检查
python scripts/health_check.py

# 验收测试
python scripts/run_acceptance.py --quick

# 手动验证
python scripts/summarize_session.py --topic "测试" --text "验证安装"
python scripts/retrieve_memory.py --query "测试"
```
