#!/bin/bash
# 一键配置 clawd intern agent 系统
# 用法: bash setup.sh
# 前提: macOS, Python 3, Claude Code 已安装, SSH key 已配 GitHub

set -e

CLAWD_DIR="$HOME/.clawd"
CTI_DIR="$HOME/.claude-to-im"
CLAUDE_DIR="$HOME/.claude"

echo "=== Clawd Intern Agent Setup ==="

# 1. 检查依赖
echo "[1/9] 检查依赖..."
command -v python3 >/dev/null || { echo "ERROR: 需要 python3"; exit 1; }
command -v git >/dev/null || { echo "ERROR: 需要 git"; exit 1; }

# inject-wiki-context.sh 硬编码 /usr/bin/python3，确保它存在
# 没装的话 macOS 用户跑: xcode-select --install
if [[ ! -x /usr/bin/python3 ]]; then
    echo "ERROR: /usr/bin/python3 不存在"
    echo "  hooks/inject-wiki-context.sh 硬编码使用 /usr/bin/python3"
    echo "  macOS: 跑 xcode-select --install 装 Command Line Tools"
    echo "  注意：目前仅支持 macOS"
    exit 1
fi

CLAUDE_BIN=$(which claude 2>/dev/null || echo "$HOME/.local/bin/claude")
if [[ ! -x "$CLAUDE_BIN" ]]; then
    echo "WARNING: 没找到 claude CLI，手机渠道可能不工作"
fi

# 2. 更新 wrapper 里的路径
echo "[2/9] 配置 wrapper 路径..."
if [[ -f "$CLAWD_DIR/claude-wrapper.sh" ]]; then
    sed -i '' "s|REAL_CLAUDE=.*|REAL_CLAUDE=\"$CLAUDE_BIN\"|" "$CLAWD_DIR/claude-wrapper.sh"
    chmod +x "$CLAWD_DIR/claude-wrapper.sh"
    echo "  wrapper -> $CLAUDE_BIN"
fi

# 3. 创建 wiki 目录结构（如果不存在）
echo "[3/9] 确保目录结构..."
for domain in work life; do
    mkdir -p "$CLAWD_DIR/$domain/wiki/projects"
    mkdir -p "$CLAWD_DIR/$domain/wiki/decisions"
    mkdir -p "$CLAWD_DIR/$domain/raw"
    # 创建空 log 和 index（如果不存在）
    [[ -f "$CLAWD_DIR/$domain/wiki/log.md" ]] || echo "# ${domain^} Log" > "$CLAWD_DIR/$domain/wiki/log.md"
    [[ -f "$CLAWD_DIR/$domain/wiki/index.md" ]] || echo "# ${domain^} Wiki Index" > "$CLAWD_DIR/$domain/wiki/index.md"
done
mkdir -p "$CLAWD_DIR/shared-wiki"

# 4. 配置 Claude-to-IM（如果有 config.env.example）
echo "[4/9] 配置 Claude-to-IM..."
if [[ -d "$CTI_DIR" ]]; then
    if [[ ! -f "$CTI_DIR/config.env" ]] && [[ -f "$CLAWD_DIR/config.env.example" ]]; then
        cp "$CLAWD_DIR/config.env.example" "$CTI_DIR/config.env"
        chmod 600 "$CTI_DIR/config.env"
        echo "  已创建 config.env，请填入 IM 凭证: $CTI_DIR/config.env"
    elif [[ -f "$CTI_DIR/config.env" ]]; then
        # 更新路径
        sed -i '' "s|CTI_DEFAULT_WORKDIR=.*|CTI_DEFAULT_WORKDIR=$CLAWD_DIR|" "$CTI_DIR/config.env"
        sed -i '' "s|CTI_CLAUDE_CODE_EXECUTABLE=.*|CTI_CLAUDE_CODE_EXECUTABLE=$CLAWD_DIR/claude-wrapper.sh|" "$CTI_DIR/config.env"
        echo "  config.env 路径已更新"
    fi
else
    echo "  Claude-to-IM 未安装，跳过（手机渠道不可用）"
fi

