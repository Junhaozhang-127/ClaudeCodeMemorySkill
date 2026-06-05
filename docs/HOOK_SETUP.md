# Hook 配置指南

## 概述

Claude Code Memory Skill 通过 Hook 在三个关键时机自动触发：

1. **会话结束 (Stop)** → 保存对话为 Markdown 记忆
2. **用户输入前 (UserPromptSubmit)** → 检索相关历史记忆注入上下文
3. **用户输入前 (UserPromptSubmit)** → 轮次计时器，每 N 轮自动保存（默认 10 轮）

## Hook 脚本清单

| 脚本 | 平台 | 用途 |
|------|------|------|
| `hooks/post_conversation.sh` | Linux / macOS / Git Bash | 会话后保存记忆 |
| `hooks/pre_prompt.sh` | Linux / macOS / Git Bash | 用户输入前检索 |
| `hooks/auto_save.sh` | Linux / macOS / Git Bash | 轮次自动保存 |
| `hooks/post_conversation.bat` | Windows CMD | 会话后保存记忆 |
| `hooks/pre_prompt.bat` | Windows CMD | 用户输入前检索 |
| `hooks/auto_save.bat` | Windows CMD | 轮次自动保存 |
| `hooks/post_conversation.ps1` | PowerShell | 会话后保存记忆 |
| `hooks/pre_prompt.ps1` | PowerShell | 用户输入前检索 |
| `hooks/auto_save.ps1` | PowerShell | 轮次自动保存 |

## 快速配置

将 `docs/settings.template.json` 中的 Hook 配置合并到 Claude Code 的 `settings.json`：

### Linux / macOS / Git Bash

```jsonc
{
  "hooks": {
    "Stop": [
      {
        "command": "bash \"${CLAUDE_PROJECT_DIR}/hooks/post_conversation.sh\""
      }
    ],
    "PrePrompt": [
      {
        "command": "bash \"${CLAUDE_PROJECT_DIR}/hooks/pre_prompt.sh\" \"${CLAUDE_USER_INPUT}\""
      }
    ]
  }
}
```

### Windows CMD

```jsonc
{
  "hooks": {
    "Stop": [
      {
        "command": "cmd /c \"${CLAUDE_PROJECT_DIR}\\hooks\\post_conversation.bat\""
      }
    ],
    "PrePrompt": [
      {
        "command": "cmd /c \"${CLAUDE_PROJECT_DIR}\\hooks\\pre_prompt.bat\" \"${CLAUDE_USER_INPUT}\""
      }
    ]
  }
}
```

### PowerShell

```jsonc
{
  "hooks": {
    "Stop": [
      {
        "command": "powershell -ExecutionPolicy Bypass -File \"${CLAUDE_PROJECT_DIR}\\hooks\\post_conversation.ps1\""
      }
    ],
    "PrePrompt": [
      {
        "command": "powershell -ExecutionPolicy Bypass -File \"${CLAUDE_PROJECT_DIR}\\hooks\\pre_prompt.ps1\" -Query \"${CLAUDE_USER_INPUT}\""
      }
    ]
  }
}
```

### 跨平台（直接 Python）

```jsonc
{
  "hooks": {
    "Stop": [
      {
        "command": "python \"${CLAUDE_PROJECT_DIR}/scripts/summarize_session.py\" --topic \"${CLAUDE_CONVERSATION_TITLE}\" --text \"${CLAUDE_CONVERSATION_CONTENT}\""
      }
    ],
    "PrePrompt": [
      {
        "command": "python \"${CLAUDE_PROJECT_DIR}/scripts/retrieve_memory.py\" --query \"${CLAUDE_USER_INPUT}\" --top-k 5"
      }
    ]
  }
}
```

> **重要**: 事件名 (`Stop` / `PrePrompt`) 和环境变量名 (`${CLAUDE_USER_INPUT}` 等) 请根据你的 Claude Code 版本实际 Hook 规范调整。

## 自动保存间隔配置

轮次自动保存间隔可通过以下方式配置（优先级从高到低）：

1. **环境变量**：`MEMORY_AUTO_SAVE_INTERVAL=5`（设为 0 禁用）
2. **config.json**：`"auto_save_interval": 5`
3. **默认值**：10 轮

```bash
# 每 5 轮自动保存
export MEMORY_AUTO_SAVE_INTERVAL=5

# 禁用轮次自动保存（仅保留会话结束保存）
export MEMORY_AUTO_SAVE_INTERVAL=0
```

## 手动验证

```bash
# 保存测试
bash hooks/post_conversation.sh "Hook测试" --text "这是一条测试记忆。"
cat memory/index.json | python -m json.tool

# 检索测试
bash hooks/pre_prompt.sh "Hook测试"

# 自动保存测试（模拟 hook stdin JSON）
echo '{"session_id":"test-123","transcript_path":"'$HOME'/.claude/history.jsonl"}' | bash hooks/auto_save.sh

# 检查记忆文件
ls memory/topics/

# 查看轮次计数状态
cat memory/.turn_state.json
```

## 故障排查

| 问题 | 解决方案 |
|------|----------|
| Hook 未触发 | 确认 `settings.json` 中事件名正确，重启 Claude Code |
| `python: command not found` | 在 Hook 脚本中指定 Python 完整路径 |
| 中文乱码 | 设置 `PYTHONIOENCODING=utf-8` 环境变量 |
| PowerShell 执行策略阻止 | 添加 `-ExecutionPolicy Bypass` 参数 |

## 手动运行（不依赖 Hook）

Hook 不可用时，仍可通过 CLI 或 Slash Command 手动使用：

```bash
python scripts/summarize_session.py --topic "主题" --text "内容"
python scripts/retrieve_memory.py --query "查询"
python scripts/update_index.py
```
