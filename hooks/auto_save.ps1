# ============================================================================
# Claude Code Memory Skill — UserPromptSubmit Hook：轮次自动保存 (PowerShell)
#
# 每 N 轮对话自动保存一次记忆（默认 N=10）。
# ============================================================================

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# ── 读取 hook stdin JSON ─────────────────────────────────────
$HookInput = $input | Out-String

if ([string]::IsNullOrWhiteSpace($HookInput)) {
    Write-Error "[AutoSave Hook] stdin 为空，跳过自动保存"
    exit 0
}

# ── Python 解释器检测 ────────────────────────────────────────
$PythonBin = $null
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $PythonBin = "python"
} elseif (Get-Command "python3" -ErrorAction SilentlyContinue) {
    $PythonBin = "python3"
} else {
    Write-Error "[AutoSave Hook] 找不到可用的 Python，跳过自动保存"
    exit 0
}

# ── 调用 Python 自动保存脚本 ─────────────────────────────────
Set-Location $ProjectDir
$HookInput | & $PythonBin scripts/auto_save_memory.py --stdin