# 5. 安装全局 CLAUDE.md wiki 同步规则
echo "[5/9] 配置全局 CLAUDE.md..."
mkdir -p "$CLAUDE_DIR"
if [[ -f "$CLAUDE_DIR/CLAUDE.md" ]]; then
    if ! grep -q "Wiki 知识同步" "$CLAUDE_DIR/CLAUDE.md"; then
        # 先备份，便于 uninstall.sh 精准还原
        BACKUP="$CLAUDE_DIR/CLAUDE.md.before-clawd-$(date +%Y%m%d-%H%M%S)"
        cp "$CLAUDE_DIR/CLAUDE.md" "$BACKUP"
        echo "  已备份原文件到 $BACKUP"
        cat >> "$CLAUDE_DIR/CLAUDE.md" << 'WIKI_RULE'

## Wiki 知识同步（仅当 ~/.clawd 存在）

如果 `~/.clawd/` 目录存在（即用户装了 intern-clawd 秘书系统），且本次交互产生了值得持久化的知识（项目决策、架构变更、重要结论），可以在任务结束时考虑：

1. 追加一条到 `~/.clawd/{work|life}/wiki/log.md`，格式：`## [YYYY-MM-DD HH:MM] {operation} | {标题}`，1-3 行摘要
2. 涉及已有 wiki 页面更新时，先和用户确认

`~/.clawd` 不存在则跳过此规则。闲聊、简单问答、跟知识库无关的任务也跳过。
WIKI_RULE
        echo "  已添加 wiki 同步规则"
    else
        echo "  wiki 同步规则已存在"
    fi
fi

# 6. 设置 cron
echo "[6/9] 设置定时任务..."
CRON_LINE="7 9 * * * /usr/bin/python3 $CLAWD_DIR/reorganize-index.py --ask >> $CLAWD_DIR/reorganize.log 2>&1"
if crontab -l 2>/dev/null | grep -q "reorganize-index.py"; then
    echo "  cron 已存在"
else
    (crontab -l 2>/dev/null; echo "# Wiki index reorganize - daily 9:07 AM"; echo "$CRON_LINE") | crontab -
    echo "  已添加每日 9:07 AM 整理任务"
fi

# 7. 安装 Claude Code hooks
echo "[7/9] 安装 Claude Code hooks..."
mkdir -p "$CLAUDE_DIR/hooks"
for f in "$CLAWD_DIR/claude-hooks/"*; do
    [[ -f "$f" ]] || continue
    base=$(basename "$f")
    cp "$f" "$CLAUDE_DIR/hooks/$base"
    chmod +x "$CLAUDE_DIR/hooks/$base" 2>/dev/null || true
    echo "  已复制 $base"
done

# 8. 配置 settings.json hooks（用 python3 做 JSON merge）
echo "[8/9] 配置 settings.json hooks..."
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
            print("  WARNING: settings.json 格式错误，已备份为 .bak 并重建")
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
            print(f"  已添加 {event}: {h['command'].split('/')[-1]}")
        else:
            print(f"  {event} 已存在，跳过")

with open(settings_file, "w") as f:
    json.dump(settings, f, indent=2, ensure_ascii=False)
    f.write("\n")
PYEOF

# 9. 添加 zsh aliases
echo "[9/9] 配置 zsh aliases..."
ZSHRC="$HOME/.zshrc"
touch "$ZSHRC"

add_alias() {
    local line="$1"
    local name="$2"
    if ! grep -q "alias $name=" "$ZSHRC"; then
        echo "" >> "$ZSHRC"
        echo "# intern-clawd" >> "$ZSHRC"
        echo "$line" >> "$ZSHRC"
        echo "  已添加: $line"
    else
        echo "  $name alias 已存在，跳过"
    fi
}

add_alias "alias clawd='cd ~/.clawd && claude'" "clawd"
add_alias "alias inbox='~/.clawd/collect.sh'" "inbox"

echo ""
echo "=== 配置完成 ==="
echo ""
echo "下一步："
echo "  1. 编辑 shared-wiki/boss-profile.md（填写你的身份/偏好/目标）"
echo "  2. source ~/.zshrc（或重开终端）"
echo "  3. 输入 clawd 进入秘书模式，说「站会」试试"
echo ""
echo "可选："
echo "  - 全局快捷键 ⌃⌥C：见 README §可选入口"
echo "  - 手机 IM 通道：见 README §手机 IM 通道"
