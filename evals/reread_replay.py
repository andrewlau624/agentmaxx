#!/usr/bin/env python3
"""Offline measurement: how much do repeat Reads and huge tool results cost in your own sessions?

1. Read dedupe: Reads of a path already Read earlier in the session with no Edit/Write/NotebookEdit/Bash
   touching that path in between. Split into exact repeats (same offset/limit), overlapping ranges, and
   disjoint ranges (new lines, not savable). Resident cost = tokens x requests left in the session.
2. Huge results: share of tool-result tokens from Reads over 5k tokens, WebFetch and WebSearch, the ten
   largest Read results, and how often a >5k-token Read took a whole >2000-line file.

    python3 evals/reread_replay.py [--days 14]
"""
from __future__ import annotations

import argparse
import os
import time
from collections import Counter

from evals.residency import CHARS_PER_TOKEN, PROJECTS, context_of, load

BIG = 5000  # tokens
WRITERS = ("Edit", "Write", "NotebookEdit", "MultiEdit")


def span(inp: dict) -> tuple[int, float]:
    """Inclusive line range a Read asked for (1-based; no limit means to the end of the file)."""
    start = max(1, int(inp.get("offset") or 1))
    return start, start + int(inp["limit"]) - 1 if inp.get("limit") else float("inf")


def overlaps(a: tuple[int, float], b: tuple[int, float]) -> bool:
    return a[0] <= b[1] and b[0] <= a[1]


def classify_reads(events: list) -> list[tuple[str, tuple, int, int]]:
    """For each Read result: (kind, path, at, size) with kind in first|exact|overlap|disjoint.
    A write to the path (Edit/Write/NotebookEdit, or a Bash command mentioning it) forgets earlier Reads."""
    seen: dict[str, list[tuple]] = {}
    out = []
    for kind, at, *rest in events:
        if kind != "result":
            continue
        name, inp, size = rest
        path = inp.get("file_path") or inp.get("notebook_path") or ""
        if name == "Read" and path:
            sp = span(inp)
            prior = seen.setdefault(path, [])
            k = ("first" if not prior else "exact" if sp in prior
                 else "overlap" if any(overlaps(sp, p) for p in prior) else "disjoint")
            prior.append(sp)
            out.append((k, path, at, size, inp))
        elif name in WRITERS and path:
            seen.pop(path, None)
        elif name == "Bash":
            cmd = inp.get("command") or ""
            for p in [p for p in seen if p in cmd or os.path.basename(p) in cmd]:
                seen.pop(p)
    return out


def table(rows: list[tuple]) -> None:
    w = [max(len(str(r[i])) for r in rows) for i in range(len(rows[0]))]
    for j, r in enumerate(rows):
        print("  " + "  ".join(str(c).ljust(w[i]) if i == 0 else str(c).rjust(w[i]) for i, c in enumerate(r)))
        if j == 0:
            print("  " + "  ".join("-" * x for x in w))


def report(sessions: list[dict], label: str, days: int) -> None:
    reads, tool_tok, tool_res, all_res = Counter(), Counter(), Counter(), 0
    tokens, resident = Counter(), Counter()
    big_reads, whole = [], Counter()
    for s in sessions:
        n = len(s["usage"])
        all_res += sum(context_of(u) for u in s["usage"])
        for k, path, at, size, inp in classify_reads(s["events"]):
            tok, rem = size / CHARS_PER_TOKEN, max(1, n - at)
            reads["all"] += 1
            reads[k] += 1
            tokens[k] += tok
            resident[k] += tok * rem
            if tok > BIG:
                big_reads.append((tok, path, inp))
                if not inp.get("offset") and not inp.get("limit"):
                    try:
                        lines = sum(1 for _ in open(path, errors="ignore"))
                    except OSError:
                        whole["unknown"] += 1
                        continue
                    whole["whole_big" if lines > 2000 else "whole_small"] += 1
                else:
                    whole["ranged"] += 1
        for kind, at, *rest in s["events"]:
            if kind != "result":
                continue
            name, inp, size = rest
            tok, rem = size / CHARS_PER_TOKEN, max(1, n - at)
            tool_tok["all"] += tok
            tool_res["all"] += tok * rem
            key = "Read>5k" if name == "Read" and tok > BIG else name if name in ("WebFetch", "WebSearch", "Read") else None
            if key:
                tool_tok[key] += tok
                tool_res[key] += tok * rem
    print(f"\n== {label}: {len(sessions):,} sessions, last {days}d ==")
    print(f"{reads['all']:,} Reads, {tool_tok['all'] / 1e6:.1f}M tool-result tokens, "
          f"{tool_res['all'] / 1e6:,.0f}M resident result token-turns, {all_res / 1e6:,.0f}M resident context token-turns")
    print("\nRead dedupe (repeat = same path re-Read, nothing touched it in between)")
    rows = [("kind", "reads", "% reads", "tokens added", "resident tok-turns", "% result resident", "% all resident")]
    for k in ("exact", "overlap", "disjoint"):
        rows.append((k, f"{reads[k]:,}", f"{reads[k] / max(1, reads['all']):.1%}", f"{tokens[k] / 1e3:,.0f}k",
                     f"{resident[k] / 1e6:,.1f}M", f"{resident[k] / max(1, tool_res['all']):.2%}",
                     f"{resident[k] / max(1, all_res):.2%}"))
    sav = reads["exact"] + reads["overlap"]
    rs = resident["exact"] + resident["overlap"]
    rows.append(("savable (exact+overlap)", f"{sav:,}", f"{sav / max(1, reads['all']):.1%}",
                 f"{(tokens['exact'] + tokens['overlap']) / 1e3:,.0f}k", f"{rs / 1e6:,.1f}M",
                 f"{rs / max(1, tool_res['all']):.2%}", f"{rs / max(1, all_res):.2%}"))
    table(rows)
    print("\nHuge results (share of tool-result tokens / resident token-turns)")
    rows = [("source", "tokens", "% tokens", "% resident")]
    for k in ("Read>5k", "Read", "WebFetch", "WebSearch"):
        rows.append((k if k != "Read" else "Read (all)", f"{tool_tok[k] / 1e3:,.0f}k",
                     f"{tool_tok[k] / max(1, tool_tok['all']):.1%}", f"{tool_res[k] / max(1, tool_res['all']):.1%}"))
    table(rows)
    print("\nTop 10 Read results")
    for tok, path, inp in sorted(big_reads, key=lambda x: -x[0])[:10]:
        rng = f" offset={inp.get('offset')} limit={inp.get('limit')}" if inp.get("offset") or inp.get("limit") else ""
        print(f"  {tok / 1e3:6.1f}k  {path}{rng}")
    total_big = len(big_reads)
    known = whole["whole_big"] + whole["whole_small"]
    print(f"\n{total_big:,} Reads over {BIG} tokens: {whole['ranged']:,} ranged, {known:,} whole-file (line count from disk), "
          f"{whole['unknown']:,} whole-file but file gone; {whole['whole_big']:,} "
          f"({whole['whole_big'] / max(1, total_big - whole['unknown']):.1%} of big Reads with known size) were whole reads of >2000-line files")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=14)
    args = ap.parse_args()
    cutoff = time.time() - args.days * 86400
    main_s, sub_s = [], []
    for path in PROJECTS.rglob("*.jsonl"):
        if path.stat().st_mtime >= cutoff and (s := load(path)):
            (sub_s if s["subagent"] else main_s).append(s)
    report(main_s, "main sessions", args.days)
    report(sub_s, "subagents", args.days)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
