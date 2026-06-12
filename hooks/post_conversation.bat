@echo off
REM ============================================================================
REM Claude Code Memory Skill — Save conversation memory (Windows CMD)
REM
REM Usage:
REM   hooks\post_conversation.bat "Topic" "C:\path\to\conversation.txt"
REM
REM Environment variables (set by Claude Code):
REM   CLAUDE_CONVERSATION_TITLE   — fallback topic
REM ============================================================================
setlocal disabledelayedexpansion

REM ── Python detection (verify actual executability) ──────────
set "PYTHON_BIN="
python3 -c "import sys; print(sys.executable)" >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_BIN=python3"
) else (
    python -c "import sys; print(sys.executable)" >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_BIN=python"
    )
)
if "%PYTHON_BIN%"=="" (
    echo [Memory Hook] No usable Python interpreter found
    exit /b 1
)

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.." 2>nul || exit /b 1

set "TOPIC=%~1"
if "%TOPIC%"=="" if defined CLAUDE_CONVERSATION_TITLE set "TOPIC=%CLAUDE_CONVERSATION_TITLE%"
if "%TOPIC%"=="" set "TOPIC=Untitled"

set "CONV_FILE=%~2"

if not "%CONV_FILE%"=="" if exist "%CONV_FILE%" (
    "%PYTHON_BIN%" scripts\summarize_session.py --topic "%TOPIC%" --file "%CONV_FILE%"
    exit /b %errorlevel%
)

echo [Memory Hook] Usage: post_conversation.bat "Topic" "C:\path\to\file.txt"
echo [Memory Hook] Or set CLAUDE_CONVERSATION_TITLE and provide a file path.
exit /b 1
