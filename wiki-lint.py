#!/usr/bin/env python3
"""
Wiki 快速 lint：验证结构完整性。
可被其他脚本 import 调用，也可独立运行。

用法:
  python3 wiki-lint.py           # 全量检查，输出报告
  python3 wiki-lint.py --quiet   # 只在有问题时输出
"""

import re
import sys
from pathlib import Path

CLAWD_DIR = Path.home() / ".clawd"
DOMAINS = [
    ("work", CLAWD_DIR / "work/wiki"),
    ("life", CLAWD_DIR / "life/wiki"),
    ("shared", CLAWD_DIR / "shared-wiki"),
]

def lint_all():
    """返回 (issues: list[str], stats: dict)"""
    issues = []
    stats = {"pages": 0, "links_ok": 0, "links_broken": 0, "orphans": 0}

    all_pages = {}  # relative_name -> Path
    all_referenced = set()  # pages referenced by wiki-links or index

    # 收集所有 md 文件
    for domain, wiki_dir in DOMAINS:
        if not wiki_dir.exists():
            continue
        for md in wiki_dir.rglob("*.md"):
            rel = md.relative_to(wiki_dir)
            key = f"{domain}/{rel}"
            all_pages[key] = md
            stats["pages"] += 1

    # 检查每个页面
    for key, md_path in all_pages.items():
        domain = key.split("/")[0]
        wiki_dir = dict(DOMAINS)[domain] if domain != "shared" else CLAWD_DIR / "shared-wiki"
        content = md_path.read_text(encoding="utf-8", errors="replace")

        # 1. frontmatter 检查
        if not content.strip().startswith("---") and md_path.name not in ("index.md", "log.md"):
            issues.append(f"[{key}] 缺少 YAML frontmatter")

        # 2. wiki-link 检查
        wiki_links = re.findall(r'\[\[([^\]]+)\]\]', content)
        for link in wiki_links:
            link_name = link.strip()
            # 尝试在同域 wiki 下查找，找不到则跨域查找
            found = False
            search_dirs = [(domain, wiki_dir)]
            for d, wd in DOMAINS:
                if d != domain:
                    search_dirs.append((d, wd))
            for search_domain, search_dir in search_dirs:
                if found:
                    break
                for subdir in ["projects", "decisions", "people", "patterns", "topics", "reflections", ""]:
                    candidate = search_dir / subdir / f"{link_name}.md" if subdir else search_dir / f"{link_name}.md"
                    if candidate.exists():
                        found = True
                        all_referenced.add(f"{search_domain}/{(candidate.relative_to(search_dir))}")
                        break
            if found:
                stats["links_ok"] += 1
            else:
                stats["links_broken"] += 1
                issues.append(f"[{key}] 死链: [[{link_name}]] 找不到对应文件")

        # 3. 空页面检查（只有 frontmatter 没有正文）
        body = re.sub(r'^---.*?---\s*', '', content, flags=re.DOTALL).strip()
        if not body and md_path.name not in ("index.md", "log.md"):
            issues.append(f"[{key}] 空页面（只有 frontmatter）")

    # 4. index 一致性检查
    for domain, wiki_dir in DOMAINS:
        index_path = wiki_dir / "index.md"
        if not index_path.exists():
            continue
        index_content = index_path.read_text(encoding="utf-8", errors="replace")
        # 提取 index 中引用的文件路径
        index_links = re.findall(r'\[.*?\]\(([^)]+)\)', index_content)
        for link in index_links:
            target = wiki_dir / link
            ref_key = f"{domain}/{link}"
            all_referenced.add(ref_key)
            if not target.exists():
                issues.append(f"[{domain}/index.md] 索引指向不存在的文件: {link}")

    # 5. 孤立页面检查（排除 index.md, log.md, schema.md）
    skip_names = {"index.md", "log.md", "schema.md"}
    for key, md_path in all_pages.items():
        if md_path.name in skip_names:
            continue
        if key not in all_referenced:
            stats["orphans"] += 1
            issues.append(f"[{key}] 孤立页面（未被 index 或其他页面引用）")

    return issues, stats


def main():
    quiet = "--quiet" in sys.argv
    issues, stats = lint_all()

    if quiet and not issues:
        return

    print(f"Wiki Lint Report")
    print(f"  Pages: {stats['pages']}")
    print(f"  Links OK: {stats['links_ok']}, Broken: {stats['links_broken']}")
    print(f"  Orphans: {stats['orphans']}")
    print(f"  Issues: {len(issues)}")

    if issues:
        print()
        for issue in issues:
            print(f"  ⚠ {issue}")
        sys.exit(1)
    else:
        print("  ✓ All clean")


if __name__ == "__main__":
    main()
