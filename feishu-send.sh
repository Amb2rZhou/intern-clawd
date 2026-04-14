#!/bin/bash
# Send a message to Feishu (Lark) chat
# Usage: feishu-send.sh "message content"

MSG="$1"
if [ -z "$MSG" ]; then exit 1; fi

CLAWD_DIR="${CLAWD_DIR:-$HOME/.clawd}"
/usr/bin/python3 -c "
import sys, os
sys.path.insert(0, os.environ['CLAWD_DIR'])
from feishu_utils import send_feishu_message
send_feishu_message(sys.argv[1], tag='quick-send')
" "$MSG"
