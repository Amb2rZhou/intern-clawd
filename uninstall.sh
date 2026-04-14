#!/bin/bash
# One-step uninstaller for intern-clawd
# Usage: bash uninstall.sh
#
# Design principles:
# - Back up before every change
# - Does NOT delete ~/.clawd knowledge base by default (your notes are the most valuable part)
# - Auto-generates restore.sh for one-command rollback
# - Idempotent: safe to run multiple times
# - Does NOT touch macOS Shortcuts.app programmatically (too risky) — prompts manual removal

set -e

CLAWD_DIR="${CLAWD_DIR:-$HOME/.clawd}"
CLAUDE_DIR="$HOME/.claude"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="$HOME/.clawd-uninstall-backup/$TIMESTAMP"

echo "=== intern-clawd uninstaller ==="
echo "Backup directory: $BACKUP_DIR"
echo ""

mkdir -p "$BACKUP_DIR"

# ---- 1. Back up everything we're about to change ----

echo "[1/8] Backing up current state..."

if [[ -f "$CLAUDE_DIR/CLAUDE.md" ]]; then
    cp "$CLAUDE_DIR/CLAUDE.md" "$BACKUP_DIR/CLAUDE.md.bak"
    echo "  ✓ ~/.claude/CLAUDE.md"
fi

if [[ -f "$CLAUDE_DIR/settings.json" ]]; then
    cp "$CLAUDE_DIR/settings.json" "$BACKUP_DIR/settings.json.bak"
    echo "  ✓ ~/.claude/settings.json"
fi

if crontab -l >/dev/null 2>&1; then
    crontab -l > "$BACKUP_DIR/crontab.bak"
    echo "  ✓ crontab"
fi

if [[ -f "$HOME/.zshrc" ]]; then
    cp "$HOME/.zshrc" "$BACKUP_DIR/zshrc.bak"
    echo "  ✓ ~/.zshrc"
fi

# ---- 2. Remove wiki sync section from global CLAUDE.md ----

echo ""
echo "[2/8] Removing wiki sync section from ~/.claude/CLAUDE.md..."
if [[ -f "$CLAUDE_DIR/CLAUDE.md" ]] && grep -q "Wiki Knowledge Sync\|Wiki 知识同步" "$CLAUDE_DIR/CLAUDE.md"; then
    /usr/bin/python3 - "$CLAUDE_DIR/CLAUDE.md" << 'PY'
import sys, re
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    text = f.read()
new = re.sub(r"\n*## Wiki Knowledge Sync[\s\S]*?(?=\n## |\Z)", "\n", text)
new = re.sub(r"\n*## Wiki 知识同步[\s\S]*?(?=\n## |\Z)", "\n", new)
new = new.rstrip() + "\n"
with open(path, "w", encoding="utf-8") as f:
    f.write(new)
PY
    echo "  ✓ Removed"
else
    echo "  - Not found, skipping"
fi

# ---- 3. Remove clawd-related hooks from settings.json ----

echo ""
echo "[3/8] Cleaning clawd hooks from ~/.claude/settings.json..."
if [[ -f "$CLAUDE_DIR/settings.json" ]]; then
    /usr/bin/python3 - "$CLAUDE_DIR/settings.json" << 'PY'
import json, sys
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    data = json.load(f)

removed = 0
hooks = data.get("hooks", {})
for event in list(hooks.keys()):
    new_groups = []
    for group in hooks[event]:
        new_hooks = [
            h for h in group.get("hooks", [])
            if not any(s in str(h.get("command", "")) for s in
                       ["inject-wiki-context", "session-relocate", "permission-router", "mark-session-project"])
        ]
        if new_hooks:
            group["hooks"] = new_hooks
            new_groups.append(group)
        else:
            removed += len(group.get("hooks", []))
    if new_groups:
        hooks[event] = new_groups
    else:
        del hooks[event]
        removed += 1

if not hooks:
    data.pop("hooks", None)

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
print(f"  ✓ Removed {removed} related hook entries")
PY
else
    echo "  - File not found, skipping"
fi

# ---- 4. Delete clawd scripts from ~/.claude/hooks/ ----

echo ""
echo "[4/8] Removing clawd scripts from ~/.claude/hooks/..."
for script in session-relocate.py mark-session-project.sh; do
    if [[ -f "$CLAUDE_DIR/hooks/$script" ]]; then
        cp "$CLAUDE_DIR/hooks/$script" "$BACKUP_DIR/hooks-$script.bak"
        rm "$CLAUDE_DIR/hooks/$script"
        echo "  ✓ Deleted $script (backed up)"
    fi
done

# ---- 5. Remove clawd cron entries ----

echo ""
echo "[5/8] Cleaning clawd entries from crontab..."
if crontab -l 2>/dev/null | grep -q "reorganize-index.py\|clawd"; then
    crontab -l 2>/dev/null \
      | grep -v "reorganize-index.py" \
      | grep -v "Wiki index reorganize" \
      | grep -v "wiki-maintenance.py" \
      | crontab -
    echo "  ✓ Removed"
