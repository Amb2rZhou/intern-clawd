#!/usr/bin/env python3
"""
Wiki auto-maintenance: LLM periodic wake-up to clean and organize the knowledge base.
Based on Andrej Karpathy's LLM Wiki design pattern.

Schedule: first Saturday of each month at 09:07 (finishes well before the 6th/7th)
Method: calls claude -p for comprehensive maintenance, sends IM notification with results

Usage:
  python3 wiki-maintenance.py           # Run maintenance
  python3 wiki-maintenance.py --dry-run # Print prompt only, don't execute
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from feishu_utils import send_feishu_message

CLAWD_DIR = Path.home() / ".clawd"
REAL_CLAUDE = Path.home() / ".local/bin/claude"
LOG_FILE = CLAWD_DIR / "maintenance.log"

def read_file(path, max_lines=80):
    try:
        lines = path.read_text(encoding="utf-8").strip().split("\n")[:max_lines]
        return "\n".join(lines)
    except Exception:
        return "(empty)"

def build_prompt():
    work_idx = read_file(CLAWD_DIR / "work/wiki/index.md")
    life_idx = read_file(CLAWD_DIR / "life/wiki/index.md")
    shared_idx = read_file(CLAWD_DIR / "shared-wiki/index.md")

    work_log = read_file(CLAWD_DIR / "work/wiki/log.md", max_lines=20)
    life_log = read_file(CLAWD_DIR / "life/wiki/log.md", max_lines=20)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""You are the Wiki maintainer. Current time: {now}. Perform monthly auto-maintenance.

## Current Knowledge Base State

### Work domain index:
{work_idx}

### Life domain index:
{life_idx}

### Shared Wiki index:
{shared_idx}

### Work domain recent log:
{work_log}

### Life domain recent log:
{life_log}

## Maintenance Tasks (execute in order)

### 1. Health Check (Lint)
- Read all wiki pages, verify [[wiki-links]] have matching files
- Check that index.md entries point to existing pages
- Find orphaned pages (exist but not referenced by index or other pages)
- Find empty pages or pages with only frontmatter
- Check that frontmatter `updated` dates roughly match actual last modification

### 2. Cross-Reference Updates
- Check for missing [[wiki-links]] between related pages
- Fill in missing references in linked_from fields
- Ensure linked_from lists are accurate (don't point to deleted pages)

### 3. Index Cleanup
- Sort by active date descending (most recent first)
- Flag projects inactive for 30+ days as stale
- Ensure each entry's one-line description accurately reflects current page content

### 4. Content Quality
- Check if page content is outdated (compare against recent log.md entries)
- If a description is clearly outdated, update it directly
- Ensure shared-wiki/boss-profile.md and coding-style.md are coherent

### 5. Pattern Drift Detection (content vs source consistency)
- Check that wiki page `sources` fields point to valid raw sources or GitHub repos
- Use Bash to run `git -C ~/repo-name log --oneline -5` to check recent commits
- If a repo is recently active but wiki page `updated` is 14+ days behind, flag as drift
- Append `> [!drift] Wiki description may be out of sync with current repo state` to drifted pages
- Summarize drift findings in the maintenance report

### 6. Generate Maintenance Report
When done, append a maintenance log entry to shared-wiki/log.md:
## [{now}] maintenance | Monthly Wiki Maintenance

Report should include:
- Number of issues found and fixed
- New/updated cross-references
- Projects flagged as stale
- Overall knowledge base health assessment (one sentence)

### Rules
- Output in English
- Directly fix clear issues (broken links, missing references, outdated descriptions)
- Do not delete any pages
- Do not modify raw sources
- Log every change
- End with a brief maintenance summary (for the boss to read)"""


def main():
    dry_run = "--dry-run" in sys.argv
    prompt = build_prompt()

    if dry_run:
        print(prompt)
        return

    from wiki_lint import lint_all
    pre_issues, pre_stats = lint_all()
    print(f"[wiki-maintenance] pre-lint: {len(pre_issues)} issues, {pre_stats['pages']} pages")

    print(f"[wiki-maintenance] Starting, log: {LOG_FILE}")

    try:
        result = subprocess.run(
            [str(REAL_CLAUDE), "-p", prompt,
             "--allowedTools", "Read,Edit,Write,Bash,Glob,Grep",
             "--max-turns", "15",
             "--output-format", "text"],
            capture_output=True, text=True, timeout=600,
            cwd=str(CLAWD_DIR)
        )
        output = result.stdout.strip() or "(no output)"
        if result.returncode != 0:
            output += f"\n[stderr] {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        output = "Maintenance timed out (10 min limit)"
    except Exception as e:
        output = f"Maintenance failed: {e}"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().isoformat()}]\n{output}\n{'='*60}\n")

    post_issues, post_stats = lint_all()
    lint_delta = len(pre_issues) - len(post_issues)

    try:
        from telemetry import log_op
        log_op("maintenance", domain="both", pages_touched=post_stats["pages"],
               status="ok" if result.returncode == 0 else "error",
               detail=f"pre:{len(pre_issues)} post:{len(post_issues)} fixed:{lint_delta}",
               source="cron")
    except Exception:
        pass

    summary = output[:400] if len(output) > 400 else output
    lint_info = f"\n\nLint: {len(pre_issues)}->{len(post_issues)} issues ({lint_delta} fixed)"
    send_feishu_message(f"Wiki Monthly Maintenance Complete\n\n{summary}{lint_info}", tag="wiki-maintenance")

    print(f"[wiki-maintenance] Done")


if __name__ == "__main__":
    main()
