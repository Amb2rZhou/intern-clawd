# Known Risks & Limitations

intern-clawd 改装 Claude Code 的同时，也会动你机器上的几个全局文件。这份清单**完整列出**所有已知风险，让你装之前心里有数。

> 这不是营销话术，是装之前你应该知道的全部坏消息。

---

## A 类：装上后立刻可能影响你的

### A1. 修改全局 `~/.claude/CLAUDE.md`

`setup.sh` 第 5 步会往 `~/.claude/CLAUDE.md` **追加**一段「Wiki 知识同步」规则。

- ✅ **已治**：追加前先备份到 `~/.claude/CLAUDE.md.before-clawd-{时间戳}`
- ✅ **已治**：规则已软化为「**仅当 ~/.clawd 存在**」，对裸 Claude Code 用户和无关项目零影响
- ✅ **已治**：`uninstall.sh` 能精准移除这一段

### A2. SessionStart hook 给所有 session 加 50-200ms 启动延迟

`hooks/inject-wiki-context.sh` 装了之后，**每个** Claude Code session 启动都会跑一遍这个 hook。

- ✅ **已治**：cwd 检查已前移到 hook 最前面，**非秘书 cwd 用纯 bash 几毫秒退出**，不启动 python3
- 实测：非秘书 session 增加 ~5ms，秘书 session 增加 ~100-200ms（拼上下文需要的开销）

### A3. 硬编码 `/usr/bin/python3`

`inject-wiki-context.sh` 用 `/usr/bin/python3`，不是 `$(which python3)`。

- macOS 没装 Xcode Command Line Tools 的话，`/usr/bin/python3` 不存在
- ✅ **已治**：`setup.sh` 第 1 步现在会主动检测 `/usr/bin/python3`，不存在直接报错并提示装法

### A4. SessionEnd hook (`session-relocate.py`) 用 `shutil.move`

如果你把 `~/.claude` 软链到外置盘 / 网络存储，`shutil.move` 跨文件系统时是 **copy + delete**，中途崩溃理论上可能丢 session JSONL。

- 缓解：脚本有 collision 检测，目标已存在不会覆盖
- 没修：跨 FS 场景不常见，且没有低成本治法。如果你 `~/.claude` 在外置盘，**请不要装 SessionEnd hook**

### A5. `permission-router.sh` 默认无超时（如果你装它）

如果你 opt-in 装了 PermissionRequest hook 但上游 Mr. Krabs 服务没起，curl 会卡 600s。

- 没修：`permission-router.sh` 是可选的，setup.sh 默认**不**装它
- 装的话请参考 `setup-new-machine.md` §5 的已知坑表，自行加 `--connect-timeout 2`

---

## B 类：长期使用会累积的

### B1. `inbox.md` / `log.md` 无 rotation

`collect.sh` 一直 append 到 `inbox.md`，wiki sync 也一直追加 `log.md`。半年后单文件可能涨到几 MB。

- 后果：SessionStart 注入的 token 涨（hook 读 log.md 前 50 行）
- 没修：手动 archive 旧条目即可，月度 `wiki-maintenance.py` 应该 cover 但当前实现不保证

### B2. `raw/` 只读约束**只在 schema.md 写**，不是 OS 层强制

agent 看了 `schema.md` 后**应该**只 Read raw/，但没有 chmod 444 之类的硬约束。模型听不进去 / 被 prompt injection 时可能写坏。

- 缓解：`raw/` 整个目录可以自己加 `chmod -R a-w` 强制只读
- 没修：默认设置不强制，给重度用户留灵活性

### B3. 跟 Claude Code 内部 schema 强耦合

依赖：
- `SessionStart` / `SessionEnd` hook 字段名
- JSONL 里的 `customTitle` 格式
- `~/.claude/projects/` 目录的 cwd 编码规则（`[^a-zA-Z0-9-]` → `-`）
- `settings.json` 里 hooks 的 schema

Anthropic 哪天改了任何一个，**对应功能就废**。没有版本探测，没有兼容层。

