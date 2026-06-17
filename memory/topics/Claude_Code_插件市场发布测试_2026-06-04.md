# Claude Code 插件市场发布测试

> 更新时间：2026-06-04 09:42:43

## 摘要

用户询问如何将记忆 Skill 发布到 Claude Code 插件市场。经过搜索发现三种路径：官方市场（面向企业）、社区合集（PR提交）、自建市场（最适合个人开发者）。最终采用自建市场方案，将 plugin.json 移入 .claude-plugin/ 目录，创建 marketplace.json，通过 claude plugin validate 验证通过，提交推送后通过 /plugin marketplace add 安装。插件现已成功安装并启用。

## 关键词

Claude, Code, 插件市场发布测试, Skill, plugin, json, claude-plugin, marketplace, claude, validate

## 关键决策

- 最终采用自建市场方案，将 plugin.json 移入 .claude-plugin/ 目录，创建 marketplace.json，通过 claude plugin validate 验证通过，提交推送后通过 /plugin market…

## 待办事项

- 最终采用自建市场方案，将 plugin.json 移入 .claude-plugin/ 目录，创建 marketplace.json，通过 claude plugin validate 验证通过，提交推送后通过 /plugin marketplace add 安装

## 原始对话摘录

````text
用户询问如何将记忆 Skill 发布到 Claude Code 插件市场。经过搜索发现三种路径：官方市场（面向企业）、社区合集（PR提交）、自建市场（最适合个人开发者）。最终采用自建市场方案，将 plugin.json 移入 .claude-plugin/ 目录，创建 marketplace.json，通过 claude plugin validate 验证通过，提交推送后通过 /plugin marketplace add 安装。插件现已成功安装并启用。
````

---

