# ============================================================================
# Claude Code Memory Skill — 用户输入前检索记忆 Hook (PowerShell)
#
# 用法：
#   .\hooks\pre_prompt.ps1 -Query "用户当前问题"
# ============================================================================
param(
    [string]$Query = ""
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

if (-not $Query -and $env:CLAUDE_USER_INPUT) {
    $Query = $env:CLAUDE_USER_INPUT
}
if (-not $Query) {
    exit 0
}

$PythonBin = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }

Set-Location $ProjectDir

& $PythonBin scripts/retrieve_memory.py --query $Query --top-k 5

Write-Host ""
Write-Host "[Memory Hook] 检索完成。以上上下文将注入 Claude Code。"
