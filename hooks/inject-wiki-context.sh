#!/bin/bash
# Claude Code SessionStart hook: only when cwd is the secretary workspace (~/.clawd or subdirectory)
# Injects dual-domain wiki index + progress.md.
#
# Design:
# - Secretary persona / rules / format come from ~/.clawd/CLAUDE.md (auto-loaded when cwd is .clawd)
# - This hook only injects "dynamic content": current index state + cross-session continuity
# - Non-secretary cwd exits immediately; global ~/.claude/CLAUDE.md wiki sync rule covers those
#
# Savings: ~1.4K tok per non-secretary session; ~1K tok dedup within secretary sessions

CLAWD_DIR="${CLAWD_DIR:-$HOME/.clawd}"

INPUT=$(cat)

# Pure bash cwd extraction (skip python3, save 50-200ms startup)
# JSON looks like {"cwd":"/path/...","session_id":"..."}
CWD=$(printf '%s' "$INPUT" | grep -o '"cwd"[[:space:]]*:[[:space:]]*"[^"]*"' | sed 's/.*"\([^"]*\)"$/\1/')

# Gate: only inject in $CLAWD_DIR workspace
# Early return — non-secretary sessions don't start python3, zero pollution on vanilla CC
case "$CWD" in
  "$CLAWD_DIR"|"$CLAWD_DIR"/*) ;;
  *) exit 0 ;;
esac

# Only start python3 when actually in secretary workspace
/usr/bin/python3 -c "
import json

clawd = '$CLAWD_DIR'

def read_file(path, max_lines=50):
    try:
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()[:max_lines]
            return ''.join(lines).strip()
    except:
        return '(empty)'

work_idx = read_file(f'{clawd}/work/wiki/index.md')
life_idx = read_file(f'{clawd}/life/wiki/index.md')
progress = read_file(f'{clawd}/progress.md', max_lines=30)

import os
archives = []
for d in ['work', 'life']:
    p = f'{clawd}/{d}/wiki/index-archive.md'
    if os.path.exists(p):
        archives.append(d)

progress_block = ''
if progress and progress != '(empty)':
    progress_block = f'''

## Pending Tasks (from previous session)
{progress}
Please handle these first or ask the boss whether to continue.'''

archive_block = ''
if archives:
    archive_block = f'''

> Note: {', '.join(archives)} domain(s) have index-archive.md (cold tier). Check cold tier if a relevant page isn't found in hot tier.'''

# Only inject dynamic state; persona/rules come from ~/.clawd/CLAUDE.md
prompt = f'''## Wiki Current State (dynamically injected)

### Work domain index
{work_idx}

### Life domain index
{life_idx}{archive_block}{progress_block}'''

print(json.dumps({'appendSystemPrompt': prompt}, ensure_ascii=False))
"
