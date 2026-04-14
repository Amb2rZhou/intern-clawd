#!/usr/bin/env python3
"""
Scan and extract historical Claude Code sessions for wiki archival.
Phase 1 (this script): scan → stats → extract to raw/sessions/
Phase 2 (run by a Claude session): classify → write wiki → generate graph

Usage:
  python3 import-history.py --scan          # Scan only, don't extract
  python3 import-history.py --extract       # Scan + extract unprocessed sessions
  python3 import-history.py --extract --all # Re-extract all sessions (including already extracted)
"""

import json, sys, os, re
from pathlib import Path
from datetime import datetime

CLAUDE_DIR = Path.home() / ".claude"
CLAWD_DIR = Path(os.environ.get("CLAWD_DIR", Path.home() / ".clawd"))
RAW_SESSIONS = CLAWD_DIR / "raw" / "sessions"


def scan_sessions():
    """Scan ~/.claude/projects/ for all JSONL session files."""
    sessions = []
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return sessions

    for jsonl in sorted(projects_dir.rglob("*.jsonl")):
        try:
            stat = jsonl.stat()
        except OSError:
            continue

        size_kb = stat.st_size / 1024
        if size_kb < 1:
            continue

        msg_count = 0
        user_count = 0
        first_user_msg = ""

        with open(jsonl, encoding="utf-8", errors="replace") as f:
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
                    msg_count += 1
                    user_count += 1
                    if not first_user_msg:
                        content = entry.get("message", {}).get("content", "")
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    first_user_msg = block.get("text", "")[:100]
                                    break
                        elif isinstance(content, str):
                            first_user_msg = content[:100]
                elif msg_type == "assistant":
                    msg_count += 1

        if msg_count == 0:
            continue

        session_id = jsonl.stem
        already_extracted = any(RAW_SESSIONS.glob(f"*_{session_id[:8]}_*"))

        rel = jsonl.relative_to(projects_dir)
        project_dir = str(rel.parent).replace("-", "/").lstrip("/")

        sessions.append({
            "path": str(jsonl),
            "session_id": session_id,
            "project_dir": project_dir,
            "size_kb": round(size_kb, 1),
            "msg_count": msg_count,
            "user_count": user_count,
            "first_msg": first_user_msg.replace("\n", " ").strip(),
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "extracted": already_extracted,
        })

    return sorted(sessions, key=lambda s: s["created"])


def print_report(sessions):
    """Print scan report."""
    new = [s for s in sessions if not s["extracted"]]
    old = [s for s in sessions if s["extracted"]]
    total_size = sum(s["size_kb"] for s in sessions)
    new_size = sum(s["size_kb"] for s in new)

    print(f"Scan results:")
    print(f"  Total sessions: {len(sessions)}")
    print(f"  Already extracted: {len(old)}")
    print(f"  Pending: {len(new)}")
    print(f"  Total size: {total_size:.0f} KB")
    print(f"  Pending size: {new_size:.0f} KB")
    print()

    if sessions:
        print(f"  Date range: {sessions[0]['created'].strftime('%Y-%m-%d')} -> {sessions[-1]['modified'].strftime('%Y-%m-%d')}")
        print()

    by_project = {}
    for s in sessions:
        p = s["project_dir"] or "(unknown)"
        by_project.setdefault(p, []).append(s)

    print(f"By project:")
    for proj, ss in sorted(by_project.items(), key=lambda x: -len(x[1])):
        new_count = sum(1 for s in ss if not s["extracted"])
        print(f"  {proj}: {len(ss)} sessions ({new_count} new)")
    print()

    extract_input_tokens = int(new_size * 1024 / 4 * 0.2)
    classify_tokens = len(new) * 500
    total_tokens = extract_input_tokens + classify_tokens

    print(f"Phase 2 (LLM classify + archive) estimated cost:")
    print(f"  Input tokens: ~{extract_input_tokens:,}")
    print(f"  Classification tokens: ~{classify_tokens:,}")
    print(f"  Total: ~{total_tokens:,} tokens")
    if total_tokens > 100000:
        print(f"  Note: high token count — consider importing only the last 30 days first")
    print()

    print(f"Last 5 pending sessions:")
    for s in new[-5:]:
        date = s["created"].strftime("%m-%d")
        msg = s["first_msg"][:50] or "(empty)"
        tag = "+" if s["extracted"] else "o"
        print(f"  {tag} [{date}] {s['user_count']} turns {s['size_kb']:.0f}KB | {msg}")
    print()