else
    echo "  - Not found, skipping"
fi

# ---- 6. Remove clawd aliases from ~/.zshrc ----

echo ""
echo "[6/8] Cleaning clawd aliases from ~/.zshrc..."
if [[ -f "$HOME/.zshrc" ]] && grep -q "alias clawd\|alias inbox=" "$HOME/.zshrc"; then
    /usr/bin/python3 - "$HOME/.zshrc" << 'PY'
import sys
path = sys.argv[1]
with open(path, encoding="utf-8") as f:
    lines = f.readlines()
keep = [l for l in lines if not (
    "alias clawd=" in l or
    "alias inbox=" in l or
    ".clawd/collect.sh" in l or
    l.strip() == "# intern-clawd"
)]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(keep)
PY
    echo "  ✓ Removed (restart terminal to take effect)"
else
    echo "  - Not found, skipping"
fi

# ---- 7. Ask about ~/.clawd data ----

echo ""
echo "[7/8] ~/.clawd knowledge base..."
if [[ -d "$CLAWD_DIR" ]]; then
    echo "  ⚠️  $CLAWD_DIR contains all your notes/logs/wiki content"
    echo "  Not deleted by default. To delete, type 'delete my notes':"
    read -r CONFIRM
    if [[ "$CONFIRM" == "delete my notes" ]]; then
        mv "$CLAWD_DIR" "$BACKUP_DIR/clawd-data"
        echo "  ✓ Moved to $BACKUP_DIR/clawd-data (can still be restored manually)"
    else
        echo "  - Keeping ~/.clawd intact"
    fi
else
    echo "  - ~/.clawd not found, skipping"
fi

# ---- 8. Generate restore.sh ----

echo ""
echo "[8/8] Generating restore.sh..."
cat > "$BACKUP_DIR/restore.sh" << RESTORE
#!/bin/bash
# Auto-generated by intern-clawd uninstaller at $TIMESTAMP
# One-command rollback of this uninstall
set -e
BACKUP_DIR="$BACKUP_DIR"
CLAUDE_DIR="$CLAUDE_DIR"
CLAWD_DIR="$CLAWD_DIR"

echo "=== intern-clawd restore ==="
echo "Restoring from \$BACKUP_DIR"
echo ""

[[ -f "\$BACKUP_DIR/CLAUDE.md.bak" ]] && cp "\$BACKUP_DIR/CLAUDE.md.bak" "\$CLAUDE_DIR/CLAUDE.md" && echo "  ✓ CLAUDE.md"
[[ -f "\$BACKUP_DIR/settings.json.bak" ]] && cp "\$BACKUP_DIR/settings.json.bak" "\$CLAUDE_DIR/settings.json" && echo "  ✓ settings.json"
[[ -f "\$BACKUP_DIR/crontab.bak" ]] && crontab "\$BACKUP_DIR/crontab.bak" && echo "  ✓ crontab"
[[ -f "\$BACKUP_DIR/zshrc.bak" ]] && cp "\$BACKUP_DIR/zshrc.bak" "\$HOME/.zshrc" && echo "  ✓ ~/.zshrc"

mkdir -p "\$CLAUDE_DIR/hooks"
for s in session-relocate.py mark-session-project.sh; do
    if [[ -f "\$BACKUP_DIR/hooks-\$s.bak" ]]; then
        cp "\$BACKUP_DIR/hooks-\$s.bak" "\$CLAUDE_DIR/hooks/\$s"
        echo "  ✓ hooks/\$s"
    fi
done

if [[ -d "\$BACKUP_DIR/clawd-data" ]]; then
    if [[ -e "\$CLAWD_DIR" ]]; then
        echo "  ⚠️  \$CLAWD_DIR already exists, skipping data restore (manually move from \$BACKUP_DIR/clawd-data)"
    else
        mv "\$BACKUP_DIR/clawd-data" "\$CLAWD_DIR"
        echo "  ✓ ~/.clawd data restored"
    fi
fi

echo ""
echo "Done. Restart your terminal for alias changes to take effect."
RESTORE
chmod +x "$BACKUP_DIR/restore.sh"
echo "  ✓ $BACKUP_DIR/restore.sh"

# ---- Final notes ----

echo ""
echo "=== Uninstall complete ==="
echo ""
echo "These require manual action (uninstall.sh does not touch them):"
echo "  1. macOS Shortcuts.app: delete the ctrl+opt+C shortcut for 'Capture to inbox'"
echo "  2. ~/.claude-to-im/: if you installed the mobile IM bridge, follow its own README to uninstall"
echo ""
echo "Changed your mind? Run this to restore everything:"
echo "  bash $BACKUP_DIR/restore.sh"
echo ""
