#!/usr/bin/env python3
"""
Wiki index 自动整理：按 active 日期排序，活跃的在前，冷门的沉底。
找出 30 天未活跃的条目，生成提问清单。

用法:
  python3 reorganize-index.py              # 整理并打印结果
  python3 reorganize-index.py --ask        # 整理并通过飞书/微信发提问
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
TIER_THRESHOLD = 50  # 超过此条目数时拆分热区/冷区


def parse_index(path):
    """解析 index.md，提取条目和 active 日期"""
    if not path.exists():
        return "", [], []

    lines = path.read_text().strip().split("\n")
    sections = []
    current_section = None
    current_items = []
    preamble = []  # title + 首个 ## 之前的内容

    for line in lines:
        # 检测 section 标题
        if line.startswith("## "):
            if current_section:
                sections.append((current_section, current_items))
            current_section = line
            current_items = []
            continue

        # 首个 section 之前的内容保留到 preamble
        if current_section is None:
            preamble.append(line)
            continue

        # 解析条目行（兼容 em-dash 和普通 dash）
        match = re.match(r'^- \[(.+?)\]\((.+?)\)\s+[—\-]+\s+(.+?)(?:\s+`active:(\d{4}-\d{2}-\d{2})`)?$', line)
        if match:
            name, link, desc, active_date = match.groups()
            try:
                active = datetime.strptime(active_date, "%Y-%m-%d") if active_date else datetime(2020, 1, 1)
            except ValueError:
                print(f"[reorganize] 警告: 日期格式异常 '{active_date}'，跳过")
                active = datetime(2020, 1, 1)
            current_items.append({
                "name": name,
                "link": link,
                "desc": desc,
                "active": active,
                "raw": line
            })
        elif line.strip() and not line.startswith("#"):
            # 非条目行（如 _暂无_），原样保留
            current_items.append({"raw": line, "active": None})

    if current_section:
        sections.append((current_section, current_items))

    return preamble, sections


def sort_and_find_stale(sections):
    """按 active 日期排序，找出过期条目"""
    stale = []
    cutoff = datetime.now() - timedelta(days=STALE_DAYS)

    for section_title, items in sections:
        # 分离可排序和不可排序的条目
        sortable = [i for i in items if i.get("active") is not None]
        unsortable = [i for i in items if i.get("active") is None]

        # 按 active 降序排列（最近的在前）
        sortable.sort(key=lambda x: x["active"], reverse=True)

        # 找出过期的
        for item in sortable:
            if item["active"] < cutoff:
                stale.append((section_title, item))

        # 替换回 items
        items.clear()
        items.extend(sortable + unsortable)

    return stale


def rebuild_index(preamble, sections):
    """重建 index.md"""
    # 去掉 preamble 尾部空行，再加一个空行分隔
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
    """当条目总数超过 TIER_THRESHOLD 时，把冷门条目拆到 archive sections"""
    cutoff = datetime.now() - timedelta(days=STALE_DAYS)

    # 统计总可排序条目数
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
                hot_items.append(item)  # 非条目行留在热区
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

        # 分层拆分：热区留 index.md，冷区移到 index-archive.md
        hot_sections, cold_sections, cold_count = tier_split(sections)

        if cold_count > 0:
            # 写热区
            new_content = rebuild_index(preamble, hot_sections)
            index_path.write_text(new_content)

            # 读已有冷区存档（如果有），合并
            if archive_path.exists():
                _, existing_cold = parse_index(archive_path)
                # 按 section title 合并
                merged = {}
                for title, items in existing_cold + cold_sections:
                    if title not in merged:
                        merged[title] = []
                    # 去重（按 link）
                    existing_links = {i.get("link") for i in merged[title] if i.get("link")}
                    for item in items:
                        if item.get("link") and item["link"] not in existing_links:
                            merged[title].append(item)
                            existing_links.add(item["link"])
                        elif not item.get("link"):
                            merged[title].append(item)
                cold_sections = list(merged.items())

            archive_preamble = [f"# {domain.title()} Wiki Index (Archive)", "",
                                f"> {STALE_DAYS} 天未活跃的条目自动归入此文件，秘书按需检索。"]
            archive_content = rebuild_index(archive_preamble, cold_sections)
            archive_path.write_text(archive_content)
            print(f"[reorganize] {domain}: {cold_count} 条冷门条目移入 index-archive.md")
        else:
            # 没有冷区拆分，只重排
            new_content = rebuild_index(preamble, sections)
            index_path.write_text(new_content)

        print(f"[reorganize] {domain}/wiki/index.md 已按活跃度重排")

        # 收集过期条目的提问
        for section, item in stale:
            days = (datetime.now() - item["active"]).days
            questions.append(f"[{domain}] {item['name']}：已 {days} 天未活跃。还在进行中吗？要不要归档？")

    if questions:
        print(f"\n[reorganize] 发现 {len(questions)} 个冷门条目:")
        for q in questions:
            print(f"  - {q}")

        if ask_mode and send_feishu_message:
            msg_lines = ["Wiki 整理提醒", ""]
            for q in questions:
                msg_lines.append(f"- {q}")
            msg_lines.append("")
            msg_lines.append("回复「归档 项目名」或「继续 项目名」来决定")
            send_feishu_message("\n".join(msg_lines), tag="reorganize")
    else:
        print("[reorganize] 所有条目都活跃，无需提问")


if __name__ == "__main__":
    main()
