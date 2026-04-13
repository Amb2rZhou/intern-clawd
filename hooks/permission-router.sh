#!/bin/bash
# 智能权限路由：终端前台 → 终端内审批，否则 → 静默放行
# PermissionRequest hook，可选安装

INPUT=$(cat)

# 检查当前前台 app 是否是终端
FRONT_APP=$(/usr/bin/osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true' 2>/dev/null)

case "$FRONT_APP" in
  Terminal|iTerm2|Alacritty|kitty|WezTerm|Warp)
    # 用户在终端，直接退出，让 Claude Code 终端内提示
    exit 0
    ;;
esac

# 不在终端 → 静默放���，让 Claude Code 走默认 prompt 流程
# 如果你有桌面审批 app，可以在这里加 HTTP 转发
exit 0
