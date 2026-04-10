# intern-clawd — A Personal Secretary OS for Claude Code

[![syntax](https://github.com/Amb2rZhou/intern-clawd/actions/workflows/syntax.yml/badge.svg)](https://github.com/Amb2rZhou/intern-clawd/actions/workflows/syntax.yml)
[![license](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

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
| Multi-channel capture | ✅ 5+ entry points | ❌ single entry | ❌ API only | ⚠️ Obsidian only |
| Session routing hooks | ✅ auto-archives JSONLs | ❌ | ❌ | ❌ |
| Install | ✅ clone to `~/.clawd`, zero servers | ⚠️ needs backend | ⚠️ needs backend / DB | ✅ but bound to Obsidian |
| Self-maintenance (lint + monthly job) | ✅ | ⚠️ partial | ❌ | ❌ |

**Core difference**: others build "knowledge base + LLM." We build "**a secretary with a persona + 7 rituals + 5 capture channels**." The wiki is the secretary's notebook, not the product itself.

---

## What problem does it solve

Vanilla Claude Code is just "a coding assistant that works one session at a time." When you try to do more with it, you hit a few walls:

| Pain | How clawd fixes it |
|---|---|
| Every new session = amnesia | Persistent wiki + auto-injects index on every SessionStart |
| You have to sit at a terminal to talk to it | `⌃⌥C` global hotkey, terminal aliases, Feishu, WeChat, desktop bubble |
| No "role" concept, you re-prompt every time | Persona baked into CLAUDE.md + 7 fixed rituals (standup / weekly / reflect / archive / resume / inbox / lint) |
| Work and personal notes get mixed up | Dual-domain architecture: `work/` + `life/`, independent index and log |
| Sessions started from `~` all pile into one folder | Session routing hooks auto-relocate JSONLs by project |
| Knowledge bases rot | wiki-lint + monthly auto-maintenance + post-write self-check |

---

## Architecture

```
┌──────────── capture ────────────┐
│ ⌃⌥C global hotkey   `clawd` cmd │
│ Feishu / WeChat     desktop bubble│
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

## Quick Start (5 minutes to first effect)

Want to see what it does before committing to the full install? Run these 4 lines:

```bash
git clone https://github.com/Amb2rZhou/intern-clawd.git ~/.clawd
cd ~/.clawd && bash setup.sh
echo "I am $(whoami), trying out intern-clawd today." > shared-wiki/boss-profile.md
claude
```

In the Claude session, type **`standup`** — the secretary will read `life/wiki/log.md` (currently empty), greet you, and ask where you want to start. That's the minimum viable form.

Spend one more minute on this: select text in any app → `⌃C` → run `~/.clawd/collect.sh` in a terminal → return to the secretary session and say **`process inbox`** — it will file what you just captured into the right domain wiki.

**If you like it**, continue installing the `⌃⌥C` global hotkey, Claude Code hooks, cron jobs, etc. (sections §1–§5 below). **If not**, run `bash uninstall.sh` for a one-shot cleanup.

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

Will automatically:
- Check dependencies
- Create the `work/life` wiki directory skeleton
- Inject the wiki sync rule into `~/.claude/CLAUDE.md` (with backup)
- Set up a daily 9:07 AM cron for wiki reorganization

### 3. Write your profile

```bash
$EDITOR shared-wiki/boss-profile.md
```

Fill in your identity, preferences, current goals, red lines — this is the only source the secretary has to learn about you.

### 4. Install capture entries (manual)

Detailed steps in [`setup-new-machine.md`](setup-new-machine.md). Short version:

**zsh aliases** (add to `~/.zshrc`):

```bash
alias clawd='cd ~/.clawd && claude'
alias inbox='~/.clawd/collect.sh'
```

**Global hotkey `⌃⌥C` to capture into inbox** (macOS):

1. Open Shortcuts.app, create a new shortcut
2. Add a "Run Shell Script" action with content: `/Users/$USER/.clawd/collect.sh` (absolute path)
3. Add a "Show Notification" action (osascript notifications fail silently on Sequoia, you must use this)
4. System Settings → Keyboard → Keyboard Shortcuts → Services → Shortcuts → find this entry → double-click the right side and bind `⌃⌥C`

⚠️ **Do not use** `create-quick-action.sh` — it uses the Automator path, which is broken on Sequoia.

### 5. Install Claude Code hooks (optional but recommended)

```bash
mkdir -p ~/.claude/hooks
cp claude-hooks/* ~/.claude/hooks/
```

Then add to `~/.claude/settings.json`:

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

## Usage (the 8 you'll actually use)

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

The Chinese keywords (站会/周会/复盘/处理 inbox/归档/继续/检查) work too. See [`cheatsheet.md`](cheatsheet.md) for the full command list.

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

## Optional integrations not in this repo

These are **clawd-friendly but independent** projects, not hard dependencies:

- **Mr. Krabs.app** — desktop bubble, permission approvals + notifications
- **Claude-to-IM bridge** — mobile channel (Feishu / WeChat)

Integrate as you see fit.

---

## Acknowledgements & inspiration

- **[Andrej Karpathy](https://karpathy.ai/)** — [the LLM Wiki three-layer pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) (raw / wiki / schema). The knowledge layer of intern-clawd is built entirely on this idea.
- **[Claude Code](https://docs.claude.com/claude-code)** — the entire hook system, the CLAUDE.md injection mechanism, and the SessionStart/SessionEnd lifecycle this project relies on.
- Similar-project research: `llm-wiki-agent` and `obsidian-mind` turned Karpathy's idea into pure wiki tools. intern-clawd's difference is stacking **persona + rituals + multi-channel capture** on top of the wiki layer, making it a secretary instead of a filing cabinet.

---

## License

MIT
