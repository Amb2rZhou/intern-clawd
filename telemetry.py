"""操作遥测：append-only JSONL 日志，记录每次 wiki 操作的关键指标。"""

import json
import time
from datetime import datetime
from pathlib import Path

CLAWD_DIR = Path.home() / ".clawd"
TELEMETRY_FILE = CLAWD_DIR / "telemetry.jsonl"


def log_op(op, domain="unknown", pages_touched=0, status="ok", detail="", source="unknown"):
    """记录一次操作到 telemetry.jsonl

    Args:
        op: 操作类型 (ingest/query/lint/maintenance/collect/process)
        domain: work/life/shared/both
        pages_touched: 影响的页面数
        status: ok/error/timeout
        detail: 补充信息
        source: 来源渠道 (terminal/feishu/wechat/cron/shortcut)
    """
    entry = {
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "op": op,
        "domain": domain,
        "pages": pages_touched,
        "status": status,
        "source": source,
    }
    if detail:
        entry["detail"] = detail[:200]

    try:
        with open(TELEMETRY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # telemetry 不应该阻断主流程


def summary(days=30):
    """最近 N 天的操作统计摘要"""
    if not TELEMETRY_FILE.exists():
        return "（无遥测数据）"

    cutoff = time.time() - days * 86400
    ops = {}
    errors = 0
    total = 0

    for line in TELEMETRY_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            entry = json.loads(line)
            # 粗略时间过滤
            ts = entry.get("ts", "")
            if ts < datetime.fromtimestamp(cutoff).strftime("%Y-%m-%dT%H:%M:%S"):
                continue
            total += 1
            op = entry.get("op", "unknown")
            ops[op] = ops.get(op, 0) + 1
            if entry.get("status") != "ok":
                errors += 1
        except (json.JSONDecodeError, ValueError):
            continue

    if total == 0:
        return "（无遥测数据）"

    lines = [f"最近 {days} 天：{total} 次操作，{errors} 次异常"]
    for op, count in sorted(ops.items(), key=lambda x: -x[1]):
        lines.append(f"  {op}: {count}")
    return "\n".join(lines)
