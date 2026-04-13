# 换电脑迁移清单 — clawd intern agent 系统

> 最后更新：2026-04-10
> 适用：macOS 14+（已验证 Sequoia 15.6）
>
> 这份文档记录从零搭建整套秘书系统需要的所有步骤。`setup.sh` 自动化覆盖了一部分，剩余的（GUI 操作 / 手动配置 / 第三方依赖）在下面手工列出。

---

## 0. 前置依赖（先装好）

| 工具 | 用途 | 装法 |
|---|---|---|
| Python 3 | hook 脚本、wiki 维护 | macOS 自带 `/usr/bin/python3`，或 [python.org](https://python.org) |
| git | 版本控制 | `xcode-select --install` |
| Claude Code CLI | 主体 | [官方安装](https://docs.claude.com/claude-code) → `claude` 命令可用 |
| GitHub SSH key | 拉私有 repo | 生成 + 上传到 GitHub |

把 `~/.clawd/` 整个目录从备份/旧机迁过来（rsync 或 git clone）。这一步是基础，后面所有命令都假设这个目录已存在。

---

## 1. 跑 setup.sh（自动部分）

```bash
cd ~/.clawd
bash setup.sh
```

会自动做：
- ✅ 检查 python3 / git / claude CLI
- ✅ 修正 `claude-wrapper.sh` 里的 claude 路径
- ✅ 创建 work/life wiki 目录骨架（projects/decisions/raw + 空 log.md/index.md）
- ✅ Claude-to-IM bridge 配置（如果 `~/.claude-to-im` 已装）
- ✅ 全局 `~/.claude/CLAUDE.md` 注入「Wiki 知识同步」规则
- ✅ cron 定时任务：每日 9:07 AM 跑 `reorganize-index.py`

---

## 2. 环境变量（写到 ~/.zshrc）

```bash
# Claude Code OAuth token（从旧机备份或重新生成）
export CLAUDE_CODE_OAUTH_TOKEN=sk-ant-oat01-xxxxxxx

# 各种 API key（按需）
export DASHSCOPE_API_KEY=sk-xxx
export DEEPSEEK_API_KEY=sk-xxx

# clawd 快捷 alias（核心，必加）
alias clawd='cd ~/.clawd && claude'           # 一词进秘书模式
alias inbox='~/.clawd/collect.sh'             # 终端版剪贴板收集
alias cti="bash ~/.agents/skills/claude-to-im/scripts/daemon.sh"  # claude-to-im daemon
```

加完 `source ~/.zshrc` 或重开终端。

---

## 3. Claude Code Hooks（手动复制）

`setup.sh` 不动 hooks，需要手动配置。

### 3.1 SessionEnd: 路由 + 转写

`~/.claude/hooks/` 下需要这两个文件：

```bash
# 这两个文件随 ~/.clawd 一起从备份带过来即可
ls ~/.claude/hooks/
# 应该看到：mark-session-project.sh, session-relocate.py
```

如果丢了，从 `~/.clawd/setup-new-machine.md` 引用的旧备份恢复，或者重新写（核心逻辑：marker 文件 → SessionEnd hook 把 jsonl + sidecar 搬到目标 cwd 目录）。

### 3.2 settings.json hooks 配置

`~/.claude/settings.json` 需要包含的关键 hook 条目（顺序无关）：

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [{ "type": "command", "command": "$HOME/.clawd/hooks/inject-wiki-context.sh" }] }
    ],
    "SessionEnd": [
      { "hooks": [{ "type": "command", "command": "/usr/bin/python3 $HOME/.clawd/extract-session.py" }] },
      { "hooks": [{ "type": "command", "command": "/usr/bin/python3 $HOME/.claude/hooks/session-relocate.py" }] }
    ],
    "PermissionRequest": [
      { "hooks": [{ "type": "command", "command": "$HOME/.clawd/hooks/permission-router.sh", "timeout": 600 }] }
    ]
  }
}
```

**注意**：PermissionRequest hook 是可选的。如果装了，默认行为是终端前台走终端内审批，否则静默放行。

---

## 4. 全局快捷键 ⌃⌥C 收集到 inbox（GUI 操作）

> ⚠️ **不要用 `~/.clawd/create-quick-action.sh`**！它生成的 Automator workflow 在 macOS Sequoia 15.6 已经不兼容（`AMWorkflow checkDocumentVersion:` 抛异常），服务菜单虽然能看到但点不动。改用下面的 Shortcuts.app 路线。

### 4.1 在 Shortcuts.app 建快捷指令

1. Spotlight 搜「快捷指令」/ Shortcuts.app，打开
2. 左上角 `+` 新建一个 shortcut
3. 右侧搜索框输入 `shell` → 双击「**运行 Shell 脚本**」加进来
4. 把脚本内容**全选删掉**，粘贴：
   ```
   $HOME/.clawd/collect.sh
   ```
   ⚠️ 一定要绝对路径，不要 `~`，Quick Action 沙盒里 `~` 不展开
5. Shell 选 `/bin/zsh`，「以管理员身份运行」**不要勾**
6. 再搜 `通知` → 双击「**显示通知**」加进来（osascript 在 Sequoia 静默失败，必须用 Shortcuts 内置通知）
   - 标题：`已收集到 Wiki`
   - 正文：`✓ 内容已存入 inbox`
7. 右上角 `ⓘ` 信息按钮 → 「详细信息」tab → 勾选「**作为快速操作使用**」
8. 改名（可选）：回主 Shortcuts 窗口右键卡片 → 重命名为「收集到Wiki」

### 4.2 绑全局快捷键（⚠️ 关键步骤，容易漏）

Shortcuts.app 信息面板里设的「指定快捷键」**不会**自动同步到系统服务列表。必须手动到系统设置再绑一次：

```
系统设置 → 键盘 → 键盘快捷键… → 服务（左侧栏）
→ 「快捷指令」分组（点左边小三角展开）
→ 找到刚建的那条
→ 双击右边快捷键栏 → 按下 ⌃⌥C → 「完成」
```

### 4.3 验证

```bash
# 选中任意文字，⌘C 复制，然后 ⌃⌥C
# 验证：
ls -la ~/.clawd/inbox.md  # mtime 应该是刚才的时间
tail ~/.clawd/inbox.md     # 看到刚复制的内容
cat /tmp/collect-debug.log # 应该有调用记录
```

---

## 5. 已知坑点速查

| 症状 | 原因 | 修法 |
|---|---|---|
| Quick Action 服务菜单可见但点不动 | `create-quick-action.sh` 生成的 workflow 跟 Sequoia 不兼容 | 不用 Automator，改 Shortcuts.app（见 §4） |
| 通知没弹 | `osascript display notification` 在 Sequoia 被收紧，脚本编辑器/AppleScript 不出现在通知设置里 | 在 Shortcut 里加原生「显示通知」action |
| Shortcuts.app 设的快捷键无效 | 信息面板里的「指定快捷键」没同步到系统服务列表 | 手动到系统设置 → 键盘快捷键 → 服务里再绑一遍 |
| Quick Action 调脚本 `~` 不展开 | macOS Quick Action 沙盒不展开 `~` | 改用绝对路径 `$HOME/.clawd/collect.sh` |
| `~` cwd 启动的 session 全堆在 -Users-USERNAME/ | Claude Code 默认按启动 cwd 归档 | 装 `mark-session-project.sh` + `session-relocate.py` 路由 hooks |
| permission-router 卡 600s | 上游 HTTP 服务不可达，curl 一直等 | router 加 `--connect-timeout 2`，并且 settings.json 里 PermissionRequest 只留 router 一条 |
| inject-wiki-context.sh 在所有 session 都注 1.4K tok | 没做 cwd 门控 | 加 cwd 检查，仅 `~/.clawd*` 时注入 |

---

## 6. 验证清单（迁移完成后过一遍）

```bash
# 1. 别名工作
clawd      # 应该 cd 到 ~/.clawd 并启动 claude
inbox      # 应该写一条到 ~/.clawd/inbox.md

# 2. 全局快捷键工作
# 任意 app 复制文字 → ⌃⌥C → 看到通知 + inbox.md 更新

# 3. Session 路由工作
~/.claude/hooks/mark-session-project.sh ~/.clawd "迁移测试"
# 当前 session 退出后，jsonl 应该被搬到 ~/.claude/projects/-Users-USERNAME--clawd/

# 4. Hook 注入工作
cd ~/.clawd && claude   # SessionStart 应该注入 wiki index
cd ~ && claude          # 不应该注入（cwd 门控）

# 5. cron 工作
crontab -l | grep reorganize-index   # 应该看到 9:07 AM 那行
```

---

## 7. 不在这份文档里的东西

- **Claude-to-IM bridge**：手机渠道（飞书/微信），在 `~/.claude-to-im/`，独立项目，按它自己的 README 装。
