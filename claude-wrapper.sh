#!/bin/bash
# Claude wrapper: 主 Agent（秘书）+ 特殊命令硬路由
# 被 Claude-to-IM Bridge 调用，替代直接调 claude
#
# 架构:
#   用户 → wrapper → 主 Agent（秘书，全局视角，两个域都能看）
#   特殊命令（站会/周会/复盘/归档/lint）→ 硬路由（快+省 token）

REAL_CLAUDE="${CLAUDE_BIN:-$(command -v claude || echo $HOME/.local/bin/claude)}"
CLAWD_DIR="${CLAWD_DIR:-$HOME/.clawd}"

# === 提取用户消息 ===
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

# === 特殊命令（硬路由，不走主 Agent，省 token） ===

# 归档/继续
if grep -qiE "^(归档|继续)[[:space:]]+[^[:space:]]" <<< "$USER_MSG"; then
    exec "$REAL_CLAUDE" -p "用户回复了 wiki 整理提醒。消息: $(printf '%q' "$USER_MSG")

处理规则:
- 「继续 项目名」: 更新该项目在 work 和 life 的 index.md 里的 active 日期为今天
- 「归档 项目名」: 把该条目从 index.md 移到底部并加 (archived) 标记
- 找不到项目名就列出所有项目让用户选
操作完后追加 log.md 记录。" --allowedTools "Read,Edit,Write,Bash" --max-turns 5 --output-format text
fi

# 站会
if grep -qiE "^(standup|站会|早)$" <<< "$USER_MSG"; then
    WORK_LOG=$(tail -20 "$CLAWD_DIR/work/wiki/log.md" 2>/dev/null || echo "（无记录）")
    LIFE_LOG=$(tail -20 "$CLAWD_DIR/life/wiki/log.md" 2>/dev/null || echo "（无记录）")
    exec "$REAL_CLAUDE" --append-system-prompt "执行站会汇报。最近的 work log: ${WORK_LOG} 最近的 life log: ${LIFE_LOG}" "$@"
fi

# 周会
if grep -qiE "^(周会|weekly|周报)$" <<< "$USER_MSG"; then
    WORK_LOG=$(tail -80 "$CLAWD_DIR/work/wiki/log.md" 2>/dev/null || echo "（无记录）")
    LIFE_LOG=$(tail -80 "$CLAWD_DIR/life/wiki/log.md" 2>/dev/null || echo "（无记录）")
    WORK_INDEX=$(cat "$CLAWD_DIR/work/wiki/index.md" 2>/dev/null || echo "（空）")
    LIFE_INDEX=$(cat "$CLAWD_DIR/life/wiki/index.md" 2>/dev/null || echo "（空）")
    exec "$REAL_CLAUDE" -p "执行周会。

数据源:
- Work log: ${WORK_LOG}
- Life log: ${LIFE_LOG}
- Work index: ${WORK_INDEX}
- Life index: ${LIFE_INDEX}

输出:
## 本周回顾
每个活跃项目 1-2 句进展，标注卡住/超预期的
## 下周建议
按优先级，最多 3 条
## 提问
异常观察 + 开放性问题让 boss 判断

语气：靠谱实习生汇报，不要套话。" --allowedTools "Read,Bash" --max-turns 8 --output-format text
fi

# 复盘
if grep -qiE "^(复盘|reflect)" <<< "$USER_MSG"; then
    exec "$REAL_CLAUDE" -p "Boss 想做一次复盘。引导过程：
1. 问 boss 想复盘什么
2. 读取相关 wiki 页面和 log.md
3. 整理时间线：做了什么 → 结果 → 意外发现
4. 提炼可复用的模式或教训
5. 确认后写入 $CLAWD_DIR/life/wiki/reflections/（YAML frontmatter: title, created, trigger, tags, linked_from）
6. 更新 life/wiki/index.md 的 Reflections 区域
中文，建议性表达。" --allowedTools "Read,Edit,Write,Bash" --max-turns 15 --output-format text
fi

# 处理 inbox
if grep -qiE "^(inbox|处理inbox|处理收集)$" <<< "$USER_MSG"; then
    exec "$CLAWD_DIR/collect.sh" --process
fi

# lint
if grep -qiE "^(lint|检查)$" <<< "$USER_MSG"; then
    exec "$REAL_CLAUDE" --append-system-prompt "执行 wiki 健康检查：检查 $CLAWD_DIR/work/wiki/ 和 $CLAWD_DIR/life/wiki/ 的 index.md 与实际文件是否一致，检查孤立页面、空页面、死链。输出报告。" "$@"
fi

# === 主 Agent（秘书） ===

# 注入两个域的 index
WORK_INDEX=$(head -50 "$CLAWD_DIR/work/wiki/index.md" 2>/dev/null || echo "（空）")
LIFE_INDEX=$(head -50 "$CLAWD_DIR/life/wiki/index.md" 2>/dev/null || echo "（空）")

# 用 python 安全构建系统提示
SYSTEM_PROMPT=$(python3 -c "
import sys
clawd = sys.argv[1]
work_idx = sys.argv[2]
life_idx = sys.argv[3]
print(f'''你是 Boss 的私人秘书 Agent。你管理 Boss 的全部工作和生活知识。

## 你的职责
1. **理解意图** — 判断 boss 的消息属于工作、生活、还是跨域/闲聊
2. **调用知识** — 根据判断去对应域的 wiki 读取详情再回答
3. **记录一切** — 有价值的交互都要写 log.md
4. **主动提醒** — 发现关联知识时主动提供（比如 boss 问工作项目时，如果 life 域有相关的就一起说）

## 知识库结构
工作域: {clawd}/work/wiki/（项目、同事、决策、模式）
生活域: {clawd}/life/wiki/（个人项目、话题、复盘）
共享: {clawd}/shared-wiki/（boss 偏好、编码风格）

## Work 域 index:
{work_idx}

## Life 域 index:
{life_idx}

## 操作规则
- 读 wiki 页面后再回答，不要凭空猜
- log.md 自动追加，不需要确认。格式: ## [YYYY-MM-DD HH:MM] {{operation}} | {{标题}}
- wiki 页面新建/修改：先确认再写
- 涉及某项目时，更新对应 index.md 的 active 日期为今天
- 跨域任务（比如「把工作经验总结到 life 复盘」）：两个域都操作，分别写 log

## Boss 偏好
- 中文回复，精简，建议性表达
- 不用"必须""应该"，不复述已知内容
- 详见 {clawd}/shared-wiki/boss-profile.md''')
" "$CLAWD_DIR" "$WORK_INDEX" "$LIFE_INDEX" 2>/dev/null)

if [[ -z "$SYSTEM_PROMPT" ]]; then
    SYSTEM_PROMPT="你是 Boss 的私人秘书 Agent，管理工作和生活知识。中文回复，精简。"
fi

exec "$REAL_CLAUDE" --append-system-prompt "$SYSTEM_PROMPT" "$@"
