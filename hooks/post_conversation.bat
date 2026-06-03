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

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.." 2>nul || exit /b 1

set "TOPIC=%~1"
if "%TOPIC%"=="" if defined CLAUDE_CONVERSATION_TITLE set "TOPIC=%CLAUDE_CONVERSATION_TITLE%"
if "%TOPIC%"=="" set "TOPIC=Untitled"

set "CONV_FILE=%~2"

if not "%CONV_FILE%"=="" if exist "%CONV_FILE%" (
    python scripts\summarize_session.py --topic "%TOPIC%" --file "%CONV_FILE%"
    exit /b %errorlevel%
)

echo [Memory Hook] Usage: post_conversation.bat "Topic" "C:\path\to\file.txt"
echo [Memory Hook] Or set CLAUDE_CONVERSATION_TITLE and provide a file path.
exit /b 1
