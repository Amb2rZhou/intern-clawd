# intern-clawd — A Personal Secretary OS for Claude Code

[![syntax](https://github.com/Amb2rZhou/intern-clawd/actions/workflows/syntax.yml/badge.svg)](https://github.com/Amb2rZhou/intern-clawd/actions/workflows/syntax.yml)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

把 Claude Code 从「每次失忆的编程工具」改造成「跨 session 长记性、跨设备多入口、有角色和仪式感的私人秘书」。

不是又一个 LLM wiki，是一个**完整的秘书操作系统**：知识库只是其中一个器官。

> **clawd** = **Claude** + **wd** (working directory)。一个驻留在 `~/.clawd/` 的秘书 agent，管理你的工作 / 生活两个域的知识库，覆盖从「想到 → 捕获 → 消化 → 检索 → 复盘」全链路。

---

## 跟同类项目的差异

| | intern-clawd | LLM Wiki 工具<br>(`llm-wiki-agent` 等) | LLM 记忆框架<br>(`mem0`, `letta`) | Obsidian + LLM<br>(`obsidian-mind` 等) |
|---|---|---|---|---|
| 双域（work / life） | ✅ | ❌ 单一 wiki | ❌ 通用记忆 | ❌ 单 vault |
| 角色化 ritual（站会/周会/复盘） | ✅ 7 个固定命令 | ❌ | ❌ | ❌ |
| 多入口 capture | ✅ 5+ 渠道 | ❌ 单入口 | ❌ API only | ⚠️ Obsidian only |
| Session 路由 hooks | ✅ 自动归档 jsonl | ❌ | ❌ | ❌ |
| 安装方式 | ✅ clone 到 `~/.clawd`，零服务器 | ⚠️ 需后端服务 | ⚠️ 需后端 / DB | ✅ 但绑定 Obsidian |
| 自维护（lint + 月度 maintenance） | ✅ | ⚠️ 部分 | ❌ | ❌ |

**核心差异**：别人在做「知识库 + LLM」，我们在做「**有人格的秘书 + 7 个仪式 + 5 个入口**」。Wiki 是这个秘书的笔记本，不是产品本身。

---

## 解决什么问题

裸 Claude Code 只是个「按 session 工作的编程助手」。当你想用它做更多事时，会撞上几个墙：

| 痛点 | clawd 怎么解 |
|---|---|
| 每开一个新 session 等于失忆 | 持久 wiki + 每次 SessionStart 自动注入 index |
| 必须坐下打开终端才能跟它说话 | 全局快捷键 `⌃⌥C` 一秒收集 / 终端 alias / 飞书 / 微信 / 桌面 bubble |
| 没有"角色"概念，每次都得重复 prompt | CLAUDE.md 里写死秘书人格 + 7 个固定 ritual（站会/周会/复盘/归档/继续/inbox/lint） |
| 工作和生活的笔记混在一起 | 双域架构：work/ + life/，独立 index 和 log |
| `~` 启动的 session 全堆在一个文件夹 | Session 路由 hooks 自动按项目搬 jsonl |
| 知识库容易腐烂 | wiki-lint + 月度自动维护 + post-write 自检 |

---

## 架构

```
┌──────────────── 入口 ────────────────┐
│ ⌃⌥C 全局快捷键   终端 alias `clawd`   │
│ 飞书 / 微信       桌面 bubble          │
└────────────────┬─────────────────────┘
                 │
                 ▼
        ┌────────────────┐
        │  秘书 Agent     │  ← CLAUDE.md (人格+规则)
        │  (Claude Code) │     双域 index 自动注入
        └───────┬────────┘
                │
        ┌───────┴────────┐
        ▼                ▼
   ┌────────┐       ┌────────┐
   │ work/  │       │ life/  │       ┌─────────────┐
   │ wiki/  │       │ wiki/  │  ←──  │ shared-wiki │
   │ raw/   │       │ raw/   │       │ (boss-      │
   └────────┘       └────────┘       │  profile)   │
                                     └─────────────┘

  raw/   ← 不可变事实源（agent 只读）
  wiki/  ← LLM 维护层（agent 读写）
  schema ← 约束层（人 + agent 共同维护）
```

知识层的三层架构直接借鉴 **Andrej Karpathy** 提出的 [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) 模式：把"事实源"和"LLM 综合层"严格分离，让 agent 只能 Read raw 不能 Write，避免幻觉污染源头。详细思想见 Karpathy 的 gist 原文。

intern-clawd 在此基础上扩展：在 wiki 层之上叠加了**角色 + 仪式 + 多入口**，把"知识库"变成"秘书"。

---

## Quick Start（5 分钟看到效果）

想先看效果再决定要不要全装？跑这 4 行：

```bash
git clone https://github.com/Amb2rZhou/intern-clawd.git ~/.clawd
cd ~/.clawd && bash setup.sh
echo "我是 $(whoami)，今天想试试 intern-clawd 这个秘书系统。" > shared-wiki/boss-profile.md
claude
```

进 Claude session 后直接说 **「站会」**——秘书会读 `life/wiki/log.md`（现在是空的），跟你打招呼，问你想从哪开始。这就是最小可用形态。

再多花 1 分钟试这个：在任何 app 选中一段文字 → `⌃C` → 在终端跑 `~/.clawd/collect.sh` → 回到秘书 session 说 **「处理 inbox」**——它会把你刚才存的东西归档到对应域 wiki。

**满意了再继续装** ⌃⌥C 全局快捷键、Claude Code hooks、cron 定时任务等完整入口（下面 §1-§5）。**不满意就** `bash uninstall.sh` 一键清干净。

---

## 安装

### 0. 前置依赖

- macOS 14+ / Linux（已验证 macOS Sequoia 15.6）
- Python 3.9+
- [Claude Code CLI](https://docs.claude.com/claude-code) 已装好且 `claude` 在 PATH 里
- git

### 1. Clone

```bash
git clone https://github.com/Amb2rZhou/intern-clawd.git ~/.clawd
cd ~/.clawd
```

### 2. 跑 setup.sh

```bash
bash setup.sh
```

会自动：
- 检查依赖
- 创建 work/life wiki 目录骨架
- 配置 `~/.claude/CLAUDE.md` 注入 wiki sync 规则
- 设置 cron（每日 9:07 AM 整理 wiki）

### 3. 写你的画像

```bash
$EDITOR shared-wiki/boss-profile.md
```

填写身份、偏好、当前目标、红线 —— 这是秘书了解你的唯一来源。

### 4. 装快捷入口（手动）

详细步骤见 [`docs/setup-new-machine.md`](setup-new-machine.md)。简版：

**zsh aliases**（写到 `~/.zshrc`）：

```bash
alias clawd='cd ~/.clawd && claude'
alias inbox='~/.clawd/collect.sh'
```

**全局快捷键 `⌃⌥C` 收集到 inbox**（macOS）：

1. 打开 Shortcuts.app，新建 shortcut
2. 加「运行 Shell 脚本」action，内容：`/Users/$USER/.clawd/collect.sh`（绝对路径）
3. 加「显示通知」action（macOS Sequoia 上 osascript 通知会失败，必须用这个）
4. 系统设置 → 键盘 → 键盘快捷键 → 服务 → 快捷指令 → 找到这条 → 双击右边绑 `⌃⌥C`

⚠️ **不要用** `create-quick-action.sh` —— 它用 Automator 路线，在 Sequoia 已经不兼容。

### 5. 装 Claude Code hooks（可选但推荐）

```bash
mkdir -p ~/.claude/hooks
cp claude-hooks/* ~/.claude/hooks/
```

然后在 `~/.claude/settings.json` 加：

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "$HOME/.clawd/hooks/inject-wiki-context.sh" }] }
    ],
    "SessionEnd": [
      { "hooks": [{ "type": "command", "command": "/usr/bin/python3 $HOME/.claude/hooks/session-relocate.py" }] }
    ]
  }
}
```

---

## 用法（高频 8 个）

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

完整命令清单见 [`cheatsheet.md`](cheatsheet.md)。

---

## 文件结构

```
.
├── CLAUDE.md                  # 秘书人格 + 规则（cwd 在 .clawd 时 Claude Code 自动加载）
├── schema.md                  # 全局 schema（agent 行为约束）
├── README.md                  # 本文件
├── cheatsheet.md              # 快捷命令大全
├── setup-new-machine.md       # 完整迁移/安装手册（含已知坑速查）
│
├── setup.sh                   # 一键初始化
├── claude-wrapper.sh          # 秘书 wrapper（特殊命令硬路由）
├── collect.sh                 # 剪贴板 → inbox 收集
├── extract-session.py         # SessionEnd: 提取对话到 raw/sessions/
│
├── wiki-lint.py               # wiki 健康检查
├── wiki-maintenance.py        # 月度全面维护（cron）
├── reorganize-index.py        # 每日 index 整理
├── weekly-report.py           # 周报生成
├── monthly-review.py          # 月度复盘
├── telemetry.py               # 操作日志（jsonl）
│
├── feishu_utils.py            # 飞书 API（可选）
├── feishu-send.sh             # 飞书发送（可选）
├── config.env.example         # Claude-to-IM bridge 配置模板（可选）
│
├── hooks/
│   ├── inject-wiki-context.sh # SessionStart hook（cwd 门控）
│   └── permission-router.sh   # PermissionRequest 智能路由
│
├── claude-hooks/              # 装到 ~/.claude/hooks/
│   ├── mark-session-project.sh
│   └── session-relocate.py
│
├── work/
│   ├── schema.md
│   ├── wiki/
│   │   ├── index.md           # 工作域 index
│   │   ├── log.md             # 工作时间线
│   │   ├── projects/
│   │   ├── people/
│   │   ├── decisions/
│   │   └── patterns/
│   └── raw/                   # 不可变源
│
├── life/
│   ├── schema.md
│   ├── wiki/
│   │   ├── index.md
│   │   ├── log.md
│   │   ├── projects/
│   │   ├── topics/
│   │   ├── reflections/
│   │   └── patterns/
│   └── raw/
│
└── shared-wiki/
    ├── index.md
    ├── boss-profile.md        # ⭐ 首次安装必填
    └── coding-style.md