- 当前测试：Claude Code v1.x 系列（2026-04 测试）
- 没修：跟着 CC 走，破了再修

### B4. 装上后每个秘书 session 多 1.4-3K tok prompt overhead

SessionStart hook 注入 wiki index，增加 prompt 输入。
- 用 Claude **订阅**：无感（订阅是包月）
- 用 Claude **API**：**直接增加月账单**

如果你是 API 用户，每天跑 50 次秘书 session × 30 天 × 2K tok ≈ 300 万 tok 输入/月。按当前 Sonnet 输入价 $3/M tok = **额外 $9/月**。

- 缓解：cwd 门控保证只在秘书 cwd 注入；普通 coding 项目零开销
- 没修：这就是这个系统的核心成本

### B5. 数据明文存 `~/.clawd`

整个知识库是 plaintext markdown。

- ⚠️ **如果你把 `~/.clawd` 加进 git 然后 push public**，所有笔记/log 都会上 GitHub
  - 这就是为什么有 intern-clawd 这个**脱敏对外版**——作者本人踩过
- ⚠️ **Time Machine 备份到家庭 NAS** = 整个秘书内存暴露给家庭网络
- 缓解：`.gitignore` 模板已包含 `inbox.md` / `log.md` / 个人 wiki 内容
- 没修：明文是设计选择（grep / git diff / 普通编辑器都能用），加密会破坏这些性质

---

## C 类：粗糙但不致命

| | |
|---|---|
| C1 | `setup.sh` 没有 `--dry-run`，跑了就开始改 |
| C2 | macOS Shortcuts.app 全局快捷键这一段全靠手册（无法自动化，Apple 不开放） |
| C3 | README 说"Linux 已支持"，但 `⌃⌥C` 全局快捷键、Mr. Krabs 桌面 bubble 都是 macOS-only |
| C4 | 没有 "tested against Claude Code version X.Y" 标注 |

---

## 怎么撤掉（一键回退）

```bash
bash uninstall.sh
```

会做的事：
1. 备份所有要改的文件到 `~/.clawd-uninstall-backup/{时间戳}/`
2. 移除全局 `CLAUDE.md` 的 wiki 同步段
3. 清理 `settings.json` 里的 clawd hooks
4. 删 `~/.claude/hooks/` 里的 clawd 脚本
5. 清理 crontab 里的整理任务
6. 清理 `~/.zshrc` 里的 `clawd` / `inbox` alias
7. **询问** 是否删 `~/.clawd` 知识库（默认 N，需要输入 `delete my notes` 确认）
8. 生成 `restore.sh`，反悔可以一键还原

不会自动碰：
- macOS Shortcuts.app 里的 ⌃⌥C 快捷指令（Apple API 不开放，自己删）
- `~/.claude-to-im/`（独立项目，按它自己 README 卸）
- Mr. Krabs.app（独立 app，从 Applications 拖走）

反悔了：

```bash
bash ~/.clawd-uninstall-backup/{时间戳}/restore.sh
```

一键还原所有改动。

---

## 装之前自检清单

- [ ] 我装的是 macOS（Linux 也能装但部分入口不可用）
- [ ] `xcode-select --install` 已跑过 / `/usr/bin/python3` 存在
- [ ] 我的 `~/.claude/CLAUDE.md` 没有不能被备份/追加的敏感内容
- [ ] 我的 `~/.claude` 不在外置盘 / 网络存储（避开 A4）
- [ ] 我用的是 Claude **订阅**，或者已经接受 API 用户每月可能多花几刀（B4）
- [ ] 我清楚 `~/.clawd` 是明文，不会不小心 git push 到 public（B5）
- [ ] 我知道这套东西跟 Claude Code 强耦合，Anthropic 改 API 可能就废（B3）

---

如果你看完这份清单还是想装：欢迎。如果有疑虑：先看 README 的「设计原则」section 想清楚再装，或者直接 fork 改成你想要的样子。
