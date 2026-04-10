#!/usr/bin/env python3
"""
月会：冷门清理 + 月度总结，每月 1 号发送到飞书。

用法:
  python3 monthly-review.py           # 生成并发送
  python3 monthly-review.py --dry-run # 只打印不发送
"""

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from feishu_utils import send_feishu_message

CLAWD_DIR = Path.home() / ".clawd"
STALE_DAYS = 30


def read_recent_logs(domain, days=30):
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


def find_stale_projects(domain):
    index_path = CLAWD_DIR / domain / "wiki" / "index.md"
    if not index_path.exists():
        return [], []

    cutoff = datetime.now() - timedelta(days=STALE_DAYS)
    active = []
    stale = []

    for line in index_path.read_text().strip().split("\n"):
        match = re.match(r'^- \[(.+?)\]\((.+?)\)\s+[—\-]+\s+(.+?)(?:\s+`active:(\d{4}-\d{2}-\d{2})`)?$', line)
        if match:
            name, link, desc, active_date = match.groups()
            try:
                dt = datetime.strptime(active_date, "%Y-%m-%d") if active_date else datetime(2020, 1, 1)
            except ValueError:
                dt = datetime(2020, 1, 1)
            item = {"name": name, "desc": desc, "active": active_date or "unknown", "days": (datetime.now() - dt).days}
            if dt < cutoff:
                stale.append(item)
            else:
                active.append(item)

    return active, stale


def build_monthly_review():
    now = datetime.now()
    lines = [f"📅 月会 — {now.strftime('%Y年%m月')}", ""]

    all_stale = []

    for domain in ["work", "life"]:
        entries = read_recent_logs(domain, days=30)
        active_proj, stale_proj = find_stale_projects(domain)

        lines.append(f"{'='*20}")
        lines.append(f"【{domain.upper()}】")
        lines.append("")

        # 活跃项目
        if active_proj:
            lines.append(f"活跃项目 ({len(active_proj)}):")
            for p in active_proj:
                lines.append(f"  ✅ {p['name']} — {p['desc']}")
            lines.append("")

        # 冷门项目
        if stale_proj:
            lines.append(f"冷门项目 ({len(stale_proj)}):")
            for p in stale_proj:
                lines.append(f"  ⚠️ {p['name']} — {p['days']}天未活跃")
                all_stale.append(f"[{domain}] {p['name']}")
            lines.append("")

        # 本月活动统计
        lines.append(f"本月活动: {len(entries)} 条记录")
        if entries:
            # 按 operation 分类统计
            ops = {}
            for e in entries:
                parts = e["title"].split("|")
                op = parts[0].strip() if parts else "other"
                ops[op] = ops.get(op, 0) + 1
            for op, count in sorted(ops.items(), key=lambda x: -x[1]):
                lines.append(f"  • {op}: {count}次")
        lines.append("")

    # 底部操作提示
    lines.append("---")
    if all_stale:
        lines.append(f"有 {len(all_stale)} 个冷门项目，逐个回复:")
        for s in all_stale:
            lines.append(f"  「归档 {s.split('] ')[1]}」或「继续 {s.split('] ')[1]}」")
        lines.append("")
    lines.append("回复「周会」看本周详情")
    lines.append("回复「复盘」做深度回顾")

    return "\n".join(lines)


def main():
    dry_run = "--dry-run" in sys.argv
    review = build_monthly_review()

    print(review)
    print()

    if dry_run:
        print("[monthly] dry-run 模式，不发送")
    else:
        send_feishu_message(review, tag="monthly")


if __name__ == "__main__":
    main()
