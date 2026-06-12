<#
.SYNOPSIS
    Claude Code Memory Skill — Retrieve memory context (PowerShell)
.DESCRIPTION
    Called by Claude Code Hook (PrePrompt event) to search for relevant
    historical memories and output them as injectable context.
.PARAMETER Query
    User's current input text. Falls back to CLAUDE_USER_INPUT env var.
.EXAMPLE
    .\hooks\pre_prompt.ps1 -Query "How to save session memory?"
#>

param(
    [string]$Query = ""
)

# ---- encoding setup (must come first) ----
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

# ---- resolve project root ----
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# ---- determine query ----
if ((-not $Query) -and $env:CLAUDE_USER_INPUT) {
    $Query = $env:CLAUDE_USER_INPUT
}
if (-not $Query) {
    exit 0
}

# ---- detect Python (verify actual executability, not just PATH existence) ----
$PythonBin = $null
foreach ($candidate in @("python3", "python")) {
    $found = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($found) {
        try {
            $null = & $candidate -c "import sys; print(sys.executable)" 2>&1
            if ($LASTEXITCODE -eq 0) {
                $PythonBin = $candidate
                break
            }
        } catch {
            continue
        }
    }
}
if (-not $PythonBin) {
    Write-Error "[Memory Hook] Python not found in PATH"
    exit 1
}

# ---- run retrieval ----
Push-Location $ProjectDir
try {
    & $PythonBin scripts/retrieve_memory.py --query $Query --top-k 5
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "[Memory Hook] Retrieval complete. Context above will be injected."
