#!/bin/bash
# Claude Code SessionStart hook: 仅当 cwd 是秘书工作区 (~/.clawd 或子目录) 时
# 注入双域 wiki index + progress.md。
#
# 设计：
# - 秘书 persona / 规则 / 格式由 ~/.clawd/CLAUDE.md 提供（cwd 在 .clawd 时自动加载）
# - 此 hook 只补充"动态内容"：index 当前状态 + 跨 session 接力
# - 非秘书 cwd 直接 exit 0，由全局 ~/.claude/CLAUDE.md 的 wiki sync 规则兜底
#
# 节省：每个非秘书 session ~1.4K tok；秘书 session 内部去重 ~1K tok

CLAWD_DIR="${CLAWD_DIR:-$HOME/.clawd}"

# 读取 hook 输入获取 cwd
INPUT=$(cat)
CWD=$(echo "$INPUT" | /usr/bin/python3 -c "import json,sys
try:
    print(json.loads(sys.stdin.read()).get('cwd',''))
except: pass" 2>/dev/null)

# cwd 门控：只在 $CLAWD_DIR 工作区注入
case "$CWD" in
  "$CLAWD_DIR"|"$CLAWD_DIR"/*) ;;
  *) exit 0 ;;
esac

/usr/bin/python3 -c "
import json

clawd = '$CLAWD_DIR'

def read_file(path, max_lines=50):
    try:
        with open(path, encoding='utf-8') as f:
            lines = f.readlines()[:max_lines]
            return ''.join(lines).strip()
    except:
        return '（空）'

work_idx = read_file(f'{clawd}/work/wiki/index.md')
life_idx = read_file(f'{clawd}/life/wiki/index.md')
progress = read_file(f'{clawd}/progress.md', max_lines=30)

progress_block = ''
if progress and progress != '（空）':
    progress_block = f'''

## 未完成任务（上个 session 遗留）
{progress}
请先处理或询问 boss 是否继续。'''

# 只注入动态状态，人格/规则交给 ~/.clawd/CLAUDE.md
prompt = f'''## Wiki 当前状态（动态注入）

### Work 域 index
{work_idx}

### Life 域 index
{life_idx}{progress_block}'''

print(json.dumps({'appendSystemPrompt': prompt}, ensure_ascii=False))
"
