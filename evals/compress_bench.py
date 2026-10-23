#!/usr/bin/env python3
"""Replay better-compress against v2 squeeze over real Bash outputs.

Same corpus and metrics as squeeze_replay.py (result volume, resident chars,
signal retention), plus the router's backend mix. Run with the python that has
headroom installed to measure the combined stack:

    python3 evals/compress_bench.py [--days 14] [--subagents]
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from collections import Counter
from pathlib import Path

EVALS = Path(__file__).resolve().parent
ROOT = EVALS.parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--subagents", action="store_true")
    args = ap.parse_args()
    replay = load("squeeze_replay", EVALS / "squeeze_replay.py")
    sq = replay.load_hook()
    bc = load("better_compress", ROOT / "tools" / "better-compress" / "better_compress.py")

    def v2(text, cmd):
        os.environ.pop("AGENTMAXX_SQUEEZE_ROUTER", None)
        return sq.process(text, cmd, write_spill=lambda t: "/tmp/x.log"), None

    def v2_router(text, cmd):
        os.environ["AGENTMAXX_SQUEEZE_ROUTER"] = "1"
        out = sq.process(text, cmd, write_spill=lambda t: "/tmp/x.log")
        info = None
        if out and "[better-compress:" in out:
            info = {"kind": bc.classify(text, cmd), "backend": "routed"}
        return out, info

    policies = {"v2 squeeze": v2, "v2 + router flag": v2_router}
    stats = {name: Counter() for name in policies}
    total = Counter()
    for cmd, text, remaining in replay.outputs(args.days, args.subagents):
        total["outputs"] += 1
        total["chars"] += len(text)
        total["resident"] += len(text) * remaining
        signal = [l for l in text.splitlines() if sq.SIGNAL.search(l)]
        for name, policy in policies.items():
            out, info = policy(text, cmd)
            if out is None:
                continue
            st = stats[name]
            st["touched"] += 1
            st["saved_chars"] += len(text) - len(out)
            st["saved_resident"] += (len(text) - len(out)) * remaining
            st["signal_lines"] += len(signal)
            st["signal_kept"] += sum(1 for l in signal if l.strip() in out)
            if info:
                st[f"via_{info['backend']}"] += 1
                st[f"kind_{info['kind']}"] += 1
    print(f"{total['outputs']:,} Bash outputs, {total['chars'] / 1e6:.1f}M chars, {total['resident'] / 1e9:.2f}G resident chars "
          f"({'subagents' if args.subagents else 'main sessions'}, last {args.days}d)")
    for name, st in stats.items():
        print(f"\n{name}")
        print(f"  touched {st['touched']:,} ({st['touched'] / max(1, total['outputs']):.1%})")
        print(f"  result volume -{st['saved_chars'] / max(1, total['chars']):.1%} ({st['saved_chars'] / 4e6:.2f}M tokens added)")
        print(f"  resident Bash chars -{st['saved_resident'] / max(1, total['resident']):.1%} ({st['saved_resident'] / 4e9:.2f}G token-turns)")
        if st["signal_lines"]:
            print(f"  signal lines kept {st['signal_kept'] / st['signal_lines']:.1%} of {st['signal_lines']:,} in touched outputs")
        mix = " ".join(f"{k}={v:,}" for k, v in sorted(st.items()) if k.startswith(("via_", "kind_")))
        if mix:
            print(f"  mix: {mix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
