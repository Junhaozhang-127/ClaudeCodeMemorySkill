<#
.SYNOPSIS
    Claude Code Memory Skill — Save conversation memory (PowerShell)
.DESCRIPTION
    Called by Claude Code Hook (Stop event) to save the current conversation
    as a structured Markdown memory file and update index.json.
.PARAMETER Topic
    Conversation topic/title. Falls back to CLAUDE_CONVERSATION_TITLE env var.
.PARAMETER File
    Path to a text file containing conversation content.
.PARAMETER Text
    Conversation text passed directly on the command line.
.EXAMPLE
    .\hooks\post_conversation.ps1 -Topic "Architecture" -Text "We decided to..."
    .\hooks\post_conversation.ps1 -Topic "Bug Fix" -File "C:\temp\conv.txt"
#>

param(
    [string]$Topic = "",
    [string]$File = "",
    [string]$Text = ""
)

# ---- encoding setup (must come first) ----
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$PSDefaultParameterValues['*:Encoding'] = 'utf8'

# ---- resolve project root ----
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

# ---- determine topic ----
if ((-not $Topic) -and $env:CLAUDE_CONVERSATION_TITLE) {
    $Topic = $env:CLAUDE_CONVERSATION_TITLE
}
if (-not $Topic) {
    $Topic = "Untitled-" + (Get-Date -Format 'yyyyMMdd-HHmm')
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

# ---- navigate to project root ----
Push-Location $ProjectDir
try {
    if ($Text) {
        # pass text via stdin / temp file to avoid shell quoting issues with CJK
        $TempFile = [System.IO.Path]::GetTempFileName() + ".txt"
        try {
            [System.IO.File]::WriteAllText($TempFile, $Text, [System.Text.UTF8Encoding]::new($false))
            & $PythonBin scripts/summarize_session.py --topic $Topic --file $TempFile
        } finally {
            if (Test-Path $TempFile) { Remove-Item $TempFile -Force }
        }
    }
    elseif ($env:CLAUDE_CONVERSATION_CONTENT) {
        $TempFile = [System.IO.Path]::GetTempFileName() + ".txt"
        try {
            [System.IO.File]::WriteAllText($TempFile, $env:CLAUDE_CONVERSATION_CONTENT, [System.Text.UTF8Encoding]::new($false))
            & $PythonBin scripts/summarize_session.py --topic $Topic --file $TempFile
        } finally {
            if (Test-Path $TempFile) { Remove-Item $TempFile -Force }
        }
    }
    elseif ($File -and (Test-Path $File)) {
        & $PythonBin scripts/summarize_session.py --topic $Topic --file $File
    }
    else {
        Write-Error "[Memory Hook] No conversation content available"
        exit 1
    }
} finally {
    Pop-Location
}

Write-Host "[Memory Hook] Memory saved: $Topic"
