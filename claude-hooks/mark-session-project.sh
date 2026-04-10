#!/bin/bash
# Mark current Claude Code session for relocation at SessionEnd.
#
# Usage:
#   mark-session-project.sh <project_abs_path> [title]
#
# Examples:
#   mark-session-project.sh ~/some-project "feature work"
#   mark-session-project.sh ~/.clawd "secretary maintenance"
#
# Mechanism:
#   1. Find current session by picking the most recently modified .jsonl
#      under ~/.claude/projects/ (this script is invoked mid-session, so the
#      JSONL Claude is currently writing to is reliably the most recent).
#   2. Write a marker file at ~/.claude/session-targets/<session_id>.target
#      with target_cwd= and title=.
#   3. SessionEnd hook (session-relocate.py) reads the marker and moves the
#      JSONL into ~/.claude/projects/<encoded-cwd>/ on session exit.

set -e

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <project_abs_path> [title]" >&2
    exit 1
fi

# Resolve ~ in case caller passed it
TARGET="${1/#\~/$HOME}"
TITLE="${2:-}"

if [[ ! -d "$TARGET" ]]; then
    echo "Warning: target dir does not exist: $TARGET (marker will still be written)" >&2
fi

# Find current session: most recently modified .jsonl across all project dirs
RECENT=$(ls -t ~/.claude/projects/*/*.jsonl 2>/dev/null | head -1)
if [[ -z "$RECENT" ]]; then
    echo "Error: no session JSONL found under ~/.claude/projects/" >&2
    exit 1
fi

SESSION_ID=$(basename "$RECENT" .jsonl)
CURRENT_DIR=$(basename "$(dirname "$RECENT")")

mkdir -p ~/.claude/session-targets
MARKER="$HOME/.claude/session-targets/${SESSION_ID}.target"

{
    echo "target_cwd=$TARGET"
    [[ -n "$TITLE" ]] && echo "title=$TITLE"
    echo "created=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "from_dir=$CURRENT_DIR"
} > "$MARKER"

echo "✓ marked session ${SESSION_ID:0:8} for relocation"
echo "  current: $CURRENT_DIR"
echo "  target:  $TARGET"
[[ -n "$TITLE" ]] && echo "  title:   $TITLE"
echo "  marker:  $MARKER"
echo ""
echo "Will be moved on SessionEnd. To cancel: rm $MARKER"