def extract_session(jsonl_path: Path, session_id: str) -> Path | None:
    """Extract a single session to raw/sessions/, return output path."""
    RAW_SESSIONS.mkdir(parents=True, exist_ok=True)

    messages = []
    with open(jsonl_path, encoding="utf-8", errors="replace") as f:
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
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            parts.append(block)
                    content = "\n".join(parts)
                if content.strip():
                    messages.append(("user", content.strip()))
            elif msg_type == "assistant":
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            parts.append(block)
                    content = "\n".join(parts)
                if content.strip():
                    messages.append(("assistant", content.strip()))
            elif msg_type == "summary":
                text = entry.get("summary", "")
                if text:
                    messages.append(("summary", text.strip()))

    if not messages:
        return None

    title = "untitled"
    for role, content in messages[:3]:
        if role == "user":
            title = re.sub(r'[/\\:*?"<>|\n\r]', '_', content[:50]).strip('_. ')
            if title:
                break

    stat = Path(jsonl_path).stat()
    date_str = datetime.fromtimestamp(stat.st_ctime).strftime("%Y%m%d")
    filename = f"{date_str}_{session_id[:8]}_{title}.md"
    output = RAW_SESSIONS / filename

    created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")
    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

    lines = [
        f"---",
        f"session_id: {session_id}",
        f"created: {created}",
        f"modified: {modified}",
        f"source: {jsonl_path}",
        f"messages: {len(messages)}",
        f"---",
        f"",
    ]
    for role, content in messages:
        if role == "user":
            lines.append(f"## User\n\n{content}\n")
        elif role == "assistant":
            if len(content) > 2000:
                content = content[:2000] + "\n\n[...truncated...]"
            lines.append(f"## Assistant\n\n{content}\n")
        elif role == "summary":
            lines.append(f"## [Context Summary]\n\n{content[:500]}\n")

    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def snapshot_wiki():
    """Back up current wiki state for rollback after import."""
    import tarfile
    from datetime import datetime

    backup_dir = CLAWD_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tar_path = backup_dir / f"pre-import-{timestamp}.tar.gz"

    dirs_to_backup = []
    for d in ["work/wiki", "life/wiki", "shared-wiki"]:
        p = CLAWD_DIR / d
        if p.exists():
            dirs_to_backup.append((p, d))

    if not dirs_to_backup:
        print("  No wiki content to back up")
        return None

    with tarfile.open(tar_path, "w:gz") as tar:
        for full_path, arc_name in dirs_to_backup:
            tar.add(full_path, arcname=arc_name)

    rollback_path = CLAWD_DIR / "rollback-import.sh"
    rollback_content = f"""#!/bin/bash
# Rollback import — restore wiki state from {timestamp}
# Auto-generated, safe to delete after use

set -e
CLAWD_DIR="${{CLAWD_DIR:-$HOME/.clawd}}"
BACKUP="{tar_path}"

if [[ ! -f "$BACKUP" ]]; then
    echo "ERROR: backup file not found: $BACKUP"
    exit 1
fi

echo "About to restore wiki to pre-import state ({timestamp})"
echo "This will overwrite current wiki content (work/wiki, life/wiki, shared-wiki)"
echo ""
read -p "Confirm rollback? (y/N) " confirm
[[ "$confirm" == [yY] ]] || {{ echo "Cancelled"; exit 0; }}

echo "Restoring..."
for d in work/wiki life/wiki shared-wiki; do
    [[ -d "$CLAWD_DIR/$d" ]] && rm -rf "$CLAWD_DIR/$d"
done

tar -xzf "$BACKUP" -C "$CLAWD_DIR"

BACKUP_TIME=$(stat -f %m "$BACKUP" 2>/dev/null || stat -c %Y "$BACKUP" 2>/dev/null)
if [[ -d "$CLAWD_DIR/raw/sessions" ]]; then
    find "$CLAWD_DIR/raw/sessions" -name "*.md" -newer "$BACKUP" -delete 2>/dev/null
    echo "  Cleaned up raw/sessions files added after import"
fi

echo ""
echo "Wiki restored to {timestamp} state"
echo "  Backup preserved at: $BACKUP"
echo "  This rollback script can be deleted: rm $CLAWD_DIR/rollback-import.sh"
"""
    rollback_path.write_text(rollback_content, encoding="utf-8")
    os.chmod(rollback_path, 0o755)

    size_kb = tar_path.stat().st_size / 1024
    print(f"  Snapshot saved: {tar_path} ({size_kb:.0f} KB)")
    print(f"  Rollback script: {rollback_path}")
    return tar_path


