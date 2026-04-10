#!/usr/bin/env python3
"""
Wiki 自动维护：LLM 定期苏醒，整理知识库。
参考 Andrej Karpathy 的 LLM Wiki 设计模式。

定时：每月第一个周六 09:07 运行（保证在 6/7 号前完成）
方式：调用 claude -p 执行全面维护，结果发飞书通知

用法:
  python3 wiki-maintenance.py           # 执行维护
  python3 wiki-maintenance.py --dry-run # 只打印 prompt 不执行
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
        return "（空）"

def build_prompt():
    work_idx = read_file(CLAWD_DIR / "work/wiki/index.md")
    life_idx = read_file(CLAWD_DIR / "life/wiki/index.md")
    shared_idx = read_file(CLAWD_DIR / "shared-wiki/index.md")

    # 最近 30 天的 log
    work_log = read_file(CLAWD_DIR / "work/wiki/log.md", max_lines=20)
    life_log = read_file(CLAWD_DIR / "life/wiki/log.md", max_lines=20)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    return f"""你是 Wiki 维护员。现在是 {now}，执行月度自动维护。

## 当前知识库状态

### Work 域 index:
{work_idx}

### Life 域 index:
{life_idx}

### Shared Wiki index:
{shared_idx}

### Work 域最近 log:
{work_log}

### Life 域最近 log:
{life_log}

## 维护任务（按顺序执行）

### 1. 健康检查 (Lint)
- 读取所有 wiki 页面，检查 [[wiki-link]] 是否都有对应文件
- 检查 index.md 列出的页面是否都存在
- 找出孤立页面（存在但没被 index 或其他页面引用）
- 找出空页面或只有 frontmatter 的页面
- 检查 frontmatter 的 updated 日期是否与实际内容最后修改时间大致吻合

### 2. 交叉引用更新
- 检查页面之间应该有但缺失的 [[wiki-link]]
- 在相关页面的 linked_from 字段补充缺失的引用
- 确保 linked_from 列表准确（不指向已删除的页面）

### 3. Index 整理
- 按 active 日期降序排列（活跃的在前）
- 标记 30+ 天未活跃的项目为 stale
- 确保每个条目的一句话描述准确反映页面当前内容

### 4. 内容质量
- 检查页面内容是否过时（对比 log.md 记录的最近操作）
- 如果发现明显过时的描述，直接更新
- 确保 shared-wiki/boss-profile.md 和 coding-style.md 内容连贯

### 5. Pattern Drift 检测（内容与源头一致性）
- 检查 wiki 页面的 sources 字段是否指向有效的 raw source 或 GitHub 仓库
- 用 Bash 运行 `git -C ~/仓库名 log --oneline -5` 检查各 GitHub 仓库最近 commit
- 如果仓库有近期活跃但 wiki 页面 updated 日期明显滞后（>14天），标记为 drift
- 在有 drift 的页面追加 `> [!drift] Wiki 描述可能与仓库当前状态不符，待确认`
- 汇总 drift 情况到维护报告

### 6. 生成维护报告
完成后，在 shared-wiki/log.md 追加一条维护记录:
## [{now}] maintenance | 月度 Wiki 维护

报告内容包括：
- 发现的问题数量和修复情况
- 新增/更新的交叉引用
- 标记为 stale 的项目
- 知识库整体健康度评估（一句话）

### 规则
- 中文输出
- 可以直接修复明确的问题（死链、缺失引用、过时描述）
- 不要删除任何页面
- 不要修改 raw sources
- 每次修改都在 log 里记录
- 完成后输出一段简短的维护摘要（给 boss 看的）"""


def main():
    dry_run = "--dry-run" in sys.argv
    prompt = build_prompt()

    if dry_run:
        print(prompt)
        return

    # 先跑快速 lint
    from wiki_lint import lint_all
    pre_issues, pre_stats = lint_all()
    print(f"[wiki-maintenance] pre-lint: {len(pre_issues)} issues, {pre_stats['pages']} pages")

    print(f"[wiki-maintenance] 开始执行，日志: {LOG_FILE}")

    try:
        result = subprocess.run(
            [str(REAL_CLAUDE), "-p", prompt,
             "--allowedTools", "Read,Edit,Write,Bash,Glob,Grep",
             "--max-turns", "15",
             "--output-format", "text"],
            capture_output=True, text=True, timeout=600,
            cwd=str(CLAWD_DIR)
        )
        output = result.stdout.strip() or "(无输出)"
        if result.returncode != 0:
            output += f"\n[stderr] {result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        output = "维护超时（10分钟限制）"
    except Exception as e:
        output = f"维护失败: {e}"

    # 写日志
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().isoformat()}]\n{output}\n{'='*60}\n")

    # post-lint
    post_issues, post_stats = lint_all()
    lint_delta = len(pre_issues) - len(post_issues)

    # telemetry
    try:
        from telemetry import log_op
        log_op("maintenance", domain="both", pages_touched=post_stats["pages"],
               status="ok" if result.returncode == 0 else "error",
               detail=f"pre:{len(pre_issues)} post:{len(post_issues)} fixed:{lint_delta}",
               source="cron")
    except Exception:
        pass

    # 发飞书通知
    summary = output[:400] if len(output) > 400 else output
    lint_info = f"\n\nLint: {len(pre_issues)}→{len(post_issues)} issues ({lint_delta} fixed)"
    send_feishu_message(f"Wiki 月度维护完成\n\n{summary}{lint_info}", tag="wiki-maintenance")

    print(f"[wiki-maintenance] 完成")


if __name__ == "__main__":
    main()
