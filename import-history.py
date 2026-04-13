#!/usr/bin/env python3
"""
扫描并提取历史 Claude Code session，为 wiki 归档做准备。
Phase 1（本脚本）: 扫描 → 统计 → 提取到 raw/sessions/
Phase 2（由 Claude session 执行）: 分类 → 写 wiki → 生成关系图

用法:
  python3 import-history.py --scan          # 只扫描，不提取
  python3 import-history.py --extract       # 扫描 + 提取未处理的 session
  python3 import-history.py --extract --all # 重新提取所有 session（含已提取的）
"""

import json, sys, os, re
from pathlib import Path
from datetime import datetime

CLAUDE_DIR = Path.home() / ".claude"
CLAWD_DIR = Path(os.environ.get("CLAWD_DIR", Path.home() / ".clawd"))
RAW_SESSIONS = CLAWD_DIR / "raw" / "sessions"


def scan_sessions():
    """扫描 ~/.claude/projects/ 下所有 JSONL session 文件。"""
    sessions = []
    projects_dir = CLAUDE_DIR / "projects"
    if not projects_dir.exists():
        return sessions

    for jsonl in sorted(projects_dir.rglob("*.jsonl")):
        try:
            stat = jsonl.stat()
        except OSError:
            continue

        size_kb = stat.st_size / 1024
        if size_kb < 1:  # 跳过空文件
            continue

        msg_count = 0
        user_count = 0
        first_user_msg = ""

        with open(jsonl, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg_type = entry.get("type")
                if msg_type == "user":
                    msg_count += 1
                    user_count += 1
                    if not first_user_msg:
                        content = entry.get("message", {}).get("content", "")
                        if isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    first_user_msg = block.get("text", "")[:100]
                                    break
                        elif isinstance(content, str):
                            first_user_msg = content[:100]
                elif msg_type == "assistant":
                    msg_count += 1

        if msg_count == 0:
            continue

        session_id = jsonl.stem
        already_extracted = any(RAW_SESSIONS.glob(f"*_{session_id[:8]}_*"))

        # 从路径推断项目
        rel = jsonl.relative_to(projects_dir)
        project_dir = str(rel.parent).replace("-", "/").lstrip("/")

        sessions.append({
            "path": str(jsonl),
            "session_id": session_id,
            "project_dir": project_dir,
            "size_kb": round(size_kb, 1),
            "msg_count": msg_count,
            "user_count": user_count,
            "first_msg": first_user_msg.replace("\n", " ").strip(),
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "extracted": already_extracted,
        })

    return sorted(sessions, key=lambda s: s["created"])


def print_report(sessions):
    """打印扫描报告。"""
    new = [s for s in sessions if not s["extracted"]]
    old = [s for s in sessions if s["extracted"]]
    total_size = sum(s["size_kb"] for s in sessions)
    new_size = sum(s["size_kb"] for s in new)

    print(f"📊 扫描结果:")
    print(f"  总 session 数: {len(sessions)}")
    print(f"  已提取: {len(old)}")
    print(f"  待提取: {len(new)}")
    print(f"  总大小: {total_size:.0f} KB")
    print(f"  待提取大小: {new_size:.0f} KB")
    print()

    if sessions:
        print(f"  时间跨度: {sessions[0]['created'].strftime('%Y-%m-%d')} → {sessions[-1]['modified'].strftime('%Y-%m-%d')}")
        print()

    # 按项目分组统计
    by_project = {}
    for s in sessions:
        p = s["project_dir"] or "(unknown)"
        by_project.setdefault(p, []).append(s)

    print(f"📁 按项目分布:")
    for proj, ss in sorted(by_project.items(), key=lambda x: -len(x[1])):
        new_count = sum(1 for s in ss if not s["extracted"])
        print(f"  {proj}: {len(ss)} sessions ({new_count} new)")
    print()

    # Token 估算
    # JSONL 大约 4 字符/token，提取后压缩到 ~20%，分类每个 session ~500 tok
    extract_input_tokens = int(new_size * 1024 / 4 * 0.2)  # 提取后的摘要
    classify_tokens = len(new) * 500  # 每个 session 分类消耗
    total_tokens = extract_input_tokens + classify_tokens

    print(f"💰 Phase 2（LLM 分类归档）预估消耗:")
    print(f"  输入 token: ~{extract_input_tokens:,}")
    print(f"  分类 token: ~{classify_tokens:,}")
    print(f"  总计: ~{total_tokens:,} tokens")
    if total_tokens > 100000:
        print(f"  ⚠️  token 较多，建议分批处理（可以先导入最近 30 天的）")
    print()

    # 最近 5 个 session 预览
    print(f"🔍 最近 5 个待提取 session:")
    for s in new[-5:]:
        date = s["created"].strftime("%m-%d")
        msg = s["first_msg"][:50] or "(empty)"
        tag = "✓" if s["extracted"] else "◯"
        print(f"  {tag} [{date}] {s['user_count']}轮 {s['size_kb']:.0f}KB | {msg}")
    print()


def extract_session(jsonl_path: Path, session_id: str) -> Path | None:
    """提取单个 session 到 raw/sessions/，返回输出路径。"""
    RAW_SESSIONS.mkdir(parents=True, exist_ok=True)

    messages = []
    with open(jsonl_path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            msg_type = entry.get("type")
            if msg_type == "user":
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            parts.append(block)
                    content = "\n".join(parts)
                if content.strip():
                    messages.append(("user", content.strip()))
            elif msg_type == "assistant":
                content = entry.get("message", {}).get("content", "")
                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            parts.append(block.get("text", ""))
                        elif isinstance(block, str):
                            parts.append(block)
                    content = "\n".join(parts)
                if content.strip():
                    messages.append(("assistant", content.strip()))
            elif msg_type == "summary":
                text = entry.get("summary", "")
                if text:
                    messages.append(("summary", text.strip()))

    if not messages:
        return None

    # 猜标题
    title = "untitled"
    for role, content in messages[:3]:
        if role == "user":
            title = re.sub(r'[/\\:*?"<>|\n\r]', '_', content[:50]).strip('_. ')
            if title:
                break

    stat = Path(jsonl_path).stat()
    date_str = datetime.fromtimestamp(stat.st_ctime).strftime("%Y%m%d")
    filename = f"{date_str}_{session_id[:8]}_{title}.md"
    output = RAW_SESSIONS / filename

    # 写 markdown
    created = datetime.fromtimestamp(stat.st_ctime).strftime("%Y-%m-%d %H:%M")
    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

    lines = [
        f"---",
        f"session_id: {session_id}",
        f"created: {created}",
        f"modified: {modified}",
        f"source: {jsonl_path}",
        f"messages: {len(messages)}",
        f"---",
        f"",
    ]
    for role, content in messages:
        if role == "user":
            lines.append(f"## User\n\n{content}\n")
        elif role == "assistant":
            # 截断过长的 assistant 回复
            if len(content) > 2000:
                content = content[:2000] + "\n\n[...truncated...]"
            lines.append(f"## Assistant\n\n{content}\n")
        elif role == "summary":
            lines.append(f"## [Context Summary]\n\n{content[:500]}\n")

    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def snapshot_wiki():
    """备份当前 wiki 状态，用于导入后回退。"""
    import tarfile
    from datetime import datetime

    backup_dir = CLAWD_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    tar_path = backup_dir / f"pre-import-{timestamp}.tar.gz"

    dirs_to_backup = []
    for d in ["work/wiki", "life/wiki", "shared-wiki"]:
        p = CLAWD_DIR / d
        if p.exists():
            dirs_to_backup.append((p, d))

    if not dirs_to_backup:
        print("  没有 wiki 内容需要备份")
        return None

    with tarfile.open(tar_path, "w:gz") as tar:
        for full_path, arc_name in dirs_to_backup:
            tar.add(full_path, arcname=arc_name)

    # 生成 rollback 脚本
    rollback_path = CLAWD_DIR / "rollback-import.sh"
    rollback_content = f"""#!/bin/bash
# 回退导入操作 — 恢复 {timestamp} 时的 wiki 状态
# 自动生成，运行后可删除

set -e
CLAWD_DIR="${{CLAWD_DIR:-$HOME/.clawd}}"
BACKUP="{tar_path}"

if [[ ! -f "$BACKUP" ]]; then
    echo "ERROR: 备份文件不存在: $BACKUP"
    exit 1
fi

echo "即将恢复 wiki 到导入前的状态（{timestamp}）"
echo "这会覆盖当前 wiki 内容（work/wiki, life/wiki, shared-wiki）"
echo ""
read -p "确认回退？(y/N) " confirm
[[ "$confirm" == [yY] ]] || {{ echo "已取消"; exit 0; }}

# 恢复
echo "恢复中..."
for d in work/wiki life/wiki shared-wiki; do
    [[ -d "$CLAWD_DIR/$d" ]] && rm -rf "$CLAWD_DIR/$d"
done

tar -xzf "$BACKUP" -C "$CLAWD_DIR"

# 清理 raw/sessions 中导入生成的文件（保留备份之前就有的）
BACKUP_TIME=$(stat -f %m "$BACKUP" 2>/dev/null || stat -c %Y "$BACKUP" 2>/dev/null)
if [[ -d "$CLAWD_DIR/raw/sessions" ]]; then
    find "$CLAWD_DIR/raw/sessions" -name "*.md" -newer "$BACKUP" -delete 2>/dev/null
    echo "  已清理导入后新增的 raw/sessions 文件"
fi

echo ""
echo "✓ wiki 已恢复到 {timestamp} 的状态"
echo "  备份文件保留在: $BACKUP"
echo "  rollback 脚本可以删了: rm $CLAWD_DIR/rollback-import.sh"
"""
    rollback_path.write_text(rollback_content, encoding="utf-8")
    os.chmod(rollback_path, 0o755)

    size_kb = tar_path.stat().st_size / 1024
    print(f"  ✓ 快照已保存: {tar_path} ({size_kb:.0f} KB)")
    print(f"  ✓ 回退脚本: {rollback_path}")
    return tar_path


def main():
    scan_only = "--scan" in sys.argv
    extract_all = "--all" in sys.argv
    snapshot_only = "--snapshot" in sys.argv

    if snapshot_only:
        print("=== 备份当前 wiki 状态 ===\n")
        result = snapshot_wiki()
        if result:
            print(f"\n备份完成。回退命令: bash {CLAWD_DIR}/rollback-import.sh")
        sys.exit(0)

    print("=== intern-clawd 历史 Session 导入 ===\n")

    sessions = scan_sessions()
    if not sessions:
        print("未找到任何历史 session。")
        print(f"  扫描路径: {CLAUDE_DIR / 'projects'}")
        sys.exit(0)

    print_report(sessions)

    if scan_only:
        # 输出 JSON manifest 供 Claude 读取
        manifest = CLAWD_DIR / "raw" / "import-manifest.json"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        data = []
        for s in sessions:
            data.append({
                "session_id": s["session_id"],
                "project_dir": s["project_dir"],
                "size_kb": s["size_kb"],
                "msg_count": s["msg_count"],
                "first_msg": s["first_msg"],
                "created": s["created"].isoformat(),
                "extracted": s["extracted"],
            })
        manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"📋 Manifest 已写入: {manifest}")
        sys.exit(0)

    # 提取
    to_extract = sessions if extract_all else [s for s in sessions if not s["extracted"]]
    if not to_extract:
        print("所有 session 已提取，无需操作。")
        print(f"  如需重新提取: python3 import-history.py --extract --all")
        sys.exit(0)

    print(f"开始提取 {len(to_extract)} 个 session...\n")

    success = 0
    for i, s in enumerate(to_extract, 1):
        try:
            out = extract_session(Path(s["path"]), s["session_id"])
            if out:
                print(f"  [{i}/{len(to_extract)}] ✓ {out.name}")
                success += 1
            else:
                print(f"  [{i}/{len(to_extract)}] - 跳过（无消息）")
        except Exception as e:
            print(f"  [{i}/{len(to_extract)}] ✗ {s['session_id'][:8]}: {e}")

    print(f"\n提取完成: {success}/{len(to_extract)} 成功")
    print(f"输出目录: {RAW_SESSIONS}")

    # 写 manifest
    manifest = CLAWD_DIR / "raw" / "import-manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    all_sessions = scan_sessions()  # 重新扫描，更新 extracted 状态
    data = []
    for s in all_sessions:
        data.append({
            "session_id": s["session_id"],
            "project_dir": s["project_dir"],
            "size_kb": s["size_kb"],
            "msg_count": s["msg_count"],
            "first_msg": s["first_msg"],
            "created": s["created"].isoformat(),
            "extracted": s["extracted"],
        })
    manifest.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"📋 Manifest: {manifest}")
    print(f"\n下一步: 在秘书 session 里说「导入历史」，让 Claude 分类归档。")


if __name__ == "__main__":
    main()
