# Changelog

All notable changes to intern-clawd will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

(none yet)

## [0.1.0] — 2026-04-10

First public release. Personal Secretary OS for Claude Code, built on top of
Andrej Karpathy's [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
three-layer pattern (raw / wiki / schema), extended with persona, rituals,
and multi-channel capture.

### Added
- **Dual-domain knowledge base** — `work/` and `life/` wikis with independent
  index, log, projects, and reflections
- **7 secretary rituals** — 站会 / 周会 / 复盘 / 处理 inbox / 归档 / 继续 / lint,
  routed via natural language
- **5 capture entries** — `⌃⌥C` global hotkey, `clawd` and `inbox` zsh aliases,
  Feishu/WeChat IM bridges (optional), terminal `clawd` command
- **Claude Code hook integration**
  - `inject-wiki-context.sh` — SessionStart hook injecting current wiki state
    into the secretary's system prompt
  - `session-relocate.py` — SessionEnd hook routing JSONLs to per-project
    archive directories based on user-declared markers
  - `mark-session-project.sh` — declares the project a session belongs to
- **`setup.sh`** — one-shot installer covering dependencies, directory
  skeleton, global CLAUDE.md rules, and daily cron
- **`uninstall.sh`** — one-shot reverter that backs up every file it touches,
  removes the wiki sync section from CLAUDE.md, strips clawd hooks from
  settings.json, cleans crontab and zshrc aliases, and asks twice before
  touching `~/.clawd` data. Generates a `restore.sh` in the backup directory
  so users can roll back the uninstall itself
- **`RISKS.md`** — explicit, honest catalog of A/B/C tier known issues —
  what is fixed, what is mitigated, what is intentionally left unfixed,
  plus a pre-install self-check checklist
- **Quick Start section** in README — 4 commands to see the minimum viable
  secretary, separate from the full install path
- **Wiki maintenance scripts** — `wiki-lint.py`, `wiki-maintenance.py`,
  `reorganize-index.py`, `weekly-report.py`, `monthly-review.py`
- **Path parameterization** — every script honors `$CLAWD_DIR` and
  `$CLAUDE_BIN`, no hardcoded user paths

### Vanilla Claude Code compatibility
- Installing intern-clawd does **not** affect Claude Code capability outside
  `~/.clawd/`. The cwd-gated SessionStart hook returns in ~5ms via pure bash
  before spawning python3 in non-secretary sessions, and the global
  CLAUDE.md wiki sync rule is conditional on `~/.clawd` existing.

### Acknowledgements
- [Andrej Karpathy](https://karpathy.ai/) for the LLM Wiki three-layer
  pattern this project builds on
- [Claude Code](https://docs.claude.com/claude-code) for the hook system,
  CLAUDE.md injection mechanism, and SessionStart/SessionEnd lifecycle

[Unreleased]: https://github.com/Amb2rZhou/intern-clawd/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Amb2rZhou/intern-clawd/releases/tag/v0.1.0
