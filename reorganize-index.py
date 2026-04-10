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
from feishu_utils import send_feishu_message

CLAWD_DIR = Path.home() / ".clawd"
STALE_DAYS = 30


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


def main():
    ask_mode = "--ask" in sys.argv
    questions = []

    for domain in ["work", "life"]:
        index_path = CLAWD_DIR / domain / "wiki" / "index.md"
        preamble, sections = parse_index(index_path)

        if not sections:
            continue

        stale = sort_and_find_stale(sections)

        # 重写排序后的 index
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

        if ask_mode:
            msg_lines = ["📋 Wiki 整理提醒", ""]
            for q in questions:
                msg_lines.append(f"• {q}")
            msg_lines.append("")
            msg_lines.append("回复「归档 项目名」或「继续 项目名」来决定")
            send_feishu_message("\n".join(msg_lines), tag="reorganize")
    else:
        print("[reorganize] 所有条目都活跃，无需提问")


if __name__ == "__main__":
    main()
