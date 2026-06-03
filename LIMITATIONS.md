# 已知限制 (Limitations)

本文档客观描述 Claude Code Memory Skill v0.5.0 的当前限制。这些不是缺陷，而是设计和演进阶段的边界。

## 1. Plugin Manifest 状态

`plugin.json` 是 **Manifest Template**，不代表已通过 Claude Code 官方插件运行时验证。使用前需按本机 Claude Code 版本调整 Hook 事件名称和环境变量。

## 2. Slash Command 实现方式

Slash Command（如 `/memory save`）当前通过 SKILL.md / plugin.json 中的声明式映射关联到 CLI 脚本。不是完整官方 commands 目录实现。

## 3. EmbeddingRetriever

`EmbeddingRetriever` 当前是 stub，调用时抛出 `NotImplementedError`。当前检索使用 `HybridRetriever`（关键词 + 多字段加权评分）。未来版本可对接 sentence-transformers 或 OpenAI Embeddings。

## 4. 检索方式

检索主要依赖：
- 关键词匹配（jieba + 正则回退）
- 多字段加权评分（主题、关键词、决策、待办、摘要）
- 时间衰减

不提供语义级别理解。

## 5. 存储

- 默认使用本地 Markdown + JSON 文件存储
- 不支持多用户并发数据库
- 高并发写入场景下 index.json 可能竞争（已实现简易文件锁）

## 6. 网络

- 不自动上传任何记忆到远程服务
- 不依赖外部 API（核心功能零网络依赖）
- jieba 为可选本地依赖

## 7. Hook 依赖

Hook 脚本的能力取决于用户本地 Claude Code 配置：
- 事件名称需按实际版本确认
- 环境变量名需按实际版本确认
- `docs/settings.template.json` 中的配置为模板

## 8. 跨平台差异

- Windows / macOS / Linux 下路径分隔符和 shell 行为可能不同
- PowerShell 执行策略可能阻止 `.ps1` 脚本
- Git Bash 环境下需确认 Python 在 PATH 中
