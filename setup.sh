#!/bin/bash
# One-step setup for clawd intern agent system
# Usage: bash setup.sh
# Prerequisites: macOS, Python 3, Claude Code installed, GitHub SSH key configured

set -e

CLAWD_DIR="$HOME/.clawd"
CTI_DIR="$HOME/.claude-to-im"
CLAUDE_DIR="$HOME/.claude"

echo "=== Clawd Intern Agent Setup ==="

# 1. Check dependencies
echo "[1/9] Checking dependencies..."
command -v python3 >/dev/null || { echo "ERROR: python3 required"; exit 1; }
command -v git >/dev/null || { echo "ERROR: git required"; exit 1; }

# inject-wiki-context.sh hardcodes /usr/bin/python3, make sure it exists
if [[ ! -x /usr/bin/python3 ]]; then
    echo "ERROR: /usr/bin/python3 not found"
    echo "  hooks/inject-wiki-context.sh requires /usr/bin/python3"
    echo "  macOS: run 'xcode-select --install' to get Command Line Tools"
    echo "  Note: macOS only for now"
    exit 1
fi

CLAUDE_BIN=$(which claude 2>/dev/null || echo "$HOME/.local/bin/claude")
if [[ ! -x "$CLAUDE_BIN" ]]; then
    echo "WARNING: claude CLI not found, mobile IM channel may not work"
fi

# 2. Configure wrapper path
echo "[2/9] Configuring wrapper path..."
if [[ -f "$CLAWD_DIR/claude-wrapper.sh" ]]; then
    sed -i '' "s|REAL_CLAUDE=.*|REAL_CLAUDE=\"$CLAUDE_BIN\"|" "$CLAWD_DIR/claude-wrapper.sh"
    chmod +x "$CLAWD_DIR/claude-wrapper.sh"
    echo "  wrapper -> $CLAUDE_BIN"
fi

# 3. Create wiki directory structure (if missing)
echo "[3/9] Setting up directory structure..."
for domain in work life; do
    mkdir -p "$CLAWD_DIR/$domain/wiki/projects"
    mkdir -p "$CLAWD_DIR/$domain/wiki/decisions"
    mkdir -p "$CLAWD_DIR/$domain/raw"
    [[ -f "$CLAWD_DIR/$domain/wiki/log.md" ]] || echo "# ${domain^} Log" > "$CLAWD_DIR/$domain/wiki/log.md"
    [[ -f "$CLAWD_DIR/$domain/wiki/index.md" ]] || echo "# ${domain^} Wiki Index" > "$CLAWD_DIR/$domain/wiki/index.md"
done
mkdir -p "$CLAWD_DIR/shared-wiki"

# 4. Configure Claude-to-IM (if available)
echo "[4/9] Configuring Claude-to-IM..."
if [[ -d "$CTI_DIR" ]]; then
    if [[ ! -f "$CTI_DIR/config.env" ]] && [[ -f "$CLAWD_DIR/config.env.example" ]]; then
        cp "$CLAWD_DIR/config.env.example" "$CTI_DIR/config.env"
        chmod 600 "$CTI_DIR/config.env"
        echo "  Created config.env — fill in your IM credentials: $CTI_DIR/config.env"
    elif [[ -f "$CTI_DIR/config.env" ]]; then
        sed -i '' "s|CTI_DEFAULT_WORKDIR=.*|CTI_DEFAULT_WORKDIR=$CLAWD_DIR|" "$CTI_DIR/config.env"
        sed -i '' "s|CTI_CLAUDE_CODE_EXECUTABLE=.*|CTI_CLAUDE_CODE_EXECUTABLE=$CLAWD_DIR/claude-wrapper.sh|" "$CTI_DIR/config.env"
        echo "  config.env paths updated"
    fi
else
    echo "  Claude-to-IM not installed, skipping (mobile channel unavailable)"
fi

# 5. Install wiki sync rule in global CLAUDE.md
echo "[5/9] Configuring global CLAUDE.md..."
mkdir -p "$CLAUDE_DIR"
if [[ -f "$CLAUDE_DIR/CLAUDE.md" ]]; then
    if ! grep -q "Wiki Knowledge Sync\|Wiki 知识同步" "$CLAUDE_DIR/CLAUDE.md"; then
        BACKUP="$CLAUDE_DIR/CLAUDE.md.before-clawd-$(date +%Y%m%d-%H%M%S)"
        cp "$CLAUDE_DIR/CLAUDE.md" "$BACKUP"
        echo "  Backed up original to $BACKUP"
        cat >> "$CLAUDE_DIR/CLAUDE.md" << 'WIKI_RULE'

