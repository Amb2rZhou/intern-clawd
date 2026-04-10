#!/usr/bin/env python3
"""
从 Claude Code JSONL transcript 提取完整对话记录为 Markdown。
SessionEnd hook 调用，或手动: python3 extract-session.py <session_id>

输出到 ~/.clawd/raw/sessions/{date}_{session_id:.8}_{title}.md
"""

import json, sys, os, re, glob
from datetime import datetime
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
RAW_SESSIONS = Path.home() / ".clawd/raw/sessions"
RAW_SESSIONS.mkdir(parents=True, exist_ok=True)


def find_jsonl(session_id: str) -> Path | None:
    """在 ~/.claude/projects/ 下找 session 的 JSONL 文件。"""
    for f in CLAUDE_DIR.rglob(f"{session_id}.jsonl"):
        return f
    return None


def extract_messages(jsonl_path: Path) -> list[dict]:
    """从 JSONL 提取对话消息。"""
    messages = []
    with open(jsonl_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = entry.get("type")

            if msg_type == "user":
                # 用户消息
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                            elif block.get("type") == "image":
                                text_parts.append("[图片]")
                        elif isinstance(block, str):
                            text_parts.append(block)
                    content = "\n".join(text_parts)
                if content.strip():
                    messages.append({"role": "user", "content": content.strip()})

            elif msg_type == "assistant":
                # Claude 回复
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, list):
                    text_parts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                text_parts.append(block.get("text", ""))
                            elif block.get("type") == "tool_use":
                                tool = block.get("name", "?")
                                inp = block.get("input", {})
                                # 精简工具调用显示
                                if tool == "Bash":
                                    cmd = inp.get("command", "")[:200]
                                    text_parts.append(f"```bash\n# [Tool: {tool}]\n{cmd}\n```")
                                elif tool in ("Read", "Write", "Edit"):
                                    fp = inp.get("file_path", "")
                                    text_parts.append(f"> [Tool: {tool}] {fp}")
                                elif tool == "Grep":
                                    pat = inp.get("pattern", "")
                                    text_parts.append(f"> [Tool: {tool}] pattern={pat}")
                                else:
                                    text_parts.append(f"> [Tool: {tool}]")
                            elif block.get("type") == "tool_result":
                                pass  # 跳过工具结果（太长）
                        elif isinstance(block, str):
                            text_parts.append(block)
                    content = "\n\n".join(p for p in text_parts if p.strip())
                if content.strip():
                    messages.append({"role": "assistant", "content": content.strip()})

            elif msg_type == "summary":
                # Context compaction summary
                text = entry.get("summary", "")
                if text:
                    messages.append({"role": "system", "content": f"[Context compacted]\n{text[:500]}..."})

    return messages


def guess_title(messages: list[dict]) -> str:
    """从前几条消息猜标题。"""
    for msg in messages[:3]:
        if msg["role"] == "user":
            text = msg["content"][:60].strip()
            # 清理非法文件名字符
            text = re.sub(r'[/\\:*?"<>|\n\r]', '_', text)
            text = text.strip('_. ')
            if text:
                return text[:50]
    return "untitled"


def format_markdown(messages: list[dict], session_id: str, jsonl_path: Path) -> str:
    """格式化为 Markdown。"""
    # 获取时间
    stat = jsonl_path.stat()
    created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")
    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

    lines = [
        f"# Session {session_id[:8]}",
        f"",
        f"- **Session ID**: `{session_id}`",
        f"- **Started**: {created}",
        f"- **Last active**: {modified}",
        f"- **Source**: `{jsonl_path}`",
        f"- **Messages**: {len(messages)}",
        f"",
        f"---",
        f"",
    ]

    for msg in messages:
        role = msg["role"]
        content = msg["content"]

        if role == "user":
            lines.append(f"## 👤 User\n")
            lines.append(content)
            lines.append("")
        elif role == "assistant":
            lines.append(f"## 🤖 Assistant\n")
            lines.append(content)
            lines.append("")
        elif role == "system":
            lines.append(f"## ⚙️ System\n")
            lines.append(content)
            lines.append("")

        lines.append("---\n")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        # 没有参数时，从 stdin 读取 hook JSON（SessionEnd hook 模式）
        try:
            hook_data = json.load(sys.stdin)
            session_id = hook_data.get("session_id", "")
        except:
            print("Usage: extract-session.py <session_id>", file=sys.stderr)
            sys.exit(1)
    else:
        session_id = sys.argv[1]

    if not session_id:
        print("No session_id", file=sys.stderr)
        sys.exit(1)

    jsonl_path = find_jsonl(session_id)
    if not jsonl_path:
        print(f"JSONL not found for {session_id}", file=sys.stderr)
        sys.exit(1)

    messages = extract_messages(jsonl_path)
    if not messages:
        print(f"No messages in {session_id}", file=sys.stderr)
        sys.exit(0)

    title = guess_title(messages)
    date_str = datetime.fromtimestamp(jsonl_path.stat().st_ctime).strftime("%Y%m%d")
    filename = f"{date_str}_{session_id[:8]}_{title}.md"
    output = RAW_SESSIONS / filename

    md = format_markdown(messages, session_id, jsonl_path)
    output.write_text(md, encoding="utf-8")
    print(f"✓ Extracted {len(messages)} messages → {output}")

    # telemetry
    try:
        sys.path.insert(0, str(Path.home() / ".clawd"))
        from telemetry import log_op
        log_op("session-end", source="hook", pages_touched=len(messages), detail=title[:80])
    except Exception:
        pass


if __name__ == "__main__":
    main()
