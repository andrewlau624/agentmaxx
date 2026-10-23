#!/usr/bin/env python3
"""Replay hooks/squeeze.py over real Bash outputs from ~/.claude/projects.

Measures what a squeeze policy would have done to the Bash results in your
own sessions: result volume, resident chars (chars x turns the result stayed
in context), outputs touched, and signal retention (lines that look like an
error/failure/verdict still present after squeezing).

    python3 evals/squeeze_replay.py [--days 14] [--subagents]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
HOOK = Path(__file__).resolve().parent.parent / "hooks" / "squeeze.py"


def load_hook():
    spec = importlib.util.spec_from_file_location("squeeze", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def outputs(days: int, subagents: bool):
    """Yield (command, stdout, remaining_turns) for every Bash result that was not already squeezed."""
    cutoff = time.time() - days * 86400
    for path in PROJECTS.rglob("*.jsonl"):
        if path.stat().st_mtime < cutoff or path.parts[-3].startswith("-private-var-folders") if len(path.parts) > 2 else False:
            continue
        if ("subagents" in path.parts) != subagents:
            continue
        recs = []
        for line in path.open(errors="ignore"):
            if line.startswith("{"):
                try:
                    recs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        uses, turn_at, turns = {}, [], 0
        for r in recs:
            if r.get("type") == "assistant":
                turns += 1
            turn_at.append(turns)
        for i, r in enumerate(recs):
            content = (r.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for b in content:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use" and b.get("name") == "Bash":
                    uses[b["id"]] = (b.get("input") or {}).get("command", "")
                elif b.get("type") == "tool_result" and b.get("tool_use_id") in uses:
                    out = b.get("content")
                    text = out if isinstance(out, str) else "".join(x.get("text", "") for x in out if isinstance(x, dict)) if isinstance(out, list) else ""
                    if "[agentmaxx: output squeezed" in text:
                        continue
                    yield uses[b["tool_use_id"]], text, max(1, turns - turn_at[i])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--subagents", action="store_true", help="replay subagent transcripts instead of main sessions")
    args = ap.parse_args()
    sq = load_hook()
    policies = {
        "v1 (8k threshold, no classes)": lambda text, cmd: sq.squeeze(text, "/tmp/x.log", sq.BUDGET) if len(text) > 8000 else None,
        "v2 (class-aware + filters)": lambda text, cmd: sq.process(text, cmd, write_spill=lambda t: "/tmp/x.log"),
        "3k for everything (AGENTMAXX_SQUEEZE_THRESHOLD=3000, _BUDGET=2000)":
            lambda text, cmd: sq.squeeze(text, "/tmp/x.log", 2000, cmd) if len(text) > 3000 else None,
    }
    stats = {name: Counter() for name in policies}
    total = Counter()
    for cmd, text, remaining in outputs(args.days, args.subagents):
        total["outputs"] += 1
        total["chars"] += len(text)
        total["resident"] += len(text) * remaining
        signal = [l for l in text.splitlines() if sq.SIGNAL.search(l)]
        for name, policy in policies.items():
            out = policy(text, cmd)
            if out is None:
                continue
            st = stats[name]
            st["touched"] += 1
            st["noisy"] += sq.is_noisy(cmd)
            st["saved_chars"] += len(text) - len(out)
            st["saved_resident"] += (len(text) - len(out)) * remaining
            st["signal_lines"] += len(signal)
            st["signal_kept"] += sum(1 for l in signal if l.strip() in out)
    print(f"{total['outputs']:,} Bash outputs, {total['chars'] / 1e6:.1f}M chars, {total['resident'] / 1e9:.2f}G resident chars "
          f"({'subagents' if args.subagents else 'main sessions'}, last {args.days}d)")
    for name, st in stats.items():
        print(f"\n{name}")
        print(f"  touched {st['touched']:,} outputs ({st['touched'] / max(1, total['outputs']):.1%}), {st['noisy']:,} of them noisy commands")
        print(f"  result volume -{st['saved_chars'] / max(1, total['chars']):.1%} ({st['saved_chars'] / 4e6:.2f}M tokens added)")
        print(f"  resident Bash chars -{st['saved_resident'] / max(1, total['resident']):.1%} ({st['saved_resident'] / 4e9:.2f}G token-turns)")
        if st["signal_lines"]:
            print(f"  signal lines kept {st['signal_kept'] / st['signal_lines']:.1%} of {st['signal_lines']:,} in touched outputs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
