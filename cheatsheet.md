# 实习生 Agent 快捷指令大全

> 最后更新：2026-04-10
> 高频 10 个用法在最下面，先记那 10 个就够日常用。

## 一、系统级入口（不开任何对话窗口）

| 触发 | 做什么 |
|---|---|
| **`⌃⌥C`** 全局快捷键 | 任何 app：选中文字 → `⌘C` → `⌃⌥C` → 一键存进 inbox + 通知 |
| **`clawd`** 终端命令 | 任何目录敲一个词 → 自动 cd 到 `~/.clawd` + 启动 claude（进秘书模式） |
| **`inbox`** 终端命令 | 终端里敲一个词 → 等同于 ⌃⌥C，把剪贴板存进 inbox.md |
| **`cti`** 终端命令 | 启动 IM bridge daemon（手机通道，需另装） |

## 二、秘书对话命令（在 claude session 里直接说）

| 触发词 | 做什么 |
|---|---|
| **站会** / 早 / standup | 读 log.md，简要汇报最近做了什么 |
| **周会** / weekly / 周报 | 全面回顾 + 建议 + 反向提问 |
| **复盘** / reflect | 引导式回顾，写入 `life/wiki/reflections/` |
| **处理 inbox** / inbox | 读 inbox.md，分门别类写到 work / life wiki，处理完清空 |
| **归档 项目名** | 把项目标记为 archived |
| **继续 项目名** | 刷新该项目的 active 日期到今天 |
| **检查** / lint | wiki 健康检查（孤立页、空页、死链、过期页） |
| **导入历史** / import history | 导入历史 CC session 到 wiki，自动分类归档 |
| **关系图** / graph | 生成 wiki 关系图（浏览器打开） |

直接用自然语言说就行，秘书会路由到对应 ritual。

## 三、Session 路由（任何 cwd 的 claude session 都能用）

| 命令 | 做什么 |
|---|---|
| `~/.claude/hooks/mark-session-project.sh <路径> [标题]` | 标记当前 session 归属哪个项目，session 退出后自动搬 jsonl |

例：
```bash
~/.claude/hooks/mark-session-project.sh ~/some-project "feature work"
~/.claude/hooks/mark-session-project.sh ~/.clawd "secretary maintenance"
```

实际很少手动跑 —— 在 ~ 启动的 session 里直接跟 claude 说"今天来做 X 项目"，claude 会按 `~/.claude/CLAUDE.md` 里的规则自动调这个脚本。

## 四、手动维护脚本（偶尔用）

| 脚本 | 做什么 |
|---|---|
| `python3 ~/.clawd/wiki-lint.py` | 跑 wiki 健康检查，输出报告 |
| `python3 ~/.clawd/wiki-maintenance.py` | 月度全面维护（cron 自动跑） |
| `python3 ~/.clawd/weekly-report.py` | 生成周报 |
| `python3 ~/.clawd/monthly-review.py` | 月度复盘 |
| `python3 ~/.clawd/import-history.py --scan` | 扫描历史 session（不提取） |
| `python3 ~/.clawd/wiki-graph.py` | 生成 wiki 关系图 |
| `~/.clawd/collect.sh --process` | 让秘书立刻处理 inbox（等同于对话里说"处理 inbox"） |

---

## 高频 10 个（先记这些）

| # | 触发 | 场景 |
|---|---|---|
| 1 | **`⌃⌥C`** | 看到东西想存 |
| 2 | **`clawd`** | 想跟秘书聊 |
| 3 | **「站会」** | 想知道最近做了啥 |
| 4 | **「周会」** | 想要全面回顾 |
| 5 | **「处理 inbox」** | 让秘书消化 inbox |
| 6 | **「复盘 X」** | 项目反思 |
| 7 | **「归档 X」** | 项目结束 |
| 8 | **「继续 X」** | 项目重启 |
| 9 | **「导入历史」** | 把历史 CC session 导入 wiki |
| 10 | **「关系图」** | 生成 wiki 关系图 |
