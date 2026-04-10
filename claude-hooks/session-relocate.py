#!/usr/bin/env python3
"""
SessionEnd hook: relocate session JSONL based on user-declared project marker.

Reads stdin JSON {"session_id": "..."}.
Looks for marker at ~/.claude/session-targets/<session_id>.target with:
    target_cwd=/absolute/path
    title=optional display title

If marker exists:
    1. Compute target dir name by escaping target_cwd (/ -> -)
    2. Move JSONL to ~/.claude/projects/<escaped>/
    3. Append custom-title if provided
    4. Delete marker

If no marker: do nothing. Idempotent.
"""

from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
TARGETS_DIR = CLAUDE_DIR / "session-targets"
LOG_FILE = CLAUDE_DIR / "session-relocate.log"
MARKER_TTL_DAYS = 7  # 超过 7 天未消费的 marker 视为孤儿（kill -9 / 崩溃残留）


def log(msg: str) -> None:
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass
    sys.stderr.write(msg + "\n")


def find_jsonl(session_id: str) -> Path | None:
    for f in PROJECTS_DIR.rglob(f"{session_id}.jsonl"):
        return f
    return None


def encode_cwd(cwd: str) -> str:
    """Match Claude Code's project-dir encoding: non-[a-zA-Z0-9-] -> '-'.

    Examples:
        /Users/alice/news-bot          -> -Users-alice-news-bot
        /Users/alice/.clawd            -> -Users-alice--clawd
        /Users/alice/site.github.io    -> -Users-alice-site-github-io
        /Users/alice/Desktop/录音       -> -Users-alice-Desktop----
    """
    import re
    return re.sub(r"[^a-zA-Z0-9-]", "-", cwd.rstrip("/"))


def parse_marker(path: Path) -> dict:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def append_custom_title(jsonl_path: Path, session_id: str, title: str) -> None:
    entry = {"type": "custom-title", "customTitle": title, "sessionId": session_id}
    with open(jsonl_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def sweep_orphan_markers() -> None:
    """删除超过 MARKER_TTL_DAYS 天未被消费的孤儿 marker。

    场景：claude 被 kill -9 或系统崩溃 → SessionEnd hook 没跑 → marker 留下
    """
    if not TARGETS_DIR.exists():
        return
    cutoff = time.time() - MARKER_TTL_DAYS * 86400
    for marker in TARGETS_DIR.glob("*.target"):
        try:
            if marker.stat().st_mtime < cutoff:
                marker.unlink()
                log(f"[relocate] swept orphan marker: {marker.name} (>{MARKER_TTL_DAYS}d old)")
        except Exception:
            pass


def main():
    # 顺手清理孤儿 marker（每次 SessionEnd 都跑一次，几乎零成本）
    sweep_orphan_markers()

    try:
        hook_data = json.load(sys.stdin)
    except Exception:
        return  # Not a hook invocation, silent exit
    session_id = hook_data.get("session_id", "")
    if not session_id:
        return

    marker = TARGETS_DIR / f"{session_id}.target"
    if not marker.exists():
        return

    info = parse_marker(marker)
    target_cwd = info.get("target_cwd")
    title = info.get("title")
    if not target_cwd:
        log(f"[relocate] marker missing target_cwd: {marker}")
        return

    jsonl = find_jsonl(session_id)
    if not jsonl:
        log(f"[relocate] jsonl not found for {session_id}")
        return

    target_dir = PROJECTS_DIR / encode_cwd(target_cwd)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / jsonl.name

    if jsonl.parent == target_dir:
        marker.unlink(missing_ok=True)
        log(f"[relocate] {session_id[:8]} already in {target_dir.name}, marker cleared")
        return

    if target_path.exists():
        log(f"[relocate] target collision, skipping: {target_path}")
        return

    if title:
        try:
            append_custom_title(jsonl, session_id, title)
        except Exception as e:
            log(f"[relocate] custom-title append failed: {e}")

    try:
        shutil.move(str(jsonl), str(target_path))
        log(f"[relocate] {session_id[:8]} -> {target_dir.name} (title={title!r})")
    except Exception as e:
        log(f"[relocate] move failed: {e}")
        return

    # 同名 sidecar 目录也跟着搬：subagents/ + tool-results/
    # 路径形如 ~/.claude/projects/<dir>/<session_id>/{subagents,tool-results}
    sidecar = jsonl.parent / session_id
    if sidecar.exists() and sidecar.is_dir():
        target_sidecar = target_dir / session_id
        if target_sidecar.exists():
            log(f"[relocate] sidecar collision, skipping: {target_sidecar}")
        else:
            try:
                shutil.move(str(sidecar), str(target_sidecar))
                log(f"[relocate] sidecar {session_id[:8]}/ -> {target_dir.name}")
            except Exception as e:
                log(f"[relocate] sidecar move failed: {e}")

    marker.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
