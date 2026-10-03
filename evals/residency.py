#!/usr/bin/env python3
"""Replay real transcripts to price what sits in context: tool results by tool,
duplicate Reads, and mid-session cache rewrites. Read-only.

    python3 evals/residency.py [--days N]

Residency of a tool result = its tokens x the requests that follow it in the
same session (it is re-read from cache on each), priced at cache-read weight
0.1. Compaction drops it early, so this is an upper bound on long sessions.
"""
from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
WEIGHTS = {"input_tokens": 1.0, "cache_creation_input_tokens": 1.25, "cache_read_input_tokens": 0.1, "output_tokens": 5.0}
CHARS_PER_TOKEN = 3.6
WRITERS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def ts(record: dict) -> float:
    try:
        return datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00")).timestamp()
    except (KeyError, ValueError):
        return 0.0


def size_of(content) -> int:
    if isinstance(content, str):
        return len(content)
    return sum(len(c.get("text", "")) for c in content or [] if isinstance(c, dict))


def load(path: Path) -> dict | None:
    usage, order, times, uses, events = {}, [], {}, {}, []
    for line in path.open(errors="ignore"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("isCompactSummary"):
            events.append(("compact", len(order)))
        m = r.get("message") or {}
        if r.get("type") == "assistant":
            mid = m.get("id") or r.get("uuid")
            if mid not in usage:
                order.append(mid)
                times[mid] = ts(r)
            usage[mid] = m.get("usage") or {}
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    uses[b.get("id")] = (b.get("name", "?"), b.get("input") or {})
        elif r.get("type") == "user" and isinstance(m.get("content"), list):
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    name, inp = uses.get(b.get("tool_use_id"), ("?", {}))
                    events.append(("result", len(order), name, inp, size_of(b.get("content"))))
    if not order:
        return None
    return {"usage": [usage[m] for m in order], "times": [times[m] for m in order], "events": events,
            "subagent": "subagents" in path.parts or path.stem.startswith("agent-")}


def context_of(u: dict) -> int:
    return sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


def analyze(sessions: list[dict]) -> dict:
    total = 0.0
    by_tool = Counter()
    reread = Counter()  # "dup" = same file, unchanged since; "all" = every Read
    reread_calls = Counter()
    busts = Counter()
    bust_cost = Counter()
    for s in sessions:
        n = len(s["usage"])
        total += sum(u.get(k, 0) * w for u in s["usage"] for k, w in WEIGHTS.items())
        # residency ends at the next compaction, or at session end
        compacts = sorted(i for kind, i, *_ in s["events"] if kind == "compact")
        seen: dict[str, set] = defaultdict(set)  # path -> (offset, limit) ranges shown since the last write
        for ev in s["events"]:
            if ev[0] != "result":
                continue
            _, at, name, inp, size = ev
            end = next((c for c in compacts if c > at), n)
            cost = size / CHARS_PER_TOKEN * max(0, end - at) * 0.1
            tool = name.split("__")[1] if name.startswith("mcp__") else name
            by_tool[tool] += cost
            path = inp.get("file_path") if isinstance(inp, dict) else None
            if name in WRITERS and path:
                seen.pop(path, None)
            if name == "Read" and path:
                reread_calls["all"] += 1
                reread["all"] += cost
                rng = (inp.get("offset"), inp.get("limit"))
                if rng in seen[path]:
                    reread_calls["dup"] += 1
                    reread["dup"] += cost
                seen[path].add(rng)
        for i in range(1, n):
            prev, u = context_of(s["usage"][i - 1]), s["usage"][i]
            cw, cr = u.get("cache_creation_input_tokens", 0) or 0, u.get("cache_read_input_tokens", 0) or 0
            if cw > 20_000 and cr < 0.5 * prev:
                gap = s["times"][i] - s["times"][i - 1]
                kind = "idle>1h" if gap > 3600 else "idle>5m" if gap > 300 else "other"
                busts[kind] += 1
                # extra cost vs reading the same tokens from cache
                bust_cost[kind] += cw * (1.25 - 0.1)
    return {"total": total, "by_tool": by_tool, "reread": reread, "reread_calls": reread_calls,
            "busts": busts, "bust_cost": bust_cost}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=14)
    args = ap.parse_args()
    cutoff = time.time() - args.days * 86400
    sessions = [s for p in PROJECTS.rglob("*.jsonl") if p.stat().st_mtime >= cutoff and (s := load(p))]
    r = analyze(sessions)
    t = r["total"]
    print(f"{len(sessions)} sessions, last {args.days}d, weighted total {t / 1e6:.1f}M\n")
    print("Tool-result residency (share of weighted bill)")
    for name, c in r["by_tool"].most_common(10):
        print(f"  {name:14} {c / t:6.1%}")
    print(f"  {'all tools':14} {sum(r['by_tool'].values()) / t:6.1%}")
    rc = r["reread_calls"]
    print(f"\nRead: {rc['all']} calls, {rc['dup']} repeat an unchanged file+range "
          f"({rc['dup'] / max(1, rc['all']):.0%}); repeats are {r['reread']['dup'] / t:.1%} of the bill")
    print("\nCache rewrites mid-session (write >20k while read <50% of prior context)")
    for kind in ("idle>5m", "idle>1h", "other"):
        print(f"  {kind:8} {r['busts'][kind]:5}  extra cost {r['bust_cost'][kind] / t:6.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
