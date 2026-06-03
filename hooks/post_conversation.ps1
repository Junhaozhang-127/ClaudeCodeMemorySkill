# ============================================================================
# Claude Code Memory Skill — 会话后写入记忆 Hook (PowerShell)
#
# 用法：
#   .\hooks\post_conversation.ps1 -Topic "主题" -File "C:\path\to\conversation.txt"
# ============================================================================
param(
    [string]$Topic = "",
    [string]$File = "",
    [string]$Text = ""
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

if (-not $Topic -and $env:CLAUDE_CONVERSATION_TITLE) {
    $Topic = $env:CLAUDE_CONVERSATION_TITLE
}
if (-not $Topic) {
    $Topic = "未命名对话 $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}

$PythonBin = if (Get-Command python3 -ErrorAction SilentlyContinue) { "python3" } else { "python" }

Set-Location $ProjectDir

if ($Text) {
    & $PythonBin scripts/summarize_session.py --topic $Topic --text $Text
}
elseif ($env:CLAUDE_CONVERSATION_CONTENT) {
    $TempFile = Join-Path $env:TEMP "claude_memory_hook.txt"
    $env:CLAUDE_CONVERSATION_CONTENT | Out-File -FilePath $TempFile -Encoding UTF8
    & $PythonBin scripts/summarize_session.py --topic $Topic --file $TempFile
    Remove-Item $TempFile -ErrorAction SilentlyContinue
}
elseif ($File -and (Test-Path $File)) {
    & $PythonBin scripts/summarize_session.py --topic $Topic --file $File
}
else {
    Write-Error "[Memory Hook] 无对话内容可保存"
    exit 1
}

Write-Host "[Memory Hook] 记忆保存完成：$Topic"
