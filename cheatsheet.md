# intern-clawd Command Cheatsheet

> Last updated: 2026-04-14
> The top 10 commands are at the bottom — start there.

## 1. System-Level Entry Points (no conversation window needed)

| Trigger | What it does |
|---|---|
| **`ctrl+opt+C`** global hotkey | Any app: select text -> `Cmd+C` -> `ctrl+opt+C` -> saved to inbox + notification |
| **`clawd`** terminal command | Type one word in any directory -> auto cd to `~/.clawd` + launch claude (secretary mode) |
| **`inbox`** terminal command | Type one word in terminal -> same as ctrl+opt+C, saves clipboard to inbox.md |
| **`cti`** terminal command | Start IM bridge daemon (mobile channel, requires separate install) |

## 2. Secretary Conversation Commands (say these in a claude session)

| Trigger | What it does |
|---|---|
| **standup** / 站会 / 早 | Read log.md, brief status update |
| **weekly** / 周会 / 周报 | Full review + suggestions + follow-up questions |
| **reflect** / 复盘 | Guided retrospective, writes to `life/wiki/reflections/` |
| **process inbox** / inbox / 处理inbox | Read inbox.md, classify into work/life wiki, clear when done |
| **archive \<project\>** / 归档 | Mark project as archived |
| **resume \<project\>** / 继续 | Refresh project's active date to today |
| **lint** / check / 检查 | Wiki health check (orphaned pages, empty pages, broken links, stale entries) |
| **import history** / 导入历史 | Import historical CC sessions into wiki, auto-classify |
| **graph** / 关系图 | Generate wiki knowledge graph (opens in browser) |

Just say it in natural language — the secretary routes to the right ritual.

## 3. Session Routing (works in any claude session, any cwd)

| Command | What it does |
|---|---|
| `~/.claude/hooks/mark-session-project.sh <path> [title]` | Tag current session to a project, auto-relocates jsonl on session exit |

Example:
```bash
~/.claude/hooks/mark-session-project.sh ~/some-project "feature work"
~/.claude/hooks/mark-session-project.sh ~/.clawd "secretary maintenance"
```

You rarely need to run this manually — just tell claude "working on project X today" in a session started from `~`, and it auto-calls this script per the rules in `~/.claude/CLAUDE.md`.

## 4. Manual Maintenance Scripts (occasional use)

| Script | What it does |
|---|---|
| `python3 ~/.clawd/wiki-lint.py` | Run wiki health check, output report |
| `python3 ~/.clawd/wiki-maintenance.py` | Weekly maintenance (auto-runs eve of quota reset, `--force` to override) |
| `python3 ~/.clawd/weekly-report.py` | Generate weekly report |
| `python3 ~/.clawd/monthly-review.py` | Monthly review |
| `python3 ~/.clawd/import-history.py --scan` | Scan historical sessions (don't extract) |
| `python3 ~/.clawd/wiki-graph.py` | Generate wiki knowledge graph |
| `~/.clawd/collect.sh --process` | Have secretary process inbox now (same as saying "process inbox" in conversation) |

---

## Top 10 (start here)

| # | Trigger | When to use |
|---|---|---|
| 1 | **`ctrl+opt+C`** | See something worth saving |
| 2 | **`clawd`** | Want to talk to the secretary |
| 3 | **"standup"** | What have I been working on? |
| 4 | **"weekly"** | Full week review |
| 5 | **"process inbox"** | Let secretary digest inbox items |
| 6 | **"reflect X"** | Project retrospective |
| 7 | **"archive X"** | Project finished |
| 8 | **"resume X"** | Restart a project |
| 9 | **"import history"** | Import old CC sessions into wiki |
| 10 | **"graph"** | Generate wiki knowledge graph |
