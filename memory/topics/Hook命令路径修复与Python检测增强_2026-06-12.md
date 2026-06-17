# Hook命令路径修复与Python检测增强

> 更新时间：2026-06-12 16:20:56

## 摘要

[user] 要求两项修改：1. hook 命令应使用绝对路径或支持 ${PLUGIN_DIR} 变量 2。Python 解释器检测应验证实际可执行性，而非仅检查路径存在 [assistant] 分析现有代码，发现 plugin.json 使用 ${CLAUDE_PROJECT_DIR} 指向 hook 脚本，所有 hook 脚本（sh/ps1/bat）的 Python 检测仅用 command -v / Get-Command 检查 PATH 存在性，batch 脚本甚至完全没有检测。[assistant] 修改了 8 个文件： - .claude-plugin/plugin.json：hook 路径改用 ${PLUGIN_DIR}（后因 Claude Code 不支持此变量而回退为绝对路径） - hooks/pre_prompt.sh、post_conversation.sh：Python 检测改为循环 python3→python，运行 python -c "import sys。print(sys.executable)" 验证实际可执行性 - hooks/pre_prompt…

## 关键词

Hook命令路径修复与Python检测增强, user, hook, PLUGIN_DIR, Python, assistant, plugin, json, CLAUDE_PROJECT_DIR, ps1

## 关键决策

- [assistant] 修改了 8 个文件： - .claude-plugin/plugin.json：hook 路径改用 ${PLUGIN_DIR}（后因 Claude Code 不支持此变量而回退为绝对路径） - hooks/pre_p…
- print(sys.executable)" 验证实际可执行性 - hooks/pre_prompt.ps1、post_conversation.ps1：Get-Command 后新增 try/catch 执行 python -c 并通过…
- 关键发现：Claude Code hook 命令中 ${PLUGIN_DIR} 不被支持，绝对路径是唯一可行方案

## 待办事项

- Python 解释器检测应验证实际可执行性，而非仅检查路径存在 [assistant] 分析现有代码，发现 plugin.json 使用 ${CLAUDE_PROJECT_DIR} 指向 hook 脚本，所有 hook 脚本（sh/ps1/bat）的 Python 检测仅用 command -v /…
- 立即修复回退为绝对路径 D:/SmartManufacturingWorkshop/program/Skill/ClaudeMeory/hooks/...，再次提交推送

## 原始对话摘录

````text
[user] 要求两项修改：1. hook 命令应使用绝对路径或支持 ${PLUGIN_DIR} 变量 2. Python 解释器检测应验证实际可执行性，而非仅检查路径存在

[assistant] 分析现有代码，发现 plugin.json 使用 ${CLAUDE_PROJECT_DIR} 指向 hook 脚本，所有 hook 脚本（sh/ps1/bat）的 Python 检测仅用 command -v / Get-Command 检查 PATH 存在性，batch 脚本甚至完全没有检测。

[assistant] 修改了 8 个文件：
- .claude-plugin/plugin.json：hook 路径改用 ${PLUGIN_DIR}（后因 Claude Code 不支持此变量而回退为绝对路径）
- hooks/pre_prompt.sh、post_conversation.sh：Python 检测改为循环 python3→python，运行 python -c "import sys; print(sys.executable)" 验证实际可执行性
- hooks/pre_prompt.ps1、post_conversation.ps1：Get-Command 后新增 try/catch 执行 python -c 并通过 $LASTEXITCODE 验证
- hooks/pre_prompt.bat、post_conversation.bat：新增完整的 Python 检测逻辑（此前完全缺失）
- install.sh：同样改为实际执行验证
- CHANGELOG.md：新增 v0.5.1 更新记录

[assistant] 提交并推送后，Stop hook 报错：bash: /hooks/post_conversation.sh: No such file or directory — ${PLUGIN_DIR} 展开为空字符串，Claude Code 不支持此变量。立即修复回退为绝对路径 D:/SmartManufacturingWorkshop/program/Skill/ClaudeMeory/hooks/...，再次提交推送。

关键发现：Claude Code hook 命令中 ${PLUGIN_DIR} 不被支持，绝对路径是唯一可行方案。Python 检测增强部分工作正常。
````

---

