#!/usr/bin/env python3
"""
Wiki index auto-reorganizer: sort by active date, surface stale entries.
Finds entries inactive for 30+ days and generates a question list.

Usage:
  python3 reorganize-index.py              # Reorganize and print results
  python3 reorganize-index.py --ask        # Reorganize and send questions via IM
"""

import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from feishu_utils import send_feishu_message
except ImportError:
    send_feishu_message = None

CLAWD_DIR = Path.home() / ".clawd"
STALE_DAYS = 30
TIER_THRESHOLD = 50  # Split hot/cold tiers above this entry count


def parse_index(path):
    """Parse index.md, extract entries and active dates."""
    if not path.exists():
        return "", []

    lines = path.read_text().strip().split("\n")
    sections = []
    current_section = None
    current_items = []
    preamble = []

    for line in lines:
        if line.startswith("## "):
            if current_section:
                sections.append((current_section, current_items))
            current_section = line
            current_items = []
            continue

        if current_section is None:
            preamble.append(line)
            continue

        match = re.match(r'^- \[(.+?)\]\((.+?)\)\s+[—\-]+\s+(.+?)(?:\s+`active:(\d{4}-\d{2}-\d{2})`)?$', line)
        if match:
            name, link, desc, active_date = match.groups()
            try:
                active = datetime.strptime(active_date, "%Y-%m-%d") if active_date else datetime(2020, 1, 1)
            except ValueError:
                print(f"[reorganize] Warning: malformed date '{active_date}', skipping")
                active = datetime(2020, 1, 1)
            current_items.append({
                "name": name,
                "link": link,
                "desc": desc,
                "active": active,
                "raw": line
            })
        elif line.strip() and not line.startswith("#"):
            current_items.append({"raw": line, "active": None})

    if current_section:
        sections.append((current_section, current_items))

    return preamble, sections


def sort_and_find_stale(sections):
    """Sort by active date, find stale entries."""
    stale = []
    cutoff = datetime.now() - timedelta(days=STALE_DAYS)

    for section_title, items in sections:
        sortable = [i for i in items if i.get("active") is not None]
        unsortable = [i for i in items if i.get("active") is None]

        sortable.sort(key=lambda x: x["active"], reverse=True)

        for item in sortable:
            if item["active"] < cutoff:
                stale.append((section_title, item))

        items.clear()
        items.extend(sortable + unsortable)

    return stale


def rebuild_index(preamble, sections):
    """Rebuild index.md content."""
    trimmed = list(preamble)
    while trimmed and not trimmed[-1].strip():
        trimmed.pop()
    lines = trimmed + [""]
    for section_title, items in sections:
        lines.append(section_title)
        for item in items:
            if item.get("name") and item.get("active"):
                lines.append(f'- [{item["name"]}]({item["link"]}) — {item["desc"]} `active:{item["active"].strftime("%Y-%m-%d")}`')
            else:
                lines.append(item["raw"])
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def tier_split(sections):
    """When total entries exceed TIER_THRESHOLD, split cold entries into archive."""
    cutoff = datetime.now() - timedelta(days=STALE_DAYS)

    total = sum(1 for _, items in sections for i in items if i.get("active") is not None)
    if total <= TIER_THRESHOLD:
        return sections, [], 0

    hot_sections = []
    cold_sections = []
    cold_count = 0

    for section_title, items in sections:
        hot_items = []
        cold_items = []
        for item in items:
            if item.get("active") is None:
                hot_items.append(item)
            elif item["active"] >= cutoff:
                hot_items.append(item)
            else:
                cold_items.append(item)
                cold_count += 1
        hot_sections.append((section_title, hot_items))
        if cold_items:
            cold_sections.append((section_title, cold_items))

    return hot_sections, cold_sections, cold_count


def main():
    ask_mode = "--ask" in sys.argv
    questions = []

    for domain in ["work", "life"]:
        index_path = CLAWD_DIR / domain / "wiki" / "index.md"
        archive_path = CLAWD_DIR / domain / "wiki" / "index-archive.md"
        preamble, sections = parse_index(index_path)

        if not sections:
            continue

        stale = sort_and_find_stale(sections)

        hot_sections, cold_sections, cold_count = tier_split(sections)

        if cold_count > 0:
            new_content = rebuild_index(preamble, hot_sections)
            index_path.write_text(new_content)

            if archive_path.exists():
                _, existing_cold = parse_index(archive_path)
                merged = {}
                for title, items in existing_cold + cold_sections:
                    if title not in merged:
                        merged[title] = []
                    existing_links = {i.get("link") for i in merged[title] if i.get("link")}
                    for item in items:
                        if item.get("link") and item["link"] not in existing_links:
                            merged[title].append(item)
                            existing_links.add(item["link"])
                        elif not item.get("link"):
                            merged[title].append(item)
                cold_sections = list(merged.items())

            archive_preamble = [f"# {domain.title()} Wiki Index (Archive)", "",
                                f"> Entries inactive for {STALE_DAYS}+ days are automatically moved here. The secretary checks as needed."]
            archive_content = rebuild_index(archive_preamble, cold_sections)
            archive_path.write_text(archive_content)
            print(f"[reorganize] {domain}: {cold_count} stale entries moved to index-archive.md")
        else:
            new_content = rebuild_index(preamble, sections)
            index_path.write_text(new_content)

        print(f"[reorganize] {domain}/wiki/index.md sorted by activity")

        for section, item in stale:
            days = (datetime.now() - item["active"]).days
            questions.append(f"[{domain}] {item['name']}: inactive for {days} days. Still in progress? Archive it?")

    if questions:
        print(f"\n[reorganize] Found {len(questions)} stale entries:")
        for q in questions:
            print(f"  - {q}")

        if ask_mode and send_feishu_message:
            msg_lines = ["Wiki Reorganization Reminder", ""]
            for q in questions:
                msg_lines.append(f"- {q}")
            msg_lines.append("")
            msg_lines.append("Reply 'archive <project>' or 'resume <project>' to decide")
            send_feishu_message("\n".join(msg_lines), tag="reorganize")
    else:
        print("[reorganize] All entries active, nothing to ask about")


if __name__ == "__main__":
    main()
