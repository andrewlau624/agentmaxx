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
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import residency  # noqa: E402

PROJECTS = Path.home() / ".claude" / "projects"
SETTINGS = Path.home() / ".claude" / "settings.json"
# Weighted index: input 1, cache write 1.25 (5m TTL) or 2 (1h TTL), cache read 0.1, output 5.
WEIGHTS = {"input": 1.0, "write": 1.25, "write1h": 2.0, "read": 0.1, "output": 5.0}
COMPACT_BUFFER = 33_000


def load_sessions(days: int) -> list[dict]:
    cutoff = time.time() - days * 86400
    sessions = []
    for path in PROJECTS.rglob("*.jsonl"):
        if path.stat().st_mtime >= cutoff and (s := residency.load(path)):
            s["results"] = [(at, name, size) for kind, at, *rest in s["events"] if kind == "result"
                            for name, _, size in [rest]]
            sessions.append(s)
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


def simulate_ttl(sessions: list[dict], ttl: int) -> float:
    """Bill if every write used `ttl` seconds: a gap longer than the TTL turns the cached prefix into a rewrite."""
    price = 2.0 if ttl > 300 else 1.25
    total = 0.0
    for s in sessions:
        for i, u in enumerate(s["usage"]):
            read = u.get("cache_read_input_tokens", 0) or 0
            write = u.get("cache_creation_input_tokens", 0) or 0
            if i and read and s["times"][i] - s["times"][i - 1] > ttl:
                write, read = write + read, 0
            total += (u.get("input_tokens", 0) or 0) + write * price + read * 0.1 + (u.get("output_tokens", 0) or 0) * 5
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
            hour = (u.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) or 0
            tokens["write1h"] += hour
            tokens["write"] += (u.get("cache_creation_input_tokens", 0) or 0) - hour
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
    print(f"  cache read   {weighted['read'] / total:6.1%}")
    print(f"  cache write  {(weighted['write'] + weighted['write1h']) / total:6.1%}"
          f"  ({tokens['write1h'] / max(1, tokens['write'] + tokens['write1h']):.0%} at the 1h price)")
    for k in ("output", "input"):
        print(f"  {k:12}", f"{weighted[k] / total:6.1%}")
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
    one_hour, five_min = simulate_ttl(sessions, 3600), simulate_ttl(sessions, 300)
    on_1h = tokens["write1h"] > tokens["write"]
    if abs(one_hour - five_min) / min(one_hour, five_min) > 0.03 and on_1h != (one_hour < five_min):
        advice += 1
        better, worse = ("1h", five_min) if one_hour < five_min else ("5m", one_hour)
        print(f"  {advice}. Cache TTL: replaying your request gaps, {better} costs "
              f"{1 - min(one_hour, five_min) / worse:.0%} less than what you run now.\n"
              f"     Set env CLAUDE_CODE_PROMPT_CACHE_TTL={better}.")
    hit = tokens["read"] / max(1, tokens["read"] + tokens["write"] + tokens["write1h"] + tokens["input"])
    if hit < 0.85:
        advice += 1
        print(f"  {advice}. Cache hit {hit:.0%}: the prefix keeps being rewritten (idle past TTL, /model switches,\n"
              "     late-connecting MCP servers). Avoid mid-session model switches; consider CLAUDE_CODE_PROMPT_CACHE_TTL=1h.")
    if tool_tokens.get("Bash", 0) > 0.4 * sum(tool_tokens.values()) and "squeeze" not in json.dumps(settings.get("hooks", {})):
        advice += 1
        print(f"  {advice}. Bash output is {tool_tokens['Bash'] / sum(tool_tokens.values()):.0%} of tool-result tokens. "
              "Install the agentmaxx squeeze hook (make install).")
    listing = sum(tok * (1.8 + 0.1 * max(0, len(s["usage"]) - at)) for s in sessions
                  for kind, at, *rest in s["events"] if kind == "skills" for tok in rest[:1])
    if listing / total > 0.015:
        used = {rest[0] for s in sessions for kind, _, *rest in s["events"] if kind == "invoked" and rest}
        advice += 1
        print(f"  {advice}. The skill listing rides in every request: {listing / total:.1%} of your bill. In {args.days}d Claude\n"
              f"     invoked {len(used)} skills on its own: {', '.join(sorted(used))}.\n"
              '     Hide the ones you only run by hand with settings.json\n'
              '     "skillOverrides": {"<name>": "user-invocable-only"} (they stay available as /name).')
    if not advice:
        print("  nothing major; run `make telemetry` for per-session detail")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
