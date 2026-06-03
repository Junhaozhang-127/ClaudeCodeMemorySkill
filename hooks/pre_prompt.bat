@echo off
REM ============================================================================
REM Claude Code Memory Skill — 用户输入前检索记忆 Hook (Windows Batch)
REM
REM 用法：
REM   hooks\pre_prompt.bat "用户当前问题"
REM ============================================================================
setlocal enabledelayedexpansion

set QUERY=%~1

if "%QUERY%"=="" if not "%CLAUDE_USER_INPUT%"=="" set QUERY=%CLAUDE_USER_INPUT%
if "%QUERY%"=="" exit /b 0

REM 检测 Python
set PYTHON_BIN=python
where python3 >nul 2>&1 && set PYTHON_BIN=python3

cd /d "%~dp0.."

%PYTHON_BIN% scripts\retrieve_memory.py --query "%QUERY%" --top-k 5

echo.
echo [Memory Hook] 检索完成。以上上下文将注入 Claude Code。

endlocal
