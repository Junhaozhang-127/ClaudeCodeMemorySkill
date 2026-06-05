@echo off
REM ============================================================================
REM Claude Code Memory Skill — UserPromptSubmit Hook：轮次自动保存 (Windows)
REM
REM 每 N 轮对话自动保存一次记忆（默认 N=10）。
REM ============================================================================
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM ── Python 解释器检测 ────────────────────────────────────────
set "PYTHON_BIN=python"
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    set "PYTHON_BIN=python3"
    where python3 >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo [AutoSave Hook] 找不到可用的 Python，跳过自动保存 >&2
        exit /b 0
    )
)

REM ── 读取 hook stdin ──────────────────────────────────────────
set "HOOK_INPUT="
for /f "usebackq delims=" %%i in (`findstr /r "^"`) do (
    set "HOOK_INPUT=!HOOK_INPUT!%%i"
)

if "%HOOK_INPUT%"=="" (
    echo [AutoSave Hook] stdin 为空，跳过自动保存 >&2
    exit /b 0
)

REM ── 调用 Python 自动保存脚本 ─────────────────────────────────
cd /d "%PROJECT_DIR%"
echo !HOOK_INPUT! | %PYTHON_BIN% scripts\auto_save_memory.py --stdin
