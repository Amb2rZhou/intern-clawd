#!/bin/bash
# Smart permission routing: terminal foreground → terminal approval, otherwise → silent passthrough
# PermissionRequest hook, optional install

INPUT=$(cat)

# Check if the frontmost app is a terminal
FRONT_APP=$(/usr/bin/osascript -e 'tell application "System Events" to get name of first application process whose frontmost is true' 2>/dev/null)

case "$FRONT_APP" in
  Terminal|iTerm2|Alacritty|kitty|WezTerm|Warp)
    # User is in terminal, exit and let Claude Code prompt in-terminal
    exit 0
    ;;
esac

# Not in terminal → silent passthrough, let Claude Code use its default prompt flow
# If you have a desktop approval app, add HTTP forwarding here
exit 0
