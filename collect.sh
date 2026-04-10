#!/bin/bash
# 快速 context 收集：剪贴板 → inbox.md
# 被 macOS Shortcuts.app / 全局快捷键 / 终端调用
#
# 用法:
#   collect.sh                  # 从剪贴板（处理多种编码）
#   collect.sh --process        # 让秘书处理 inbox

# 调试日志（排查 Quick Action / Shortcuts 触发问题，不需要可删）
echo "[$(date '+%Y-%m-%d %H:%M:%S')] called pid=$$ ppid=$PPID args=$* PATH=$PATH PWD=$PWD USER=$USER" >> /tmp/collect-debug.log 2>&1

CLAWD_DIR="${CLAWD_DIR:-$HOME/.clawd}"
INBOX="$CLAWD_DIR/inbox.md"
REAL_CLAUDE="${CLAUDE_BIN:-$(command -v claude || echo $HOME/.local/bin/claude)}"

# === --process 模式：秘书处理 inbox ===
if [[ "$1" == "--process" ]]; then
    if [[ ! -s "$INBOX" ]]; then
        echo "inbox 为空"
        exit 0
    fi
    INBOX_CONTENT=$(cat "$INBOX")
    exec "$REAL_CLAUDE" -p "以下是 inbox 里收集的内容片段，帮我处理：

${INBOX_CONTENT}

处理规则：
1. 逐条判断属于 work 还是 life 域
2. 提炼要点，关联已有 wiki 页面
3. 有价值的内容追加到对应域的 log.md
4. 如果内容足够丰富值得单独建页，先确认再写
5. 处理完后清空 inbox.md（写入空字符串）

读取 wiki index 了解当前知识结构后再处理。" \
    --append-system-prompt "$(cat "$CLAWD_DIR/work/wiki/index.md" 2>/dev/null) $(cat "$CLAWD_DIR/life/wiki/index.md" 2>/dev/null)" \
    --allowedTools "Read,Edit,Write,Bash" --max-turns 10 --output-format text
fi

# === 收集模式 ===

TIMESTAMP=$(date "+%Y-%m-%d %H:%M")
export COLLECT_TIMESTAMP="$TIMESTAMP"
export CLAWD_DIR

python3 -c '
import subprocess, sys, os

inbox = os.path.join(os.environ["CLAWD_DIR"], "inbox.md")
ts = os.environ.get("COLLECT_TIMESTAMP", "unknown")

# 从剪贴板读取
r = subprocess.run(["/usr/bin/pbpaste"], capture_output=True)
raw = r.stdout

# 尝试多种编码
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
        "display notification \"没有选中内容\" with title \"收集失败\""])
    sys.exit(1)

# 获取来源 app
try:
    r = subprocess.run(["/usr/bin/osascript", "-e",
        "tell application \"System Events\" to get name of first application process whose frontmost is true"],
        capture_output=True, text=True, timeout=3)
    source = r.stdout.strip() or "unknown"
except:
    source = "unknown"

# 写入 inbox (UTF-8)
with open(inbox, "a", encoding="utf-8") as f:
    f.write(f"\n## [{ts}] from: {source}\n\n{content}\n\n---\n")

# 通知（注意：osascript 通知在 macOS Sequoia 可能静默失败，
# 推荐改用 Shortcuts.app 内置「显示通知」action 包裹本脚本）
preview = content[:50].replace(chr(34), chr(39))
subprocess.run(["/usr/bin/osascript", "-e",
    f"display notification \"{preview}...\" with title \"已收集到 inbox\""])

print("[collect] 已保存到 inbox.md")

# telemetry
try:
    sys.path.insert(0, os.environ["CLAWD_DIR"])
    from telemetry import log_op
    log_op("collect", source=source, detail=content[:80])
except:
    pass
'
