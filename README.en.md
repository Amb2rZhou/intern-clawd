# intern-clawd — A Personal Secretary OS for Claude Code

[![syntax](https://github.com/Amb2rZhou/intern-clawd/actions/workflows/syntax.yml/badge.svg)](https://github.com/Amb2rZhou/intern-clawd/actions/workflows/syntax.yml)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![version](https://img.shields.io/badge/version-0.2.0-green.svg)](CHANGELOG.md)

[中文](README.md) | **English**

Turn Claude Code from "an amnesiac coding tool that forgets every session" into "a cross-session, multi-channel personal secretary with a real persona and rituals."

This is **not yet another LLM wiki**. It's a complete secretary operating system — the knowledge base is just one of its organs.

> **clawd** = **Claude** + **wd** (working directory). A secretary agent living in `~/.clawd/` that manages two domains of your knowledge (work and life), covering the full loop: capture → digest → retrieve → reflect.

---

## How it differs from similar projects

| | intern-clawd | LLM Wiki tools<br>(`llm-wiki-agent` etc.) | LLM memory frameworks<br>(`mem0`, `letta`) | Obsidian + LLM<br>(`obsidian-mind` etc.) |
|---|---|---|---|---|
| Dual domains (work / life) | ✅ | ❌ single wiki | ❌ generic memory | ❌ single vault |
| Role-based rituals (standup/weekly/reflect) | ✅ 7 fixed commands | ❌ | ❌ | ❌ |
| Multi-channel capture | ✅ terminal + hotkey + IM | ❌ single entry | ❌ API only | ⚠️ Obsidian only |
| Session routing hooks | ✅ auto-archives JSONLs | ❌ | ❌ | ❌ |
| Install | ✅ clone to `~/.clawd`, zero servers | ⚠️ needs backend | ⚠️ needs backend / DB | ✅ but bound to Obsidian |
| Self-maintenance (lint + monthly job) | ✅ | ⚠️ partial | ❌ | ❌ |

**Core difference**: others build "knowledge base + LLM." We build "**a secretary with a persona + ritual system + multi-channel capture**." The wiki is the secretary's notebook, not the product itself.

---

## What problem does it solve

Vanilla Claude Code is just "a coding assistant that works one session at a time." When you try to do more with it, you hit a few walls:

| Pain | How clawd fixes it |
|---|---|
| Every new session = amnesia | Persistent wiki + auto-injects index on every SessionStart |
| You have to sit at a terminal to talk to it | `⌃⌥C` global hotkey, terminal aliases, mobile IM channel (optional) |
| No "role" concept, you re-prompt every time | Persona baked into CLAUDE.md + 7 fixed rituals (standup / weekly / reflect / archive / resume / inbox / lint) |
| Work and personal notes get mixed up | Dual-domain architecture: `work/` + `life/`, independent index and log |
| Sessions started from `~` all pile into one folder | Session routing hooks auto-relocate JSONLs by project |
| Knowledge bases rot | wiki-lint + monthly auto-maintenance + post-write self-check |

---

## Architecture

```
┌──────────── capture ────────────┐
│ ⌃⌥C global hotkey   `clawd` cmd │
│ Mobile IM (Telegram / Slack / …) │
└──────────────┬──────────────────┘
               │
               ▼
       ┌────────────────┐
       │ Secretary Agent│  ← CLAUDE.md (persona + rules)
       │ (Claude Code)  │     dual-domain index auto-injected
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

  raw/   ← immutable source of truth (agent: read-only)
  wiki/  ← LLM-maintained layer (agent: read + write)
  schema ← constraint layer (human + agent jointly maintain)
```

The three-layer knowledge architecture is taken directly from **Andrej Karpathy**'s [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern: strict separation of "source of truth" from "LLM synthesis layer," letting the agent only Read raw and never Write, so hallucinations can't poison the source. See Karpathy's gist for the original idea.

intern-clawd extends this: on top of the wiki layer it stacks **persona + rituals + multi-channel capture**, turning "knowledge base" into "secretary."

---

## Quick Start (3 minutes)

```bash
git clone https://github.com/Amb2rZhou/intern-clawd.git ~/.clawd
cd ~/.clawd && bash setup.sh && source ~/.zshrc && clawd
```

Two commands. `setup.sh` handles all configuration automatically (hooks, settings.json, aliases, cron), then `clawd` enters secretary mode.

On first launch, the secretary detects that you haven't filled in your profile yet and **guides you through onboarding automatically** — it asks a few questions (name, role, preferences, projects, red lines) and writes the config file for you. All done via conversation, no manual file editing needed.

Once set up, type **`standup`** to see it in action. **Don't like it?** Run `bash ~/.clawd/uninstall.sh` for a one-shot cleanup.

---

## Install

### 0. Prerequisites

- macOS 14+ / Linux (verified on macOS Sequoia 15.6)
- Python 3.9+
- [Claude Code CLI](https://docs.claude.com/claude-code) installed and `claude` on `PATH`
- git

### 1. Clone

```bash
git clone https://github.com/Amb2rZhou/intern-clawd.git ~/.clawd
cd ~/.clawd
```

### 2. Run setup.sh

```bash
bash setup.sh
```

Automatically (9 steps):
- Check dependencies (python3 / git / claude CLI)
- Create `work/life` wiki directory skeleton
- Inject wiki sync rule into `~/.claude/CLAUDE.md` (with backup)
- Set up daily 9:07 AM cron for wiki reorganization
- Copy hooks to `~/.claude/hooks/`
- Inject hook config into `~/.claude/settings.json` (smart merge, won't overwrite existing config)
- Add `clawd` / `inbox` aliases to `~/.zshrc`

### 3. Start using

```bash
source ~/.zshrc   # load the aliases just added
clawd             # enter secretary mode
```

On first launch the secretary will guide you through onboarding via conversation, filling in your profile automatically. You can also skip the guided setup and manually edit `shared-wiki/boss-profile.md`.

### Optional: Global hotkey ⌃⌥C (macOS, manual GUI)

Want one-key capture from any app? Set up a shortcut in Shortcuts.app:

1. Open Shortcuts.app, create a new shortcut
2. Add a "Run Shell Script" action with content: `/Users/$USER/.clawd/collect.sh` (absolute path)
3. Add a "Show Notification" action (osascript notifications fail silently on Sequoia, you must use this)
4. System Settings → Keyboard → Keyboard Shortcuts → Services → Shortcuts → find this entry → double-click the right side and bind `⌃⌥C`

This is purely optional — core functionality works without it. See [`setup-new-machine.md`](setup-new-machine.md) §4 for details.

---

## Usage (the 10 you'll actually use)

| # | Trigger | When |
|---|---|---|
| 1 | **`⌃⌥C`** | You see something you want to save |
| 2 | **`clawd`** | You want to talk to the secretary |
| 3 | **`standup`** | You want to know what you've been doing recently |
| 4 | **`weekly`** | You want a full review |
| 5 | **`process inbox`** | You want the secretary to digest the inbox |
| 6 | **`reflect X`** | Project retrospective |
| 7 | **`archive X`** | Project ended |
| 8 | **`resume X`** | Project restarted |
| 9 | **`import history`** | Import historical CC sessions into wiki, auto-classify |
| 10 | **`graph`** | Generate wiki relationship graph (opens in browser) |

The Chinese keywords (站会/周会/复盘/处理 inbox/归档/继续/检查/导入历史/关系图) work too. See [`cheatsheet.md`](cheatsheet.md) for the full command list.

---

## File structure

```
.
├── CLAUDE.md                  # Secretary persona + rules (auto-loaded by CC when cwd is .clawd)
├── schema.md                  # Global schema (agent behavior constraints)
├── README.md / README.en.md   # Chinese / English README
├── CHANGELOG.md               # Version changelog
├── RISKS.md                   # Known risks + self-check checklist
├── cheatsheet.md              # All commands at a glance
├── setup-new-machine.md       # Full migration / install guide (with known-issue cheatsheet)
│
├── setup.sh                   # One-shot initializer (9 automated steps)
├── uninstall.sh               # One-shot uninstaller (with restore.sh rollback)
├── claude-wrapper.sh          # Secretary wrapper (hard-routes ritual commands)
├── collect.sh                 # Clipboard → inbox capture
├── extract-session.py         # SessionEnd: extract conversations to raw/sessions/
│
├── wiki-lint.py               # Wiki health check
├── wiki-maintenance.py        # Monthly full maintenance (cron)
├── wiki-graph.py              # Relationship graph (HTML + d3.js)
├── import-history.py          # Historical session import
├── reorganize-index.py        # Daily index reorganization
├── weekly-report.py           # Weekly report generator
├── monthly-review.py          # Monthly review generator
├── telemetry.py               # Operation log (jsonl)
│
├── feishu_utils.py            # Feishu/Lark notifications (optional, reference impl)
├── feishu-send.sh             # Feishu/Lark sender (optional, reference impl)
├── config.env.example         # IM bridge config template (optional)
│
├── hooks/
│   ├── inject-wiki-context.sh # SessionStart hook (cwd-gated)
│   └── permission-router.sh   # PermissionRequest smart router
│
├── claude-hooks/              # Installed to ~/.claude/hooks/
│   ├── mark-session-project.sh
│   └── session-relocate.py
│
├── work/
│   ├── schema.md
│   ├── wiki/
│   │   ├── index.md           # Work domain index
│   │   ├── log.md             # Work timeline
│   │   ├── projects/
│   │   ├── people/
│   │   ├── decisions/
│   │   └── patterns/
│   └── raw/                   # Immutable sources
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
    ├── boss-profile.md        # ⭐ Must fill on first install
    └── coding-style.md
```

---

## Risks & Uninstall

Installing this touches several global files on your machine (`~/.claude/CLAUDE.md`, `settings.json`, `crontab`, `~/.zshrc`). **Read [`RISKS.md`](RISKS.md) before installing** — it lists every known risk, scope of impact, mitigation, and the things the author explicitly says are "not fixed."

**Promise**: Installing intern-clawd **does not affect your ability to run vanilla Claude Code outside `~/.clawd/`**.
- The global CLAUDE.md rule is conditional on `~/.clawd` existing — zero interference with unrelated projects
- The SessionStart hook returns in ~5ms via pure bash before spawning python3 in non-secretary cwds
- cwd is the natural mode switch: enter `~/.clawd` for secretary mode, leave for fully vanilla CC

**One-shot uninstall**:

```bash
bash uninstall.sh
```

What it does: backs up every file it touches → removes the wiki sync section from CLAUDE.md → strips clawd hooks from settings.json → cleans crontab → cleans zsh aliases → asks (default no) before touching `~/.clawd` data, requires typing `delete my notes` for confirmation → generates a `restore.sh` so you can roll back the uninstall itself.

See [`RISKS.md`](RISKS.md) "How to undo" section for details.

---

## Design principles

- **Cognitive offload over token frugality** — making you think less matters more than making the LLM cost less
- **Multiple capture entries** — when you see something worth saving, you should be able to save it in 3 seconds
- **Role > tool** — the secretary has a persona, rituals, preferences. It is not a generic chatbot
- **Immutable persistence layer** — `raw/` is read-only for the agent, so hallucinations can't poison the source
- **Self-check over manual maintenance** — wiki-lint + post-write self-check + monthly maintenance, the system takes care of itself

---

## Mobile IM channel (optional)

The core entry point is the terminal, but you can connect the secretary to any IM bot. The pattern is simple:

```
Phone message → IM Bot → call ~/.clawd/claude-wrapper.sh -p "message" → return reply → IM Bot → phone gets reply
```

**Connecting any IM takes two steps:**

1. Create a bot on your platform (Telegram BotFather / Discord Bot / Slack App / Feishu / …)
2. Have the bot call this on each incoming message:
   ```bash
   ~/.clawd/claude-wrapper.sh -p "the user's message"
   ```
   Send stdout back as the reply.

The wrapper handles command routing (standup, weekly, etc.) and context injection automatically — same experience as the terminal.

This repo includes a Feishu (Lark) reference implementation (`feishu_utils.py` / `feishu-send.sh`) that you can use as a template for other platforms.

---

## Acknowledgements & inspiration

- **[Andrej Karpathy](https://karpathy.ai/)** — [the LLM Wiki three-layer pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (raw / wiki / schema). The knowledge layer of intern-clawd is built entirely on this idea.
- **[Claude Code](https://docs.claude.com/claude-code)** — the entire hook system, the CLAUDE.md injection mechanism, and the SessionStart/SessionEnd lifecycle this project relies on.
- Similar-project research: `llm-wiki-agent` and `obsidian-mind` turned Karpathy's idea into pure wiki tools. intern-clawd's difference is stacking **persona + rituals + multi-channel capture** on top of the wiki layer, making it a secretary instead of a filing cabinet.

---

## License

MIT
