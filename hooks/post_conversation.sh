#!/usr/bin/env bash
# ============================================================================
# Claude Code Memory Skill — Stop Hook：会话结束后自动保存记忆
#
# Claude Code Stop hook 通过 stdin 传入 JSON：
#   {"session_id":"...", "transcript_path":"~/.claude/...", "stop_hook_active":false}
#
# 本脚本读取 transcript JSONL，提取对话内容并调用 summarize_session.py 保存。
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── 读取 hook stdin JSON ─────────────────────────────────────
HOOK_INPUT="$(cat 2>/dev/null || true)"

if [ -z "$HOOK_INPUT" ]; then
    echo "[Memory Hook] stdin 为空，跳过保存" >&2
    exit 0
fi

# ── Python 解释器检测 ────────────────────────────────────────
PYTHON_BIN="python"
if ! command -v "$PYTHON_BIN" &>/dev/null || ! "$PYTHON_BIN" --version &>/dev/null; then
    PYTHON_BIN="python3"
fi
if ! command -v "$PYTHON_BIN" &>/dev/null || ! "$PYTHON_BIN" --version &>/dev/null; then
    echo "[Memory Hook] 找不到可用的 Python，跳过保存" >&2
    exit 0
fi

# ── 将 stdin JSON 写入临时文件（避免 shell 变量中特殊字符问题）──
HOOK_TMPFILE="/tmp/claude_memory_hook_$$.json"
echo "$HOOK_INPUT" > "$HOOK_TMPFILE"

cd "$PROJECT_DIR"

# ── 用 Python 解析 transcript + 保存记忆 ─────────────────────
"$PYTHON_BIN" - "$HOOK_TMPFILE" <<'PYEOF'
import json, os, sys, tempfile, subprocess
from pathlib import Path

hook_tmpfile = sys.argv[1]

try:
    with open(hook_tmpfile, "r", encoding="utf-8") as f:
        hook_data = json.load(f)
except Exception:
    print("[Memory Hook] 无法解析 hook stdin JSON，跳过保存", file=sys.stderr)
    sys.exit(0)

transcript_path = hook_data.get("transcript_path", "")
if transcript_path:
    transcript_path = os.path.expanduser(transcript_path)

# 如果 transcript_path 不存在，尝试从 history.jsonl 读取
if not transcript_path or not os.path.isfile(transcript_path):
    history_path = os.path.expanduser("~/.claude/history.jsonl")
    if os.path.isfile(history_path):
        transcript_path = history_path
    else:
        print("[Memory Hook] 找不到 transcript 文件，跳过保存", file=sys.stderr)
        sys.exit(0)

# ── 解析 JSONL transcript ──────────────────────────────────
#    支持两种格式：
#    A) 会话 JSONL: {"type":"user","message":{"role":"user","content":"..."}}
#    B) history.jsonl: {"display":"...","sessionId":"..."}
session_id = hook_data.get("session_id", "")
lines = []
topic = ""
is_history_format = False

try:
    with open(transcript_path, "r", encoding="utf-8") as f:
        all_lines = f.readlines()

    # 检测格式：看第一行有效 JSON
    for raw in all_lines:
        try:
            test = json.loads(raw.strip())
            if "sessionId" in test and "display" in test and "type" not in test:
                is_history_format = True
            break
        except Exception:
            continue

    for raw in all_lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue

        role = ""
        content = ""

        if is_history_format:
            # 格式 B: history.jsonl — 按 session_id 过滤
            if session_id and msg.get("sessionId") != session_id:
                continue
            role = "user"
            content = msg.get("display", "")
        else:
            # 格式 A: 会话 JSONL — 只提取 user/assistant 消息
            msg_type = msg.get("type", "")
            if msg_type not in ("user", "assistant"):
                continue
            inner = msg.get("message", {})
            role = inner.get("role", msg_type)
            content = inner.get("content", "")

        if not content:
            continue

        # 展平 content（可能是列表：[{"type":"text","text":"..."}, ...]）
        if isinstance(content, list):
            parts = []
            for c in content:
                if isinstance(c, dict):
                    # 提取 text 类型，跳过 thinking / tool_use 等
                    if c.get("type") == "text":
                        parts.append(c.get("text", ""))
            content = " ".join(parts)
            if not content:
                continue

        if isinstance(content, str):
            content = content.strip()
            if content:
                label = role if role else "user"
                lines.append(f"[{label}] {content}")
                if not topic and role == "user":
                    topic = content[:80]

    # 兜底 topic
    if not topic or topic.startswith("[Pasted text"):
        if is_history_format:
            topic = session_id[:50] if session_id else "未命名对话"
        else:
            topic = session_id[:50] if session_id else "未命名对话"
except Exception as e:
    print(f"[Memory Hook] 读取 transcript 失败: {e}", file=sys.stderr)
    sys.exit(0)

if not lines:
    print("[Memory Hook] 无对话内容可保存", file=sys.stderr)
    sys.exit(0)

if not topic:
    topic = "未命名对话"

conversation_text = "\n".join(lines)

# ── 写入临时文件并调用 summarize_session.py ────────────────
tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8")
try:
    tmp.write(conversation_text)
    tmp.close()

    project_dir = os.getcwd()

    result = subprocess.run(
        [sys.executable, "scripts/summarize_session.py",
         "--topic", topic,
         "--file", tmp.name],
        cwd=project_dir,
        capture_output=True,
        encoding="utf-8",
        timeout=25,
    )
    if result.returncode == 0:
        print(f"[Memory Hook] 记忆保存完成：{topic}")
    else:
        print(f"[Memory Hook] 保存失败: {result.stderr.strip()}", file=sys.stderr)
finally:
    try:
        os.unlink(tmp.name)
    except OSError:
        pass
PYEOF

# ── 清理临时 hook JSON 文件 ──────────────────────────────────
rm -f "$HOOK_TMPFILE"
