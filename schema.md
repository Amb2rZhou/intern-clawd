# Global Schema — Intern Agent System

本文件定义所有 agent 维护 wiki 的规则和流程。每个域 agent 启动时必须读取本文件 + 自己域的 schema.md。

## 架构概览

```
秘书 Agent（���由 + 管理）
  ├── work/      工作域
  ├── life/      生活域
  └── side-projects/{name}/  按需扩展
共享层: shared-wiki/（跨域知识，秘书维护）
```

## 三层架构（Karpathy LLM Wiki 模式）

```
raw/                ← 不可变事实源（agent 只读）
  ├── articles/     ← 文章原文
  ├── transcripts/  ← 录音转写
  ├── screenshots/  ← 截图
  └── clippings/    ← 网页剪藏
wiki/               ← LLM 维护层（agent 读写）
schema + CLAUDE.md  ← 约束层（人 + agent 共同维护）
```

**关键规则：agent 对 raw/ 目录只有 Read 权限，绝不 Edit/Write/Delete。**

## Wiki 维护规则

### 页面格式

每个 wiki 页面使用 YAML frontmatter：

```markdown
---
title: 页面标题
created: 2026-04-05
updated: 2026-04-05
tags: [tag1, tag2]
sources: [raw/filename.md]
linked_from: [other-page.md]
---

页面正文，使用 [[wiki-link]] 语法交叉引用。
```

### index.md 格式

每个域的 wiki/ 下维护一个 index.md，按类别组织：

```markdown
# Index

## Projects
- [project-name](projects/project-name.md) — 一行摘要

## People
- [person-name](people/person-name.md) — 一行摘要

## Decisions
- [decision-title](decisions/decision-title.md) — 一行摘要
```

规则：
- 每次 ingest/更新后必须同步更新 index.md
- 每行不超过 120 字符
- 按字母或重要性排序，保持一致

### log.md 格式

**Reverse-chronological 时间线（最新条目插在文件顶部）**，格式统一：

```markdown
## [YYYY-MM-DD HH:MM] {operation} | {title}

{1-3 行摘要，说明做了什么、影响了哪些页面}
```

> **顺序约定**：新条目插在 `# {Domain} Log` 标题下方、上一条之前。
> 原因：`inject-wiki-context.sh` 只读 log.md 前 50 行作为 session 上下文，新条目在顶部才能被看到。
> 严禁追加到文件末尾（会让最近活动对秘书 prompt 不可见）。

operation 类型：
- `ingest` — 摄入新素材
- `task-complete` — 完成任务
- `task-assign` — 布置任务
- `coaching` — 思维对话
- `lint` — 健康检查
- `update` — 页面更新（非 ingest 触发的）
- `query` — 重要查询及结论

## 三大操作流程

### 1. Ingest（摄入）

触发：用户丢素材进 raw/ 或直接发内容给 agent

流程：
1. 读取素材，提取关键实体、概念、事实
2. 检查 index.md，找到相关已有页面
3. 更新已有页面（新信息、交叉引用、矛盾标注）
4. 如有新实体/概念，创建新页面
5. 更新 index.md
6. 追加 log.md 条目
7. 如涉及跨域知识，同步到 shared-wiki/（或标记待同步）

矛盾处理：发现新旧信息矛盾时，不要静默覆盖。在页面中用以下格式标注：

```markdown
> [!conflict] 与 [[other-page]] 的记录存在矛盾
> 旧：xxx（来源：raw/old-source.md, 2026-03-01）
> 新：yyy（来源：raw/new-source.md, 2026-04-05）
> 待确认：请 boss 判断哪个为准
```

### 2. Query（查询）

触发：用户提问

流程：
1. 读取 index.md 定位相关页面
2. 读取相关页面
3. 综合回答，附引用 `[[page-name]]`
4. 如果回答产出了有价值的新综合/分析，考虑写回 wiki 作为新页面
5. 重要查询记录到 log.md

### 3. Lint（健康检查）

触发：定时（建议每周一次）或手动

检查项：
- [ ] 过时页面：有更新的信息但页面未更新
- [ ] 孤立页面：无 inbound links
- [ ] 空页面 / stub 页面
- [ ] index.md 与实际文件是否一致
- [ ] 矛盾标注是否已解决
- [ ] 交叉引用是否有效（无死链）

输出 lint 报告到 log.md。

## 跨域同步规则

以下类型的知识在产生时应同步到 shared-wiki/：
- 编码风格和技术偏好变更
- 个人成长相关的洞察（不论来源于工作还是生活）
- 通用工具/工作流的改进

同步方式：在源域 log.md 标记 `[sync → shared]`，由秘书在跨域任务时负责实际同步。

## Post-Write 自动验证（反馈回路）

每次写入 wiki 页面后，agent 应自检：
1. frontmatter 格式是否完整（title, created, updated, tags, sources, linked_from）
2. 新增的 `[[wiki-link]]` 是否都有对应文件存在
3. index.md 是否已同步更新
4. log.md 是否已追加记录
5. 如有对应 raw source，页面 `sources:` 字段是否指向它

可用 `python3 ~/.clawd/wiki-lint.py --quiet` 快速验证。有问题立即修复，不留到下次维护。

## 可观测性（Telemetry）

每次有意义的操作记录到 `~/.clawd/telemetry.jsonl`：
```python
from telemetry import log_op
log_op("ingest", domain="work", pages_touched=3, source="terminal")
```

字段：ts, op, domain, pages, status, source, detail
op 类型：ingest / query / lint / maintenance / collect / process
source 类型：terminal / im / cron / shortcut

## 跨 Session 状态接力（Progress File）

长任务（需要多轮或多 session 完成）使用 `~/.clawd/progress.md`：

```markdown
## 当前任务
{任务描述}

## 已完成
- [x] 步骤 1
- [x] 步骤 2

## 进行中
- [ ] 步骤 3（卡在 xxx）

## 下一步
- [ ] 步骤 4

## 上下文
{后续 session 需要知道的关键信息}
```

规则：
- 每个 session 结束前如果有未完成的长任务，更新 progress.md
- 新 session 开始时如果 progress.md 非空，先读取接续
- 任务全部完成后清空 progress.md

## Pattern Drift 检测（内容与源头一致性）

月度维护时额外检查：
1. 对比 wiki 页面的 `sources:` 字段指向的 raw source / GitHub 仓库，检查描述是否与源头一致
2. 检查 GitHub 仓库有近期 commit 但 wiki 页面 updated 日期明显滞后的情况
3. 发现漂移时在页面中标注 `> [!drift]` 提醒 boss 确认

## Agent 行为准则

- 你是实习生，不是老板。执行任务时精确高效，教练对话时启发而非指示。
- 维护 wiki 是你的核心职责，每次交互结束前检查是否有需要更新的页面。
- 不确定时问，不要猜。
- boss 的判断优先于 wiki 中的历史记录。
- **绝不修改 raw/ 目录下的任何文件。**
- 写完 wiki 后跑一次自检，确保不留结构性问题。
