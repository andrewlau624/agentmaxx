#!/usr/bin/env python3
"""agentmaxx doctor: find where this machine's Claude Code tokens go, and what to change.

Reads ~/.claude/projects transcripts (deduped per API response) and
~/.claude/settings.json. Read-only.

    python3 evals/doctor.py [--days N]
"""
from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
SETTINGS = Path.home() / ".claude" / "settings.json"
# Weighted index: input 1, cache write 1.25, cache read 0.1, output 5.
WEIGHTS = {"input": 1.0, "write": 1.25, "read": 0.1, "output": 5.0}
COMPACT_BUFFER = 33_000


def load_sessions(days: int) -> list[dict]:
    cutoff = time.time() - days * 86400
    sessions = []
    for path in PROJECTS.rglob("*.jsonl"):
        if path.stat().st_mtime < cutoff:
            continue
        usage, order, uses, results = {}, [], {}, []
        for line in path.open(errors="ignore"):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            message = record.get("message") or {}
            if record.get("type") == "assistant":
                msg_id = message.get("id") or record.get("uuid")
                if msg_id not in usage:
                    order.append(msg_id)
                usage[msg_id] = message.get("usage") or {}
                for block in message.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        uses[block.get("id")] = block.get("name", "?")
            elif record.get("type") == "user" and isinstance(message.get("content"), list):
                for block in message["content"]:
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        content = block.get("content")
                        size = len(content) if isinstance(content, str) else sum(
                            len(c.get("text", "")) for c in content or [] if isinstance(c, dict))
                        results.append((len(order), uses.get(block.get("tool_use_id"), "?"), size))
        if order:
            sessions.append({"usage": [usage[m] for m in order], "results": results,
                             "subagent": "subagents" in path.parts or path.stem.startswith("agent-")})
    return sessions


def context_of(u: dict) -> int:
    return sum(u.get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))


def simulate_window(sessions: list[dict], window: int | None, summary: int = 12_000) -> float:
    total = 0.0
    for s in sessions:
        contexts = [context_of(u) for u in s["usage"]]
        offset, prefix = 0, contexts[0]
        for c in contexts:
            effective = c - offset
            if window and effective > window - COMPACT_BUFFER:
                total += effective * 0.1 + summary * 5 + summary * 1.25
                offset, effective = c - (prefix + summary), prefix + summary
            total += effective * 0.1
    return total


def pct(values: list[int], q: float) -> int:
    values = sorted(values)
    return values[int(q * (len(values) - 1))] if values else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=14)
    args = parser.parse_args()

    sessions = load_sessions(args.days)
    if not sessions:
        print(f"no Claude Code sessions in the last {args.days}d")
        return 0
    settings = json.loads(SETTINGS.read_text()) if SETTINGS.exists() else {}
    env = {**settings.get("env", {}), **{k: v for k, v in os.environ.items() if k.startswith(("ENABLE_", "CLAUDE_", "ANTHROPIC_"))}}

    tokens = Counter()
    for s in sessions:
        for u in s["usage"]:
            tokens["input"] += u.get("input_tokens", 0) or 0
            tokens["write"] += u.get("cache_creation_input_tokens", 0) or 0
            tokens["read"] += u.get("cache_read_input_tokens", 0) or 0
            tokens["output"] += u.get("output_tokens", 0) or 0
    weighted = {k: tokens[k] * w for k, w in WEIGHTS.items()}
    total = sum(weighted.values())
    contexts = [context_of(u) for s in sessions for u in s["usage"]]
    prefixes = [context_of(s["usage"][0]) for s in sessions if not s["subagent"]]
    tool_tokens = Counter()
    for s in sessions:
        for _, name, size in s["results"]:
            tool_tokens[name.split("__")[1] if name.startswith("mcp__") else name] += size / 3.6

    print(f"{len(sessions)} sessions, {len(contexts):,} requests, last {args.days}d\n")
    print("Where the weighted cost goes")
    for k in ("read", "write", "output", "input"):
        print(f"  cache {k:6}" if k in ("read", "write") else f"  {k:12}", f"{weighted[k] / total:6.1%}")
    print(f"\nContext per request: p50 {pct(contexts, .5):,}  p90 {pct(contexts, .9):,}  "
          f"(>200k on {sum(c > 200_000 for c in contexts) / len(contexts):.0%} of requests)")
    print(f"Fixed prefix at session start: p50 {pct(prefixes, .5):,} tokens")
    print("Largest tool-result sources (tokens added):", ", ".join(
        f"{n} {t / 1e6:.1f}M" for n, t in tool_tokens.most_common(4)))

    print("\nRecommendations")
    advice = 0
    proxy = env.get("ANTHROPIC_BASE_URL", "")
    if proxy and "anthropic.com" not in proxy and env.get("ENABLE_TOOL_SEARCH") != "true":
        advice += 1
        print(f"  {advice}. ANTHROPIC_BASE_URL={proxy} silently disables tool search, so every tool schema\n"
              "     rides in the prefix. Set env ENABLE_TOOL_SEARCH=true (bench: prefix 63k -> 17k, -16%/task).")
    elif pct(prefixes, .5) > 40_000 and env.get("ENABLE_TOOL_SEARCH") != "true":
        advice += 1
        print(f"  {advice}. Prefix is {pct(prefixes, .5):,} tokens. Check /context; set ENABLE_TOOL_SEARCH=true and drop unused MCP servers.")
    window = env.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW")
    base = simulate_window(sessions, int(window) if window else None)
    best = min((simulate_window(sessions, w), w) for w in (200_000, 300_000, 400_000))
    if (base - best[0]) / total > 0.05:
        advice += 1
        print(f"  {advice}. Auto-compact window {window or 'model default (~1M on [1m] models)'}: replaying your sessions at "
              f"{best[1] // 1000}k\n     saves ~{(base - best[0]) / total:.0%} of the bill. "
              f"Set env CLAUDE_CODE_AUTO_COMPACT_WINDOW={best[1]}.")
    hit = tokens["read"] / max(1, tokens["read"] + tokens["write"] + tokens["input"])
    if hit < 0.85:
        advice += 1
        print(f"  {advice}. Cache hit {hit:.0%}: the prefix keeps being rewritten (idle past TTL, /model switches,\n"
              "     late-connecting MCP servers). Avoid mid-session model switches; consider CLAUDE_CODE_PROMPT_CACHE_TTL=1h.")
    if tool_tokens.get("Bash", 0) > 0.4 * sum(tool_tokens.values()) and "squeeze" not in json.dumps(settings.get("hooks", {})):
        advice += 1
        print(f"  {advice}. Bash output is {tool_tokens['Bash'] / sum(tool_tokens.values()):.0%} of tool-result tokens. "
              "Install the agentmaxx squeeze hook (make install).")
    if not advice:
        print("  nothing major; run `make telemetry` for per-session detail")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
