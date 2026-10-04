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
# $ per MTok of input, and cache reads as a multiple of input, from the pricing page on 2026-10-03:
# Opus 5.5 cache hits are 0.05x, Fable/Mythos 5.1 0.025x, everything else 0.1x. Writes and output keep
# the 1.25x/2x/5x multiples on every model. First matching prefix wins.
PRICES = [("claude-opus-5-5", 4.0, 0.05), ("claude-fable-5-1", 10.0, 0.025), ("claude-mythos-5-1", 10.0, 0.025),
          ("claude-fable-5", 10.0, 0.1), ("claude-mythos-5", 10.0, 0.1), ("claude-opus-4-1", 15.0, 0.1),
          ("claude-opus-4-0", 15.0, 0.1), ("claude-opus", 5.0, 0.1), ("claude-sonnet-5", 2.0, 0.1),
          ("claude-sonnet", 3.0, 0.1), ("claude-haiku-4", 1.0, 0.1), ("claude-haiku", 0.8, 0.1)]


def price(u: dict) -> tuple[float, float]:
    """(input $/MTok, cache-read multiple) for the model that served this request; unknown models count as Opus 5.5."""
    model = u.get("model") or ""
    return next(((p, rd) for prefix, p, rd in PRICES if model.startswith(prefix)), (4.0, 0.05))


def request_cost(u: dict, write_mult: float | None = None) -> float:
    """$ per million of this request's tokens; 1h writes at 2x unless write_mult overrides every write."""
    p, rd = price(u)
    hour = (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) or 0
    write = u.get("cache_creation_input_tokens", 0) or 0
    writes = write * write_mult if write_mult else (write - hour) * 1.25 + hour * 2.0
    return p * ((u.get("input_tokens", 0) or 0) + writes + (u.get("cache_read_input_tokens", 0) or 0) * rd
                + (u.get("output_tokens", 0) or 0) * 5.0)


def read_rate(u: dict) -> float:
    p, rd = price(u)
    return p * rd
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
    usage, order, times, uses, events, visible = {}, [], {}, {}, [], Counter()
    for line in path.open(errors="ignore"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("isCompactSummary"):
            events.append(("compact", len(order)))
        a = r.get("attachment") or {}
        if a.get("type") == "skill_listing":
            events.append(("skills", len(order), len(a.get("content") or "") / CHARS_PER_TOKEN))
        m = r.get("message") or {}
        if r.get("type") == "assistant":
            mid = m.get("id") or r.get("uuid")
            if mid not in usage:
                order.append(mid)
                times[mid] = ts(r)
            usage[mid] = {**(m.get("usage") or {}), "model": m.get("model") or ""}
            for b in m.get("content") or []:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    uses[b.get("id")] = (b.get("name", "?"), b.get("input") or {})
                    if b.get("name") == "Skill":
                        events.append(("invoked", len(order), (b.get("input") or {}).get("skill")))
                    visible[mid] += len(json.dumps(b.get("input")))
                elif isinstance(b, dict) and b.get("type") == "text":
                    visible[mid] += len(b.get("text", ""))
        elif r.get("type") == "user" and isinstance(m.get("content"), list):
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    name, inp = uses.get(b.get("tool_use_id"), ("?", {}))
                    events.append(("result", len(order), name, inp, size_of(b.get("content"))))
    if not order:
        return None
    # transcripts store thinking with an empty body, so hidden output = billed output - visible text/tool input
    return {"usage": [usage[m] for m in order], "times": [times[m] for m in order], "events": events,
            "visible": [visible[m] / CHARS_PER_TOKEN for m in order],
            "subagent": "subagents" in path.parts or path.stem.startswith("agent-")}


def context_of(u: dict) -> int:
    return sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


def composition(sessions: list[dict]) -> Counter:
    """Split cache-read volume by where the tokens came from, using each request's usage delta.

    Prior thinking stays in context on Opus 5.x (Claude Code sends clear_thinking with keep "all"), so
    an assistant turn's billed output is resident on every later request until the next compaction.
    """
    parts = Counter()
    for s in sessions:
        u, n = s["usage"], len(s["usage"])
        compacts = sorted(i for kind, i, *_ in s["events"] if kind == "compact")
        for i in range(n):
            later = next((c for c in compacts if c > i), n) - i - 1
            out = u[i].get("output_tokens", 0) or 0
            vis = min(out, s["visible"][i])
            parts["assistant text and tool calls"] += vis * later
            parts["thinking"] += (out - vis) * later
            if i == 0 or i in compacts:
                parts["prefix (system, tools, summary)"] += context_of(u[i]) * later
            else:
                grew = context_of(u[i]) - context_of(u[i - 1]) - (u[i - 1].get("output_tokens", 0) or 0)
                parts["tool results, prompts, injections"] += max(0, grew) * later
    return parts


def analyze(sessions: list[dict]) -> dict:
    total = 0.0
    by_tool = Counter()
    reread = Counter()  # "dup" = same file, unchanged since; "all" = every Read
    reread_calls = Counter()
    busts = Counter()
    bust_cost = Counter()
    for s in sessions:
        n = len(s["usage"])
        total += sum(request_cost(u) for u in s["usage"])
        # residency ends at the next compaction, or at session end
        compacts = sorted(i for kind, i, *_ in s["events"] if kind == "compact")
        seen: dict[str, set] = defaultdict(set)  # path -> (offset, limit) ranges shown since the last write
        for ev in s["events"]:
            if ev[0] != "result":
                continue
            _, at, name, inp, size = ev
            end = next((c for c in compacts if c > at), n)
            cost = size / CHARS_PER_TOKEN * max(0, end - at) * read_rate(s["usage"][min(at, n - 1)])
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
                bust_cost[kind] += cw * (1.25 * price(u)[0] - read_rate(u))
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
    parts = composition(sessions)
    print("\nWhat cache reads are made of")
    for name, c in parts.most_common():
        print(f"  {name:34} {c / sum(parts.values()):6.1%}")
    print("\nCache rewrites mid-session (write >20k while read <50% of prior context)")
    for kind in ("idle>5m", "idle>1h", "other"):
        print(f"  {kind:8} {r['busts'][kind]:5}  extra cost {r['bust_cost'][kind] / t:6.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
