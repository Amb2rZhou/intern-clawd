#!/usr/bin/env python3
"""
Wiki quick lint: verify structural integrity.
Can be imported by other scripts, or run standalone.

Usage:
  python3 wiki-lint.py           # Full check, print report
  python3 wiki-lint.py --quiet   # Only output if issues found
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
    """Return (issues: list[str], stats: dict)"""
    issues = []
    stats = {"pages": 0, "links_ok": 0, "links_broken": 0, "orphans": 0}

    all_pages = {}
    all_referenced = set()

    for domain, wiki_dir in DOMAINS:
        if not wiki_dir.exists():
            continue
        for md in wiki_dir.rglob("*.md"):
            rel = md.relative_to(wiki_dir)
            key = f"{domain}/{rel}"
            all_pages[key] = md
            stats["pages"] += 1

    for key, md_path in all_pages.items():
        domain = key.split("/")[0]
        wiki_dir = dict(DOMAINS)[domain] if domain != "shared" else CLAWD_DIR / "shared-wiki"
        content = md_path.read_text(encoding="utf-8", errors="replace")

        if not content.strip().startswith("---") and md_path.name not in ("index.md", "log.md"):
            issues.append(f"[{key}] Missing YAML frontmatter")

        wiki_links = re.findall(r'\[\[([^\]]+)\]\]', content)
        for link in wiki_links:
            link_name = link.strip()
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
                issues.append(f"[{key}] Broken link: [[{link_name}]] — no matching file")

        body = re.sub(r'^---.*?---\s*', '', content, flags=re.DOTALL).strip()
        if not body and md_path.name not in ("index.md", "log.md"):
            issues.append(f"[{key}] Empty page (frontmatter only)")

    for domain, wiki_dir in DOMAINS:
        index_path = wiki_dir / "index.md"
        if not index_path.exists():
            continue
        index_content = index_path.read_text(encoding="utf-8", errors="replace")
        index_links = re.findall(r'\[.*?\]\(([^)]+)\)', index_content)
        for link in index_links:
            target = wiki_dir / link
            ref_key = f"{domain}/{link}"
            all_referenced.add(ref_key)
            if not target.exists():
                issues.append(f"[{domain}/index.md] Index points to missing file: {link}")

    skip_names = {"index.md", "log.md", "schema.md"}
    for key, md_path in all_pages.items():
        if md_path.name in skip_names:
            continue
        if key not in all_referenced:
            stats["orphans"] += 1
            issues.append(f"[{key}] Orphaned page (not referenced by index or other pages)")

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
            print(f"  ! {issue}")
        sys.exit(1)
    else:
        print("  All clean")


if __name__ == "__main__":
    main()
