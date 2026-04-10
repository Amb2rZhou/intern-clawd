#!/usr/bin/env python3
"""
每周自动生成周会摘要并发送到飞书。
由 cron 在每周日 20:00 触发。

用法:
  python3 weekly-report.py           # 生成摘要并发送
  python3 weekly-report.py --dry-run # 只打印不发送
"""

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

CLAWD_DIR = Path.home() / ".clawd"


def read_recent_logs(domain, days=7):
    """读取最近 N 天的 log 条目"""
    log_path = CLAWD_DIR / domain / "wiki" / "log.md"
    if not log_path.exists():
        return []

    cutoff = datetime.now() - timedelta(days=days)
    entries = []
    current_entry = None

    for line in log_path.read_text().strip().split("\n"):
        # 匹配 log 标题行
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
    """读取活跃项目列表"""
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
    """构建周报摘要"""
    lines = ["📊 周会摘要", f"日期: {datetime.now().strftime('%Y-%m-%d')}", ""]

    for domain in ["work", "life"]:
        entries = read_recent_logs(domain, days=7)
        projects = read_active_projects(domain)

        lines.append(f"{'='*20}")
        lines.append(f"【{domain.upper()}】")
        lines.append("")

        # 活跃项目
        if projects:
            lines.append("活跃项目:")
            for p in projects:
                lines.append(f"  • {p['name']} — {p['desc']} (active: {p['active']})")
            lines.append("")

        # 本周活动
        if entries:
            lines.append(f"本周活动 ({len(entries)} 条):")
            for e in entries:
                lines.append(f"  • [{e['date']}] {e['title']}")
                for b in e["body"][:2]:  # 最多 2 行摘要
                    lines.append(f"    {b}")
            lines.append("")
        else:
            lines.append("本周活动: 无记录")
            lines.append("")

    lines.append("---")
    lines.append("回复「周会」开始详细讨论")
    lines.append("回复「复盘」对某个项目做深度回顾")

    return "\n".join(lines)


sys.path.insert(0, str(Path(__file__).parent))
from feishu_utils import send_feishu_message


def main():
    dry_run = "--dry-run" in sys.argv
    summary = build_weekly_summary()

    print(summary)
    print()

    if dry_run:
        print("[weekly] dry-run 模式，不发送")
    else:
        send_feishu_message(summary, tag="weekly")


if __name__ == "__main__":
    main()
