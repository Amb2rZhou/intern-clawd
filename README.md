# intern-clawd — A Personal Secretary OS for Claude Code

[![syntax](https://github.com/Amb2rZhou/intern-clawd/actions/workflows/syntax.yml/badge.svg)](https://github.com/Amb2rZhou/intern-clawd/actions/workflows/syntax.yml)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![version](https://img.shields.io/badge/version-0.2.0-green.svg)](CHANGELOG.md)

**中文** | [English](README.en.md)

把 Claude Code 从「每次失忆的编程工具」改造成「有记忆、有仪式感、陪你成长的私人秘书」。

不是又一个 LLM wiki，是一个**完整的秘书操作系统**：知识库只是其中一个器官。

> **clawd** = **Claude** + **wd** (working directory)。一个驻留在 `~/.clawd/` 的秘书 agent，管理你的工作 / 生活两个域的知识库，覆盖从「想到 → 捕获 → 消化 → 检索 → 复盘」全链路。

---

## 跟同类产品的差异

| | intern-clawd | OpenClaw | 裸 Claude Code |
|---|---|---|---|
| 定位 | Claude Code 上的私人秘书 | 自托管 AI agent（多 IM 接入） | 通用编程助手 |
| 费用 | $0（随 Claude Code 订阅走） | API 按量付费（Opus 4.6: $15/$75 per MTok） | $20/mo Max 或 $100/mo Pro |
| 运行方式 | 纯文件，零服务 | Node.js 常驻服务 | 内置 |
| 知识持久化 | ✅ 双域 wiki（work / life），三层架构 | ⚠️ skill 文件 + 对话记忆 | ⚠️ auto-memory 扁平笔记 |
| 角色 + 仪式 | ✅ 秘书人格 + 站会/周会/复盘… | ⚠️ skill 系统（自由定义） | ❌ 每次需手动 prompt |
| 多渠道 capture | ✅ 终端 + 快捷键 + IM（可选） | ✅ 终端 + IM | ✅ 终端 + IM（需自建） |
| Session 路由 | ✅ 自动按项目归档 jsonl | ❌ | ❌ 按 cwd 堆积 |
| 自维护 | ✅ lint + 月度维护 + 分层 index | ❌ | ❌ |
| 依赖 | Python 3 + Claude Code | Node 22+，独立运行 | 无 |
| 安装 | `clone + setup.sh`（3 分钟） | 一键脚本（需 Node） | 内置 |
| 卸载 | ✅ `uninstall.sh` + 回退脚本 | ✅ | — |

**怎么选**：想在手机上跟 AI 聊天 → OpenClaw。想让 Claude Code 本身变得更聪明、有记忆、有节奏 → intern-clawd。两者也可以共存：用 OpenClaw 做 IM 通道，用 intern-clawd 管知识。

---

## 解决什么问题

裸 Claude Code 只是个「按 session 工作的编程助手」。当你想用它做更多事时，会撞上几个墙：

| 痛点 | clawd 怎么解 |
|---|---|
| 每开一个新 session 等于失忆 | 持久 wiki + 每次 SessionStart 自动注入 index |
| 必须坐下打开终端才能跟它说话 | 全局快捷键 `⌃⌥C` 一秒收集 / 终端 alias / 手机 IM 通道（可选） |
| 没有"角色"概念，每次都得重复 prompt | CLAUDE.md 里写死秘书人格 + 7 个固定 ritual（站会/周会/复盘/归档/继续/inbox/lint） |
| 工作和生活的笔记混在一起 | 双域架构：work/ + life/，独立 index 和 log |
| `~` 启动的 session 全堆在一个文件夹 | Session 路由 hooks 自动按项目搬 jsonl |
| 知识库容易腐烂 | wiki-lint + 月度自动维护 + post-write 自检 |

---

## 架构

```
┌──────────────── 入口 ────────────────┐
│ ⌃⌥C 全局快捷键   终端 alias `clawd`   │
│ 手机 IM（Telegram / 飞书 / 微信 / …）  │
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

## Quick Start（3 分钟）

```bash
git clone https://github.com/Amb2rZhou/intern-clawd.git ~/.clawd
cd ~/.clawd && bash setup.sh && source ~/.zshrc && clawd
```

两行命令。`setup.sh` 自动搞定所有配置（hooks、settings.json、aliases、cron），然后 `clawd` 进入秘书模式。

首次进入时，秘书会检测到你还没填写个人画像，**自动引导你完成 onboarding**——问你几个问题（怎么称呼、做什么工作、偏好、项目、红线），然后帮你写好配置文件。全程对话完成，不用手动编辑任何文件。

设置完成后说 **「站会」** 试试效果。**不满意就** `bash ~/.clawd/uninstall.sh` 一键清干净。

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

会自动（9 步）：
- 检查依赖（python3 / git / claude CLI）
- 创建 work/life wiki 目录骨架
- 注入 wiki sync 规则到 `~/.claude/CLAUDE.md`（带备份）
- 设置 cron（每日 9:07 AM 整理 wiki）
- 复制 hooks 到 `~/.claude/hooks/`
- 注入 hook 配置到 `~/.claude/settings.json`（智能 merge，不覆盖已有配置）
- 添加 `clawd` / `inbox` alias 到 `~/.zshrc`

### 3. 开始使用

```bash
source ~/.zshrc   # 加载刚添加的 alias
clawd             # 进入秘书模式
```

首次进入时秘书会自动引导 onboarding，通过对话帮你填好个人画像。也可以跳过引导，手动编辑 `shared-wiki/boss-profile.md`。

### 可选入口：全局快捷键 ⌃⌥C（macOS，手动 GUI）

想要在任何 app 里一键收集到 inbox？在 Shortcuts.app 里建一个快捷指令：

1. 打开 Shortcuts.app，新建 shortcut
2. 加「运行 Shell 脚本」action，内容：`/Users/$USER/.clawd/collect.sh`（绝对路径）
3. 加「显示通知」action（macOS Sequoia 上 osascript 通知会失败，必须用这个）
4. 系统设置 → 键盘 → 键盘快捷键 → 服务 → 快捷指令 → 找到这条 → 双击右边绑 `⌃⌥C`

这步纯可选，不影响核心功能。详细步骤见 [`setup-new-machine.md`](setup-new-machine.md) §4。

---

## 用法（高频 10 个）

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
| 9 | **「导入历史」** | 把历史 CC session 导入 wiki，自动分类归档 |
| 10 | **「关系图」** | 生成 wiki 关系图（浏览器打开） |

完整命令清单见 [`cheatsheet.md`](cheatsheet.md)。

---

## 文件结构

```
.
├── CLAUDE.md                  # 秘书人格 + 规则（cwd 在 .clawd 时 Claude Code 自动加载）
├── schema.md                  # 全局 schema（agent 行为约束）
├── README.md / README.en.md   # 中英文 README
├── CHANGELOG.md               # 版本变更记录
├── RISKS.md                   # 已知风险 + 自检清单
├── cheatsheet.md              # 快捷命令大全
├── setup-new-machine.md       # 完整迁移/安装手册（含已知坑速查）
│
├── setup.sh                   # 一键初始化（9 步全自动）
├── uninstall.sh               # 一键卸载（带 restore.sh 回退）
├── claude-wrapper.sh          # 秘书 wrapper（特殊命令硬路由）
├── collect.sh                 # 剪贴板 → inbox 收集
├── extract-session.py         # SessionEnd: 提取对话到 raw/sessions/
│
├── wiki-lint.py               # wiki 健康检查
├── wiki-maintenance.py        # 月度全面维护（cron）
├── wiki-graph.py              # 关系图生成（HTML + d3.js）
├── import-history.py          # 历史 session 导入
├── reorganize-index.py        # 每日 index 整理
├── weekly-report.py           # 周报生成
├── monthly-review.py          # 月度复盘
├── telemetry.py               # 操作日志（jsonl）
│
├── feishu_utils.py            # 飞书通知（可选，参考实现）
├── feishu-send.sh             # 飞书发送（可选，参考实现）
├── config.env.example         # IM bridge 配置模板（可选）
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

## 手机 IM 通道（可选）

intern-clawd 的核心入口是终端，但你可以通过任何 IM 机器人连接秘书。原理很简单：

```
手机发消息 → IM Bot → 调用 ~/.clawd/claude-wrapper.sh -p "消息" → 返回回复 → IM Bot → 手机收到回复
```

**接入任意 IM 只需要两步：**

1. 在你选的平台上建一个 bot（Telegram BotFather / Discord Bot / Slack App / 飞书自建应用 / …）
2. 让 bot 收到消息时调用：
   ```bash
   ~/.clawd/claude-wrapper.sh -p "用户发来的消息"
   ```
   把 stdout 作为回复发回去

wrapper 会自动处理命令路由（站会、周会等触发词）和上下文注入，跟终端体验一致。

本 repo 附带了飞书（Lark）的参考实现（`feishu_utils.py` / `feishu-send.sh`），可以作为接入其他 IM 的模板。

---

## 致谢 & 灵感来源

- **[Andrej Karpathy](https://karpathy.ai/)** — [LLM Wiki 三层架构](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)（raw / wiki / schema）。intern-clawd 知识层完全建立在这个模式之上。
- **[Claude Code](https://docs.claude.com/claude-code)** — 整套 hook 系统、CLAUDE.md 注入机制、SessionStart/SessionEnd 生命周期的基石。
- 同类项目调研：`llm-wiki-agent` 和 `obsidian-mind` 把 Karpathy 的想法做成了纯 wiki 工具。intern-clawd 的差异是在 wiki 层之上加了**人格 + 仪式 + 多入口**，做成秘书而不是档案柜。

---

## License

MIT
