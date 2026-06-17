"""
auto_save_memory.py — 轮次驱动的自动记忆保存

由 UserPromptSubmit hook 调用，检查轮次计数并在达到间隔时保存当前会话记忆。

用法（Claude Code hook 调用）：
  python scripts/auto_save_memory.py --transcript-path <path> --session-id <id>

也可以从 stdin 读取 hook JSON（与 pre_prompt.sh 兼容）：
  echo '{"session_id":"...","transcript_path":"..."}' | python scripts/auto_save_memory.py --stdin
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from turn_counter import should_auto_save, get_interval

PROJECT_DIR = Path(__file__).resolve().parents[1]
PROGRAM_ROOT = Path(__file__).resolve().parents[3]  # scripts → ClaudeMeory → Skill → program/


def parse_hook_stdin() -> dict:
    """从 stdin 读取 hook JSON。"""
    try:
        raw = sys.stdin.read()
        if raw.strip():
            return json.loads(raw)
    except json.JSONDecodeError:
        pass
    return {}


def read_transcript(
    transcript_path: str, session_id: str
) -> tuple[str, str]:
    """从 transcript JSONL 读取对话内容，返回 (conversation_text, topic)。"""
    if not transcript_path:
        return "", ""

    transcript_path = os.path.expanduser(transcript_path)

    # 尝试 transcript_path，回退到 history.jsonl
    if not os.path.isfile(transcript_path):
        history_path = os.path.expanduser("~/.claude/history.jsonl")
        if os.path.isfile(history_path):
            transcript_path = history_path
        else:
            return "", ""

    lines: list[str] = []
    topic = ""
    is_history_format = False

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            all_lines = f.readlines()

        # 检测格式
        for raw_line in all_lines:
            try:
                test = json.loads(raw_line.strip())
                if "sessionId" in test and "display" in test and "type" not in test:
                    is_history_format = True
                break
            except Exception:
                continue

        for raw_line in all_lines:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                msg = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            role = ""
            content = ""

            if is_history_format:
                if session_id and msg.get("sessionId") != session_id:
                    continue
                role = "user"
                content = msg.get("display", "")
            else:
                msg_type = msg.get("type", "")
                if msg_type not in ("user", "assistant"):
                    continue
                inner = msg.get("message", {})
                role = inner.get("role", msg_type)
                content = inner.get("content", "")

            if not content:
                continue

            if isinstance(content, list):
                parts = []
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "text":
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
                        # 跳过粘贴内容作为 topic
                        candidate = content[:80]
                        if not candidate.startswith("[Pasted text"):
                            topic = candidate

        if not topic:
            topic = (session_id[:50] if session_id else "未命名对话")

    except Exception as e:
        print(f"[AutoSave] 读取 transcript 失败: {e}", file=sys.stderr)
        return "", ""

    return "\n".join(lines), topic


def run_save(conversation_text: str, topic: str, workspace: str = "") -> bool:
    """调用 summarize_session.py 保存记忆。"""
    if not conversation_text or not topic:
        return False

    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    )
    try:
        tmp.write(conversation_text)
        tmp.close()

        cmd = [
            sys.executable,
            str(PROJECT_DIR / "scripts" / "summarize_session.py"),
            "--topic", topic,
            "--file", tmp.name,
        ]
        if workspace:
            cmd.extend(["--workspace", workspace])

        result = subprocess.run(
            cmd,
            cwd=str(PROJECT_DIR),
            capture_output=True,
            encoding="utf-8",
            timeout=25,
        )
        if result.returncode == 0:
            print(f"[AutoSave] 自动保存完成（第 N 轮触发）: {topic}")
            return True
        else:
            print(
                f"[AutoSave] 保存失败: {result.stderr.strip()}",
                file=sys.stderr,
            )
            return False
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Auto-save memory every N conversation turns"
    )
    parser.add_argument(
        "--transcript-path", help="transcript JSONL 文件路径"
    )
    parser.add_argument("--session-id", default="", help="会话 ID")
    parser.add_argument("--workspace", default="", help="workspace 名称")
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="从 stdin 读取 hook JSON（兼容 pre_prompt.sh 调用方式）",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="自动保存间隔轮数（默认从环境变量读取或 10）",
    )

    args = parser.parse_args()

    # 获取 hook 数据
    session_id = args.session_id
    transcript_path = args.transcript_path

    if args.stdin:
        hook_data = parse_hook_stdin()
        if hook_data:
            session_id = session_id or hook_data.get("session_id", "")
            transcript_path = transcript_path or hook_data.get(
                "transcript_path", ""
            )

    if not transcript_path:
        # 静默退出 — 无 transcript 可保存
        return

    interval = args.interval or get_interval()
    memory_dir = str(PROGRAM_ROOT / "Meory" / "memory")

    # 检查是否需自动保存
    should_save, state = should_auto_save(
        session_id=session_id,
        transcript_path=transcript_path,
        memory_dir=memory_dir,
        interval=interval,
    )

    if not should_save:
        # 不输出日志，避免每轮都打印
        return

    print(
        f"[AutoSave] 第 {state.turn_count} 轮，触发自动保存 "
        f"(间隔={interval}, 累计保存={state.total_saves}次)"
    )

    conversation_text, topic = read_transcript(transcript_path, session_id)

    if not conversation_text:
        print("[AutoSave] 无对话内容可保存", file=sys.stderr)
        return

    run_save(conversation_text, topic, workspace=args.workspace)


if __name__ == "__main__":
    main()