```

---

## 已知坑（macOS Sequoia 15.6 实测）

| 症状 | 修法 |
|---|---|
| Quick Action workflow 在 Sequoia 不兼容 | 改用 Shortcuts.app（README §4） |
| osascript 通知静默失败 | 用 Shortcuts 内置「显示通知」action |
| Shortcuts 信息面板的快捷键不同步 | 手动到系统设置 → 键盘快捷键里再绑一遍 |
| Quick Action 沙盒不展开 `~` | 一律用绝对路径 `/Users/$USER/.clawd/...` |

完整坑表见 [`setup-new-machine.md`](setup-new-machine.md) §5。

---

## Risks & Uninstall

装这个会动你机器上几个全局文件（`~/.claude/CLAUDE.md`、`settings.json`、`crontab`、`~/.zshrc`）。**装之前请读** [`RISKS.md`](RISKS.md) —— 完整列出所有已知风险、影响范围、缓解措施，以及作者明确说"没修"的地方。

**承诺**：装了 intern-clawd **不会影响你在 `~/.clawd` 之外跑裸 Claude Code 的能力**。
- 全局 CLAUDE.md 注入的规则已经软化为「仅当 ~/.clawd 存在」，对无关项目零干扰
- SessionStart hook 在非秘书 cwd 用纯 bash 几毫秒早返回，不启动 python3
- cwd 就是天然的模式开关：进 `~/.clawd` = 秘书模式，离开 = 完全裸 CC

**一键卸载**：

```bash
bash uninstall.sh
```

会做：备份所有要改的文件 → 移除全局 CLAUDE.md 的 wiki 同步段 → 清理 settings.json hooks → 清理 crontab → 清理 zsh alias → 询问是否删 ~/.clawd 数据（默认不删，需要二次确认）→ 生成 `restore.sh` 反悔可一键还原。

详情见 [`RISKS.md`](RISKS.md) 「怎么撤掉」section。

---

## 设计原则

- **认知卸载优先于 token 节省** —— 让你少想，比让 LLM 少花钱重要
- **入口多样化** —— 看到东西想记的时候，总能在 3 秒内存下来
- **角色 > 工具** —— 秘书有人格、有仪式、有偏好，不是通用 chatbot
- **持久层不可变** —— raw/ 目录 agent 只读，避免幻觉污染源头
- **自检 > 人工维护** —— wiki-lint + post-write 自检 + 月度 maintenance，系统照顾自己

---

## 不在这个 repo 里的可选集成

下面这些是 **clawd 友好但独立** 的项目，不强依赖：

- **Mr. Krabs.app** — 桌面 bubble，权限审批 + 通知
- **Claude-to-IM bridge** — 手机渠道（飞书 / 微信）

按需自行集成。

---

## 致谢 & 灵感来源

- **[Andrej Karpathy](https://karpathy.ai/)** — [LLM Wiki 三层架构](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)（raw / wiki / schema）。intern-clawd 知识层完全建立在这个模式之上。
- **[Claude Code](https://docs.claude.com/claude-code)** — 整套 hook 系统、CLAUDE.md 注入机制、SessionStart/SessionEnd 生命周期的基石。
- 同类项目调研：[`llm-wiki-agent`](https://github.com/) 和 [`obsidian-mind`](https://github.com/) 把 Karpathy 的想法做成了纯 wiki 工具。intern-clawd 的差异是在 wiki 层之上加了**人格 + 仪式 + 多入口**，做成秘书而不是档案柜。

---

## License

MIT
