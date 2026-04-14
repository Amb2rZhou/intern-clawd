#!/bin/bash
# Quick context capture: clipboard → inbox.md
# Called by macOS Shortcuts.app / global hotkey / terminal
#
# Usage:
#   collect.sh                  # Capture from clipboard (handles various encodings)
#   collect.sh --process        # Have the secretary process the inbox

echo "[$(date '+%Y-%m-%d %H:%M:%S')] called pid=$$ ppid=$PPID args=$* PATH=$PATH PWD=$PWD USER=$USER" >> /tmp/collect-debug.log 2>&1

CLAWD_DIR="${CLAWD_DIR:-$HOME/.clawd}"
INBOX="$CLAWD_DIR/inbox.md"
REAL_CLAUDE="${CLAUDE_BIN:-$(command -v claude || echo $HOME/.local/bin/claude)}"

# === --process mode: secretary processes inbox ===
if [[ "$1" == "--process" ]]; then
    if [[ ! -s "$INBOX" ]]; then
        echo "Inbox is empty"
        exit 0
    fi
    INBOX_CONTENT=$(cat "$INBOX")
    exec "$REAL_CLAUDE" -p "Here are items collected in the inbox. Process them:

${INBOX_CONTENT}

Rules:
1. Classify each item as work or life domain
2. Extract key points, link to existing wiki pages
3. Append valuable items to the corresponding domain's log.md
4. If an item is rich enough for its own wiki page, confirm before writing
5. Clear inbox.md when done (write empty string)

Read the wiki indexes first to understand the current knowledge structure." \
    --append-system-prompt "$(cat "$CLAWD_DIR/work/wiki/index.md" 2>/dev/null) $(cat "$CLAWD_DIR/life/wiki/index.md" 2>/dev/null)" \
    --allowedTools "Read,Edit,Write,Bash" --max-turns 10 --output-format text
fi

# === Capture mode ===

TIMESTAMP=$(date "+%Y-%m-%d %H:%M")
export COLLECT_TIMESTAMP="$TIMESTAMP"
export CLAWD_DIR

python3 -c '
import subprocess, sys, os

inbox = os.path.join(os.environ["CLAWD_DIR"], "inbox.md")
ts = os.environ.get("COLLECT_TIMESTAMP", "unknown")

r = subprocess.run(["/usr/bin/pbpaste"], capture_output=True)
raw = r.stdout

content = ""
for enc in ["utf-8", "gbk", "gb18030", "latin-1"]:
    try:
        content = raw.decode(enc)
        break
    except (UnicodeDecodeError, LookupError):
        continue

content = content.strip()
if not content:
    subprocess.run(["/usr/bin/osascript", "-e",
        "display notification \"No content selected\" with title \"Capture failed\""])
    sys.exit(1)

try:
    r = subprocess.run(["/usr/bin/osascript", "-e",
        "tell application \"System Events\" to get name of first application process whose frontmost is true"],
        capture_output=True, text=True, timeout=3)
    source = r.stdout.strip() or "unknown"
except:
    source = "unknown"

with open(inbox, "a", encoding="utf-8") as f:
    f.write(f"\n## [{ts}] from: {source}\n\n{content}\n\n---\n")

preview = content[:50].replace(chr(34), chr(39))
subprocess.run(["/usr/bin/osascript", "-e",
    f"display notification \"{preview}...\" with title \"Saved to inbox\""])

print("[collect] Saved to inbox.md")

try:
    sys.path.insert(0, os.environ["CLAWD_DIR"])
    from telemetry import log_op
    log_op("collect", source=source, detail=content[:80])
except:
    pass
'
