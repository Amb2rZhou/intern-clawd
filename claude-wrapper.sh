#!/bin/bash
# Claude wrapper: Main Agent (secretary) + ritual command routing
# Called by Claude-to-IM Bridge as a drop-in replacement for `claude`
#
# Architecture:
#   User → wrapper → Main Agent (secretary, global view, sees both domains)
#   Ritual commands (standup/weekly/reflect/archive/lint) → hard-routed (fast + saves tokens)

REAL_CLAUDE="${CLAUDE_BIN:-$(command -v claude || echo $HOME/.local/bin/claude)}"
CLAWD_DIR="${CLAWD_DIR:-$HOME/.clawd}"

# Read language preference from boss-profile.md (default: English)
LANG_PREF="English"
if [[ -f "$CLAWD_DIR/shared-wiki/boss-profile.md" ]]; then
    _detected=$(grep -i "english\|中文\|chinese\|japanese\|日本語" "$CLAWD_DIR/shared-wiki/boss-profile.md" | head -1)
    case "$_detected" in
        *中文*|*Chinese*) LANG_PREF="Chinese" ;;
        *日本語*|*Japanese*) LANG_PREF="Japanese" ;;
    esac
fi
LANG_INSTRUCTION="Reply in ${LANG_PREF}. Use a helpful, non-directive tone (suggest, don't command)."

