#!/usr/bin/env python3
"""Claude Code statusline: the numbers that actually drive cost.

  opus 5.5 · ctx 142k/300k ▰▰▰▰▱▱ · cache 96% · $3.12 · feat/x

Context is the bill: every resident token is re-read each turn, so the
context gauge (against the auto-compact window, not the model maximum) is
the number to watch. Cache rate below ~80% means the prefix keeps getting
rewritten (idle >TTL, model switch, MCP reconnect).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

RESET, DIM, GREEN, YELLOW, RED = "\033[0m", "\033[2m", "\033[32m", "\033[33m", "\033[31m"


def tokens(n: float) -> str:
    return f"{n / 1000:.0f}k" if n < 1_000_000 else f"{n / 1_000_000:.1f}M"


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    parts = []
    model = (data.get("model") or {}).get("display_name") or ""
    if model:
        parts.append(model.lower().replace("claude ", ""))

    window = data.get("context_window") or {}
    usage = window.get("current_usage") or {}
    used = sum(usage.get(k, 0) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    limit = int(os.environ.get("CLAUDE_CODE_AUTO_COMPACT_WINDOW") or window.get("context_window_size") or 0)
    if used and limit:
        frac = min(used / limit, 1.0)
        color = GREEN if frac < 0.6 else YELLOW if frac < 0.85 else RED
        bar = "▰" * round(frac * 6) + "▱" * (6 - round(frac * 6))
        parts.append(f"ctx {color}{tokens(used)}/{tokens(limit)} {bar}{RESET}")
        reads = usage.get("cache_read_input_tokens", 0) or 0
        rate = reads / used
        parts.append(f"cache {(GREEN if rate >= 0.8 else YELLOW if rate >= 0.5 else RED)}{rate:.0%}{RESET}")

    cost = (data.get("cost") or {}).get("total_cost_usd")
    if cost:
        parts.append(f"${cost:.2f}")

    cwd = (data.get("workspace") or {}).get("current_dir") or data.get("cwd")
    if cwd:
        try:
            branch = subprocess.run(["git", "branch", "--show-current"], cwd=cwd, capture_output=True,
                                    text=True, timeout=1).stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            branch = ""
        if branch:
            parts.append(f"{DIM}{branch}{RESET}")
    print(f" {DIM}·{RESET} ".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
