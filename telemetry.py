"""Operation telemetry: append-only JSONL log tracking key metrics for each wiki operation."""

import json
import time
from datetime import datetime
from pathlib import Path

CLAWD_DIR = Path.home() / ".clawd"
TELEMETRY_FILE = CLAWD_DIR / "telemetry.jsonl"


def log_op(op, domain="unknown", pages_touched=0, status="ok", detail="", source="unknown"):
    """Log one operation to telemetry.jsonl"""
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
        pass


def summary(days=30):
    """Operation summary for the last N days."""
    if not TELEMETRY_FILE.exists():
        return "(no telemetry data)"

    cutoff = time.time() - days * 86400
    ops = {}
    errors = 0
    total = 0

    for line in TELEMETRY_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line:
            continue
        try:
            entry = json.loads(line)
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
        return "(no telemetry data)"

    lines = [f"Last {days} days: {total} operations, {errors} errors"]
    for op, count in sorted(ops.items(), key=lambda x: -x[1]):
        lines.append(f"  {op}: {count}")
    return "\n".join(lines)
