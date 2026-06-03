@echo off
REM ============================================================================
REM Claude Code Memory Skill — Retrieve memory context (Windows CMD)
REM
REM Usage:
REM   hooks\pre_prompt.bat "User's current input"
REM
REM Environment variables (set by Claude Code):
REM   CLAUDE_USER_INPUT — fallback query text
REM ============================================================================
setlocal disabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%.." 2>nul || exit /b 1

set "QUERY=%~1"
if "%QUERY%"=="" if defined CLAUDE_USER_INPUT set "QUERY=%CLAUDE_USER_INPUT%"
if "%QUERY%"=="" exit /b 0

python scripts\retrieve_memory.py --query "%QUERY%" --top-k 5
exit /b %errorlevel%
