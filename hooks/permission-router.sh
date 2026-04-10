#!/bin/bash
# 智能权限路由：终端前台 → 终端内审批，否则 → Mr. Krabs bubble
# 替代原来的 HTTP hook，改用 command hook + 条件转发

INPUT=$(cat)

# 检查当前前台 app 是否是终端
FRONT_APP=$(/usr/bin/osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true' 2>/dev/null)

case "$FRONT_APP" in
  Terminal|iTerm2|Alacritty|kitty|WezTerm|Warp)
    # 用户在终端，直接退出，让 Claude Code 终端内提示
    exit 0
    ;;
esac

# 不在终端 → 转发给 Mr. Krabs bubble
# --connect-timeout 2 让"Mr. Krabs 没启动"场景秒退（而不是等 600s 超时）
RESPONSE=$(echo "$INPUT" | /usr/bin/curl -s -X POST http://127.0.0.1:23333/permission \
  -H "Content-Type: application/json" \
  -d @- \
  --connect-timeout 2 \
  --max-time 600 2>/dev/null)
CURL_RC=$?

if [ $CURL_RC -ne 0 ]; then
  # Mr. Krabs HTTP 不可达 → 静默退出 0，让 Claude Code 走默认 prompt 流程
  echo "[permission-router] Mr. Krabs HTTP 23333 unreachable (curl exit $CURL_RC), falling through to default prompt" >&2
  exit 0
fi

if [ -n "$RESPONSE" ]; then
  echo "$RESPONSE"
fi
