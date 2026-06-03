@echo off
REM ============================================================================
REM Claude Code Memory Skill — 会话后写入记忆 Hook (Windows Batch)
REM
REM 用法：
REM   hooks\post_conversation.bat "主题" "C:\path\to\conversation.txt"
REM ============================================================================
setlocal enabledelayedexpansion

set TOPIC=%~1
set CONVERSATION_FILE=%~2

if "%TOPIC%"=="" set TOPIC=未命名对话 %date% %time%

if not "%CLAUDE_CONVERSATION_TITLE%"=="" set TOPIC=%CLAUDE_CONVERSATION_TITLE%

REM 检测 Python
set PYTHON_BIN=python
where python3 >nul 2>&1 && set PYTHON_BIN=python3

cd /d "%~dp0.."

if not "%CONVERSATION_FILE%"=="" (
    %PYTHON_BIN% scripts\summarize_session.py --topic "%TOPIC%" --file "%CONVERSATION_FILE%"
) else if not "%CLAUDE_CONVERSATION_CONTENT%"=="" (
    echo %CLAUDE_CONVERSATION_CONTENT% > "%TEMP%\claude_memory_hook.txt"
    %PYTHON_BIN% scripts\summarize_session.py --topic "%TOPIC%" --file "%TEMP%\claude_memory_hook.txt"
    del "%TEMP%\claude_memory_hook.txt" 2>nul
) else (
    echo [Memory Hook] 无对话内容可保存
    exit /b 1
)

echo [Memory Hook] 记忆保存完成：%TOPIC%
endlocal
