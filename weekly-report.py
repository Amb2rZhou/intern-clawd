#!/usr/bin/env python3
"""
Auto-generate weekly summary and send via IM.
Triggered by cron every Sunday at 20:00.

Usage:
  python3 weekly-report.py           # Generate and send
  python3 weekly-report.py --dry-run # Print only, don't send
"""

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

CLAWD_DIR = Path.home() / ".clawd"


def read_recent_logs(domain, days=7):
    """Read log entries from the last N days."""
    log_path = CLAWD_DIR / domain / "wiki" / "log.md"
    if not log_path.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    entries = []
    current_entry = None

    for line in log_path.read_text().strip().split("\n"):
        match = re.match(r'^## \[(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}\] (.+)$', line)
        if match:
            date_str, title = match.groups()
            try:
                entry_date = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                continue
            if entry_date >= cutoff:
                current_entry = {"date": date_str, "title": title, "body": []}
                entries.append(current_entry)
            else:
                current_entry = None
        elif current_entry is not None and line.strip():
            current_entry["body"].append(line.strip())

    return entries


def read_active_projects(domain):
    """Read active project list from index."""
    index_path = CLAWD_DIR / domain / "wiki" / "index.md"
    if not index_path.exists():
        return []

    projects = []
    for line in index_path.read_text().strip().split("\n"):
        match = re.match(r'^- \[(.+?)\]\((.+?)\)\s+[—\-]+\s+(.+?)(?:\s+`active:(\d{4}-\d{2}-\d{2})`)?$', line)
        if match:
            name, link, desc, active = match.groups()
            projects.append({"name": name, "desc": desc, "active": active or "unknown"})
    return projects


def build_weekly_summary():
    """Build weekly summary text."""
    lines = ["Weekly Summary", f"Date: {datetime.now().strftime('%Y-%m-%d')}", ""]

    for domain in ["work", "life"]:
        entries = read_recent_logs(domain, days=7)
        projects = read_active_projects(domain)

        lines.append(f"{'='*20}")
        lines.append(f"[{domain.upper()}]")
        lines.append("")

        if projects:
            lines.append("Active projects:")
            for p in projects:
                lines.append(f"  * {p['name']} — {p['desc']} (active: {p['active']})")
            lines.append("")

        if entries:
            lines.append(f"This week ({len(entries)} entries):")
            for e in entries:
                lines.append(f"  * [{e['date']}] {e['title']}")
                for b in e["body"][:2]:
                    lines.append(f"    {b}")
            lines.append("")
        else:
            lines.append("This week: no activity recorded")
            lines.append("")

    lines.append("---")
    lines.append("Reply 'weekly' for detailed discussion")
    lines.append("Reply 'reflect' for a deep retrospective")

    return "\n".join(lines)


sys.path.insert(0, str(Path(__file__).parent))
from feishu_utils import send_feishu_message


def main():
    dry_run = "--dry-run" in sys.argv
    summary = build_weekly_summary()

    print(summary)
    print()

    if dry_run:
        print("[weekly] Dry run, not sending")
    else:
        send_feishu_message(summary, tag="weekly")


if __name__ == "__main__":
    main()