# === Extract user message ===
USER_MSG=""
ARGS=("$@")
for i in "${!ARGS[@]}"; do
    if [[ "${ARGS[$i]}" == "-p" ]] && [[ $((i+1)) -lt ${#ARGS[@]} ]]; then
        USER_MSG="${ARGS[$((i+1))]}"
        break
    fi
done

if [[ -z "$USER_MSG" ]]; then
    for arg in "$@"; do
        [[ "$arg" != -* ]] && USER_MSG="${USER_MSG} ${arg}"
    done
    USER_MSG="${USER_MSG# }"
fi

# === Ritual commands (hard-routed, skip main agent, saves tokens) ===

# Archive / Resume
if grep -qiE "^(归档|继续|archive|resume)[[:space:]]+[^[:space:]]" <<< "$USER_MSG"; then
    exec "$REAL_CLAUDE" -p "User sent a wiki management command: $(printf '%q' "$USER_MSG")

Rules:
- 'resume <project>' or '继续': update the project's active date to today in work and life index.md
- 'archive <project>' or '归档': move the entry to the bottom of index.md and mark as (archived)
- If project not found, list all projects and ask user to pick
- Append a log.md entry after the operation.
${LANG_INSTRUCTION}" --allowedTools "Read,Edit,Write,Bash" --max-turns 5 --output-format text
fi

# Standup
if grep -qiE "^(standup|站会|早)$" <<< "$USER_MSG"; then
    WORK_LOG=$(tail -20 "$CLAWD_DIR/work/wiki/log.md" 2>/dev/null || echo "(empty)")
    LIFE_LOG=$(tail -20 "$CLAWD_DIR/life/wiki/log.md" 2>/dev/null || echo "(empty)")
    exec "$REAL_CLAUDE" --append-system-prompt "Perform a standup briefing. Recent work log: ${WORK_LOG} Recent life log: ${LIFE_LOG}
${LANG_INSTRUCTION}" "$@"
fi

# Weekly
if grep -qiE "^(周会|weekly|周报)$" <<< "$USER_MSG"; then
    WORK_LOG=$(tail -80 "$CLAWD_DIR/work/wiki/log.md" 2>/dev/null || echo "(empty)")
    LIFE_LOG=$(tail -80 "$CLAWD_DIR/life/wiki/log.md" 2>/dev/null || echo "(empty)")
    WORK_INDEX=$(cat "$CLAWD_DIR/work/wiki/index.md" 2>/dev/null || echo "(empty)")
    LIFE_INDEX=$(cat "$CLAWD_DIR/life/wiki/index.md" 2>/dev/null || echo "(empty)")
    exec "$REAL_CLAUDE" -p "Perform a weekly review.

Data:
- Work log: ${WORK_LOG}
- Life log: ${LIFE_LOG}
- Work index: ${WORK_INDEX}
- Life index: ${LIFE_INDEX}

Output format:
## This Week
1-2 sentences per active project. Flag anything stuck or ahead of schedule.
## Suggestions for Next Week
Top 3 priorities.
## Questions
Observations + open questions for the boss to decide on.

Tone: reliable intern giving a briefing, no filler.
${LANG_INSTRUCTION}" --allowedTools "Read,Bash" --max-turns 8 --output-format text
fi

# Reflect
if grep -qiE "^(复盘|reflect)" <<< "$USER_MSG"; then
    exec "$REAL_CLAUDE" -p "Boss wants to do a retrospective. Guide the process:
1. Ask what they want to reflect on
2. Read relevant wiki pages and log.md
3. Build a timeline: what happened → outcome → surprises
4. Extract reusable patterns or lessons
5. After confirmation, write to $CLAWD_DIR/life/wiki/reflections/ (YAML frontmatter: title, created, trigger, tags, linked_from)
6. Update life/wiki/index.md Reflections section
${LANG_INSTRUCTION}" --allowedTools "Read,Edit,Write,Bash" --max-turns 15 --output-format text
fi

# Process inbox
if grep -qiE "^(inbox|处理inbox|处理收集|process.?inbox)$" <<< "$USER_MSG"; then
    exec "$CLAWD_DIR/collect.sh" --process
fi

# Import history
if grep -qiE "^(导入历史|import.?history)$" <<< "$USER_MSG"; then
    SCAN_RESULT=$(/usr/bin/python3 "$CLAWD_DIR/import-history.py" --scan 2>&1)
    exec "$REAL_CLAUDE" -p "User wants to import historical Claude Code sessions into the wiki.

Phase 1 scan results:
$SCAN_RESULT

Guide the user through this flow:

1. **Show scan results** in a table (sessions by project)
2. **Explain tradeoffs**:
   Pros: auto-extract knowledge from past conversations, build a complete wiki in one step, discover cross-session patterns (the graph makes this visual), future sessions get historical context
   Cons: Phase 2 (classify + archive) uses token quota from this session, auto-classification may need manual corrections, large histories take time
   Safety net: auto-backup before starting, one-command rollback available
3. **Let user choose**: a) import all, b) last N days only, c) specific project only, d) just browsing
4. On confirmation, **run backup first**: \`python3 $CLAWD_DIR/import-history.py --snapshot\`
5. Then run \`python3 $CLAWD_DIR/import-history.py --extract\`
6. Read \`$CLAWD_DIR/raw/import-manifest.json\` and extracted session files
7. Classify each (work/life), create wiki entries or log records for important ones
8. When done, run \`python3 $CLAWD_DIR/wiki-graph.py\` to generate the graph and open in browser
9. Summarize the import, remind user: \`bash ~/.clawd/rollback-import.sh\` to undo
${LANG_INSTRUCTION}" --allowedTools "Read,Edit,Write,Bash,Glob,Grep" --max-turns 30 --output-format text
fi

# Lint
if grep -qiE "^(lint|检查|check)$" <<< "$USER_MSG"; then
    exec "$REAL_CLAUDE" --append-system-prompt "Run a wiki health check: verify $CLAWD_DIR/work/wiki/ and $CLAWD_DIR/life/wiki/ index.md entries match actual files, find orphaned pages, empty pages, and broken links. Output a report.
${LANG_INSTRUCTION}" "$@"
fi

# Graph
if grep -qiE "^(关系图|graph)$" <<< "$USER_MSG"; then
    /usr/bin/python3 "$CLAWD_DIR/wiki-graph.py"
    exit $?
fi

# === Main Agent (secretary) ===

WORK_INDEX=$(head -50 "$CLAWD_DIR/work/wiki/index.md" 2>/dev/null || echo "(empty)")
LIFE_INDEX=$(head -50 "$CLAWD_DIR/life/wiki/index.md" 2>/dev/null || echo "(empty)")

SYSTEM_PROMPT=$(python3 -c "
import sys
clawd = sys.argv[1]
work_idx = sys.argv[2]
life_idx = sys.argv[3]
lang = sys.argv[4]
print(f'''You are the Boss's personal secretary agent. You manage all of Boss's work and life knowledge.

## Your responsibilities
1. **Understand intent** — determine if the message is about work, life, or cross-domain
2. **Use knowledge** — read the relevant wiki pages before answering
3. **Record everything** — log valuable interactions to log.md
4. **Proactive reminders** — surface related knowledge when relevant (e.g. if Boss asks about a work project and there's related life-domain info, mention it)

## Knowledge base structure
Work domain: {clawd}/work/wiki/ (projects, people, decisions, patterns)
Life domain: {clawd}/life/wiki/ (personal projects, topics, reflections)
Shared: {clawd}/shared-wiki/ (boss profile, coding style)

## Work domain index:
{work_idx}

## Life domain index:
{life_idx}

## Operating rules
- Read wiki pages before answering, don't guess
- Append to log.md without asking. Format: ## [YYYY-MM-DD HH:MM] {{operation}} | {{title}}
- New/modified wiki pages: confirm with Boss before writing
- When a project is mentioned, update its active date in index.md to today
- Cross-domain tasks: operate in both domains, write separate log entries

## Boss preferences
- See {clawd}/shared-wiki/boss-profile.md for full details
- Reply in {lang}. Be concise, use a suggestive tone (not directive). Don't restate known info.''')
" "$CLAWD_DIR" "$WORK_INDEX" "$LIFE_INDEX" "$LANG_PREF" 2>/dev/null)

if [[ -z "$SYSTEM_PROMPT" ]]; then
    SYSTEM_PROMPT="You are the Boss's personal secretary agent, managing work and life knowledge. ${LANG_INSTRUCTION}"
fi

exec "$REAL_CLAUDE" --append-system-prompt "$SYSTEM_PROMPT" "$@"
