# Hook 配置指南

## Hook 机制在本项目中的作用

Claude Code 支持通过 Hook 在特定事件（会话开始、结束、工具调用前后等）触发自定义脚本。本项目利用 Hook 实现两个关键自动化：

1. **会话后写入**：在会话结束或阶段性完成时，自动将对话内容保存为 Markdown 记忆
2. **用户输入前检索**：在用户提出新问题前，自动检索相关历史记忆并注入上下文

## Hook 脚本说明

### post_conversation_example.sh — 会话后写入

**用途**：接收对话主题和对话文本文件路径，调用 `summarize_session.py` 保存记忆。

**参数**：
- `$1`：对话主题（必填）
- `$2`：对话文本文件路径（必填）

**手动调用示例**：

```bash
# Git Bash / Linux / macOS
bash hooks/post_conversation_example.sh "AI 记忆系统设计" /tmp/conversation.txt

# 先将会话内容写入文件，再触发保存
echo "本轮讨论了记忆系统的架构设计..." > /tmp/conversation.txt
bash hooks/post_conversation_example.sh "记忆系统架构" /tmp/conversation.txt
```

### pre_prompt_example.sh — 用户输入前检索

**用途**：接收用户当前输入的查询文本，调用 `retrieve_memory.py` 检索相关记忆。

**参数**：
- `$1`：用户查询文本（必填）

**手动调用示例**：

```bash
bash hooks/pre_prompt_example.sh "如何实现会话记忆持久化"
bash hooks/pre_prompt_example.sh "Claude Code Hook 配置方法"
```

## Windows PowerShell 环境注意事项

在 PowerShell 中运行 Shell 脚本时需要注意：

1. **脚本解释器**：`.sh` 文件默认不与 PowerShell 关联。使用 Git Bash 或 WSL 执行：

   ```powershell
   # 使用 Git Bash
   & "C:\Program Files\Git\bin\bash.exe" hooks/post_conversation_example.sh "主题" "文件路径"

   # 或使用 WSL
   wsl bash hooks/post_conversation_example.sh "主题" "文件路径"
   ```

2. **Python 路径**：确保 `python` 命令在 Git Bash / WSL 的 PATH 中可用。

3. **路径分隔符**：Hook 脚本使用正斜杠 `/`，在 Git Bash 和 WSL 中正常工作。避免在脚本中使用反斜杠 `\`。

4. **中文参数**：如果主题包含中文，确保终端编码为 UTF-8：

   ```powershell
   chcp 65001
   ```

5. **直接调用 Python**（绕过 Shell 脚本）：

   ```powershell
   python scripts/summarize_session.py --topic "主题" --text "内容"
   python scripts/retrieve_memory.py --query "查询"
   ```

## Git Bash / WSL 环境注意事项

1. **编码**：Git Bash 和 WSL 默认使用 UTF-8，中文参数通常正常。

2. **路径**：项目路径中的空格需要转义或使用引号：

   ```bash
   bash hooks/post_conversation_example.sh "主题" "/c/Users/me/My Documents/conversation.txt"
   ```

3. **Python 命令**：某些环境中 `python` 可能指向 Python 2.x，使用 `python3` 替代：

   ```bash
   # 如果 python 不可用，修改脚本或手动执行
   python3 scripts/summarize_session.py --topic "测试" --text "内容"
   ```

## Claude Code settings.json 配置示例模板

> **重要提示**：以下为示例模板。Claude Code Hook 的具体事件名称、环境变量和输入格式可能因版本而异。请参考你使用的 Claude Code 版本的官方 Hook 文档，按实际规范调整以下配置。

### 基本模板

```jsonc
{
  "hooks": {
    // ===== 会话后写入记忆 =====
    // 事件名（如 PostConversation / Stop / SessionEnd）请按实际 Hook 规范填写
    "<HookEventName>": [
      {
        // 匹配条件：可选，仅在特定条件下触发
        // "matcher": "",
        "command": "bash ${CLAUDE_PROJECT_DIR}/hooks/post_conversation_example.sh"
      }
    ],

    // ===== 用户输入前检索记忆 =====
    // 事件名（如 PrePrompt / PreUserInput / BeforeConversation）请按实际 Hook 规范填写
    "<HookEventName>": [
      {
        "command": "bash ${CLAUDE_PROJECT_DIR}/hooks/pre_prompt_example.sh"
      }
    ]
  }
}
```

### 字段说明

| 字段 | 说明 | 需确认项 |
|------|------|----------|
| `<HookEventName>` | Claude Code 中的 Hook 事件名称 | 请按实际事件名替换，如 `PostConversation`、`Stop`、`PrePrompt` 等 |
| `command` | 触发时执行的命令 | `bash` 路径、Python 路径、项目路径需按本机环境确认 |
| `matcher` | 可选的触发匹配条件 | 按需配置 |
| `${CLAUDE_PROJECT_DIR}` | 项目根目录变量名 | 按 Claude Code 实际提供的环境变量名替换 |

### 自定义环境变量

如果 Claude Code Hook 提供了会话相关环境变量，可在脚本中使用。以下为常见变量示例（请按实际 Hook 文档确认变量名）：

```bash
#!/usr/bin/env bash
# 使用 Claude Code Hook 环境变量的示例

TOPIC="${CLAUDE_CONVERSATION_TITLE:-未命名对话}"
CONTENT="${CLAUDE_CONVERSATION_CONTENT:-}"
QUERY="${CLAUDE_USER_INPUT:-}"

# ... 调用对应 Python 脚本
```

### 跨平台命令替代方案

如果 Shell 脚本在 Windows 上不可用，可在 settings.json 中直接调用 Python：

```jsonc
{
  "hooks": {
    "<HookEventName>": [
      {
        "command": "python ${CLAUDE_PROJECT_DIR}/scripts/summarize_session.py --topic \"${CLAUDE_CONVERSATION_TITLE}\" --text \"${CLAUDE_CONVERSATION_CONTENT}\""
      }
    ]
  }
}
```

## 验证 Hook 是否正常

1. **手动验证保存链路**：

   ```bash
   echo "测试对话内容" > /tmp/test_conversation.txt
   bash hooks/post_conversation_example.sh "Hook测试" /tmp/test_conversation.txt
   cat memory/index.json | python -m json.tool
   ```

2. **手动验证检索链路**：

   ```bash
   bash hooks/pre_prompt_example.sh "Hook测试"
   ```

3. **检查记忆文件**：

   ```bash
   ls -la memory/topics/
   ```

4. **运行完整测试**：

   ```bash
   python tests/test_memory_skill.py
   ```
