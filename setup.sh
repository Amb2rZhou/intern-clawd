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
echo "[1/6] 检查依赖..."
command -v python3 >/dev/null || { echo "ERROR: 需要 python3"; exit 1; }
command -v git >/dev/null || { echo "ERROR: 需要 git"; exit 1; }

# inject-wiki-context.sh 硬编码 /usr/bin/python3，确保它存在
# 没装的话 macOS 用户跑: xcode-select --install
if [[ ! -x /usr/bin/python3 ]]; then
    echo "ERROR: /usr/bin/python3 不存在"
    echo "  hooks/inject-wiki-context.sh 硬编码使用 /usr/bin/python3"
    echo "  macOS: 跑 xcode-select --install 装 Command Line Tools"
    echo "  Linux: 创建符号链接 sudo ln -s \$(which python3) /usr/bin/python3"
    exit 1
fi

CLAUDE_BIN=$(which claude 2>/dev/null || echo "$HOME/.local/bin/claude")
if [[ ! -x "$CLAUDE_BIN" ]]; then
    echo "WARNING: 没找到 claude CLI，手机渠道可能不工作"
fi

# 2. 更新 wrapper 里的路径
echo "[2/6] 配置 wrapper 路径..."
if [[ -f "$CLAWD_DIR/claude-wrapper.sh" ]]; then
    sed -i '' "s|REAL_CLAUDE=.*|REAL_CLAUDE=\"$CLAUDE_BIN\"|" "$CLAWD_DIR/claude-wrapper.sh"
    chmod +x "$CLAWD_DIR/claude-wrapper.sh"
    echo "  wrapper -> $CLAUDE_BIN"
fi

# 3. 创建 wiki 目录结构（如果不存在）
echo "[3/6] 确保目录结构..."
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
echo "[4/6] 配置 Claude-to-IM..."
if [[ -d "$CTI_DIR" ]]; then
    if [[ ! -f "$CTI_DIR/config.env" ]] && [[ -f "$CLAWD_DIR/config.env.example" ]]; then
        cp "$CLAWD_DIR/config.env.example" "$CTI_DIR/config.env"
        chmod 600 "$CTI_DIR/config.env"
        echo "  已创建 config.env，请填入飞书凭证: $CTI_DIR/config.env"
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
echo "[5/6] 配置全局 CLAUDE.md..."
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
echo "[6/6] 设置定时任务..."
CRON_LINE="7 9 * * * /usr/bin/python3 $CLAWD_DIR/reorganize-index.py --ask >> $CLAWD_DIR/reorganize.log 2>&1"
if crontab -l 2>/dev/null | grep -q "reorganize-index.py"; then
    echo "  cron 已存在"
else
    (crontab -l 2>/dev/null; echo "# Wiki index reorganize - daily 9:07 AM"; echo "$CRON_LINE") | crontab -
    echo "  已添加每日 9:07 AM 整理任务"
fi

echo ""
echo "=== 配置完成 ==="
echo "渠道状态:"
echo "  终端/桌面: ~/.claude/CLAUDE.md 自动同步 wiki"
echo "  手机(飞书/微信): claude-wrapper.sh -> Claude-to-IM Bridge"
echo "  定时整理: cron -> reorganize-index.py -> 飞书提醒"
echo ""
echo "如需配置飞书凭证，编辑: $CTI_DIR/config.env"