def main():
    scan_only = "--scan" in sys.argv
    extract_all = "--all" in sys.argv
    snapshot_only = "--snapshot" in sys.argv

    if snapshot_only:
        print("=== Backing up current wiki state ===\n")
        result = snapshot_wiki()
        if result:
            print(f"\nBackup complete. Rollback command: bash {CLAWD_DIR}/rollback-import.sh")
        sys.exit(0)

    print("=== intern-clawd History Import ===\n")

    sessions = scan_sessions()
    if not sessions:
        print("No historical sessions found.")
        print(f"  Scan path: {CLAUDE_DIR / 'projects'}")
        sys.exit(0)

    print_report(sessions)

    if scan_only:
        manifest = CLAWD_DIR / "raw" / "import-manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        data = []
        for s in sessions:
            data.append({
                "session_id": s["session_id"],
                "project_dir": s["project_dir"],
                "size_kb": s["size_kb"],
                "msg_count": s["msg_count"],
                "first_msg": s["first_msg"],
                "created": s["created"].isoformat(),
                "extracted": s["extracted"],
            })
        manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Manifest written to: {manifest}")
        sys.exit(0)

    to_extract = sessions if extract_all else [s for s in sessions if not s["extracted"]]
    if not to_extract:
        print("All sessions already extracted.")
        print(f"  To re-extract: python3 import-history.py --extract --all")
        sys.exit(0)

    print(f"Extracting {len(to_extract)} sessions...\n")

    success = 0
    for i, s in enumerate(to_extract, 1):
        try:
            out = extract_session(Path(s["path"]), s["session_id"])
            if out:
                print(f"  [{i}/{len(to_extract)}] + {out.name}")
                success += 1
            else:
                print(f"  [{i}/{len(to_extract)}] - skipped (no messages)")
        except Exception as e:
            print(f"  [{i}/{len(to_extract)}] x {s['session_id'][:8]}: {e}")

    print(f"\nExtraction complete: {success}/{len(to_extract)} succeeded")
    print(f"Output directory: {RAW_SESSIONS}")

    manifest = CLAWD_DIR / "raw" / "import-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    all_sessions = scan_sessions()
    data = []
    for s in all_sessions:
        data.append({
            "session_id": s["session_id"],
            "project_dir": s["project_dir"],
            "size_kb": s["size_kb"],
            "msg_count": s["msg_count"],
            "first_msg": s["first_msg"],
            "created": s["created"].isoformat(),
            "extracted": s["extracted"],
        })
    manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Manifest: {manifest}")
    print(f"\nNext step: say 'import history' in a secretary session to classify and archive.")


if __name__ == "__main__":
    main()