## Wiki Knowledge Sync (only when ~/.clawd exists)

If `~/.clawd/` exists (i.e., the user has intern-clawd installed) and this interaction produced knowledge worth persisting (project decisions, architecture changes, important conclusions), consider at the end of the task:

1. Append an entry to `~/.clawd/{work|life}/wiki/log.md`, format: `## [YYYY-MM-DD HH:MM] {operation} | {title}`, 1-3 line summary
2. If an existing wiki page needs updating, confirm with the user first

Skip this rule if `~/.clawd` doesn't exist, or for casual chat / simple Q&A / tasks unrelated to the knowledge base.
WIKI_RULE
        echo "  Wiki sync rule added"
    else
        echo "  Wiki sync rule already exists"
    fi
fi

# 6. Set up cron
echo "[6/9] Setting up scheduled tasks..."
CRON_LINE="7 9 * * * /usr/bin/python3 $CLAWD_DIR/reorganize-index.py --ask >> $CLAWD_DIR/reorganize.log 2>&1"
if crontab -l 2>/dev/null | grep -q "reorganize-index.py"; then
    echo "  Cron job already exists"
else
    (crontab -l 2>/dev/null; echo "# Wiki index reorganize - daily 9:07 AM"; echo "$CRON_LINE") | crontab -
    echo "  Added daily 9:07 AM index reorganization"
fi

# 7. Install Claude Code hooks
echo "[7/9] Installing Claude Code hooks..."
mkdir -p "$CLAUDE_DIR/hooks"
for f in "$CLAWD_DIR/claude-hooks/"*; do
    [[ -f "$f" ]] || continue
    base=$(basename "$f")
    cp "$f" "$CLAUDE_DIR/hooks/$base"
    chmod +x "$CLAUDE_DIR/hooks/$base" 2>/dev/null || true
    echo "  Copied $base"
done

# 8. Configure settings.json hooks (JSON merge via python3)
echo "[8/9] Configuring settings.json hooks..."
/usr/bin/python3 - "$CLAUDE_DIR" "$CLAWD_DIR" << 'PYEOF'
import json, os, sys

claude_dir = sys.argv[1]
clawd_dir = sys.argv[2]
settings_file = os.path.join(claude_dir, "settings.json")

if os.path.exists(settings_file):
    with open(settings_file) as f:
        try:
            settings = json.load(f)
        except json.JSONDecodeError:
            import shutil
            shutil.copy2(settings_file, settings_file + ".bak")
            print("  WARNING: settings.json malformed, backed up as .bak and rebuilt")
            settings = {}
else:
    settings = {}

if "hooks" not in settings:
    settings["hooks"] = {}

hooks = settings["hooks"]

clawd_hooks = {
    "SessionStart": [
        {"type": "command", "command": "$HOME/.clawd/hooks/inject-wiki-context.sh"}
    ],
    "SessionEnd": [
        {"type": "command", "command": "/usr/bin/python3 $HOME/.claude/hooks/session-relocate.py"}
    ],
}

for event, new_hooks in clawd_hooks.items():
    if event not in hooks:
        hooks[event] = []
    existing_cmds = set()
    for entry in hooks[event]:
        for h in entry.get("hooks", []):
            existing_cmds.add(h.get("command", ""))
    for h in new_hooks:
        if h["command"] not in existing_cmds:
            hooks[event].append({"hooks": [h]})
            print(f"  Added {event}: {h['command'].split('/')[-1]}")
        else:
            print(f"  {event} already exists, skipping")

with open(settings_file, "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")
PYEOF

# 9. Add zsh aliases
echo "[9/9] Configuring zsh aliases..."
ZSHRC="$HOME/.zshrc"
touch "$ZSHRC"

add_alias() {
    local line="$1"
    local name="$2"
    if ! grep -q "alias $name=" "$ZSHRC"; then
        echo "" >> "$ZSHRC"
        echo "# intern-clawd" >> "$ZSHRC"
        echo "$line" >> "$ZSHRC"
        echo "  Added: $line"
    else
        echo "  $name alias already exists, skipping"
    fi
}

add_alias "alias clawd='cd ~/.clawd && claude'" "clawd"
add_alias "alias inbox='~/.clawd/collect.sh'" "inbox"

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Edit shared-wiki/boss-profile.md (fill in your identity/preferences/goals)"
echo "  2. Run: source ~/.zshrc (or restart your terminal)"
echo "  3. Type 'clawd' to enter secretary mode — try saying 'standup'"
echo ""
echo "Optional:"
echo "  - Global hotkey (ctrl+opt+C): see README § Optional Entry Points"
echo "  - Mobile IM channel: see README § Mobile IM Channel"
echo ""
