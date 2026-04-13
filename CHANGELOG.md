# Changelog

All notable changes to intern-clawd will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
versioning follows [SemVer](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

(none yet)

## [0.2.0] — 2026-04-13

Major usability release: installation down from ~30 min to ~3 min, Claude-guided
onboarding, historical session import, wiki relationship graph, English README,
CI pipeline, and full independence from external dependencies.

### Added
- **One-shot setup automation** — `setup.sh` expanded from 6 to 9 steps:
  now auto-copies hooks to `~/.claude/hooks/`, injects hook config into
  `settings.json` via Python3 JSON merge (no overwrite), and adds `clawd` /
  `inbox` aliases to `~/.zshrc`
- **Claude-guided onboarding** — on first launch, the secretary detects
  unfilled `boss-profile.md` placeholders and walks the user through setup
  via conversation (name, role, language, style, projects, red lines)
- **`import-history.py`** — scan, extract, and classify historical Claude Code
  sessions into the wiki. Includes `--scan` (report only), `--extract`,
  `--snapshot` (tar.gz backup + auto-generated `rollback-import.sh`)
- **`wiki-graph.py`** — generates a standalone HTML page with a d3.js
  force-directed graph of wiki pages, links, and tags. Dark theme, color-coded
  by domain (work=blue, life=green, shared=gray)
- **English README** (`README.en.md`) with language switcher in both versions
- **CI syntax check** — GitHub Actions workflow (`syntax.yml`) + badges
- **Mobile IM connection guide** — generic two-step pattern for connecting
  any IM bot (Telegram, Discord, Slack, etc.) via `claude-wrapper.sh`

### Changed
- **Quick Start reduced to 2 commands** (was 4) — `clone + setup.sh + clawd`
  on a single line
- **Install steps reduced from 5 to 3** — Shortcuts.app demoted to optional
- **Usage table expanded** from 8 to 10 commands (added 导入历史 / 关系图)
- **IM references generalized** — replaced all Feishu/WeChat-specific language
  with platform-agnostic descriptions; Feishu code kept as reference impl
- **`permission-router.sh` simplified** — now pure terminal detection,
  no external HTTP forwarding

### Removed
- All references to external dependencies that are not part of this project

### Fixed
- Broken empty GitHub links in README 致谢 section
- Missing file structure section in English README

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
- **Multiple capture entries** — `⌃⌥C` global hotkey, `clawd` and `inbox`
  zsh aliases, mobile IM channel (optional), terminal `clawd` command
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
- **Quick Start section** in README — minimal commands to see the secretary
  in action, separate from the full install path
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

[Unreleased]: https://github.com/Amb2rZhou/intern-clawd/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Amb2rZhou/intern-clawd/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Amb2rZhou/intern-clawd/releases/tag/v0.1.0
