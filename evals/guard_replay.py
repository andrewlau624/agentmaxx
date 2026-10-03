#!/usr/bin/env python3
"""Replay real tool calls through hooks/guard.py and report what it would deny. Read-only.

    python3 evals/guard_replay.py [--days 30] [--show REASON_SUBSTRING]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
import guard  # noqa: E402

TOOLS = {"Bash", "Read", "Write", "Edit", "MultiEdit"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--show", help="print the calls denied with this reason")
    args = ap.parse_args()
    cutoff = time.time() - args.days * 86400
    calls, seen, reasons, shown = 0, set(), Counter(), []
    for path in (Path.home() / ".claude" / "projects").rglob("*.jsonl"):
        if path.stat().st_mtime < cutoff:
            continue
        for line in path.open(errors="ignore"):
            if '"tool_use"' not in line:
                continue
            try:
                content = (json.loads(line).get("message") or {}).get("content") or []
            except json.JSONDecodeError:
                continue
            for block in content:
                if not isinstance(block, dict) or block.get("type") != "tool_use" or block.get("name") not in TOOLS:
                    continue
                if block.get("id") in seen:
                    continue
                seen.add(block.get("id"))
                calls += 1
                reason = guard.check(block["name"], block.get("input") or {})
                if reason:
                    reasons[reason] += 1
                    if args.show and args.show in reason:
                        shown.append(json.dumps(block.get("input"))[:200])
    denied = sum(reasons.values())
    print(f"{calls:,} calls over {args.days}d, {denied} denied ({denied / max(calls, 1):.2%})")
    for reason, n in reasons.most_common():
        print(f"  {n:5}  {reason[:90]}")
    for s in shown[:40]:
        print("   ", s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
