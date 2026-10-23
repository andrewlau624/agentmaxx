#!/usr/bin/env python3
"""Measure a CLAUDE.md and propose (or apply) a split into rules and on-demand docs.

    python3 measure.py CLAUDE.md                      # sizes, per-section verdicts, proposed split
    python3 measure.py CLAUDE.md --keep 3 --move 10   # override a section's verdict by its index
    python3 measure.py CLAUDE.md --apply [--out docs/memory]

Every CLAUDE.md token is attached to every request and every subagent in the
repo, so a 40k-token file costs about 4k token-equivalents per request as
cache reads alone and gets rewritten in full whenever the cache misses.
Rules the agent needs on every turn stay; logs, findings, specs and other
reference material move to docs the agent reads when the task calls for
them, behind a one-line index.

Nothing is deleted: --apply writes a byte-exact backup next to the docs
before touching CLAUDE.md.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

CHARS_PER_TOKEN = 3.6
KEEP_BUDGET = 2_000      # tokens a CLAUDE.md should stay under
RULE_MAX = 900           # a section bigger than this is reference even if it reads like rules

LOG_HEAD = re.compile(r"session|log\b|\d{4}-\d{2}-\d{2}|result|finding|audit|pilot|phase|validation|"
                      r"spec|experiment|diagnos|reconstruction|map\b|ledger|memory", re.I)
KEEP_HEAD = re.compile(r"objective|priority|hard facts|trap|do not|don't|never|exhausted|non-negotiable|standard|checklist|\(user|"
                       r"rule|philosophy|permission|allowed|standing|permanent|how to|what this|orientation|assumption", re.I)
USER_RULE = re.compile(r"\(user[,)]|\buser,|permanent|standing permission|non-negotiable|user correction", re.I)
RULE_LINE = re.compile(r"^\s*[-*\d.]+\s|\b(must|never|always|do not|don't|before|after|only|use|read|run|report|"
                       r"rank|keep|ask|check|prefer|allowed|permission)\b", re.I)
NUMERIC = re.compile(r"\d")


def sections(text: str) -> list[dict]:
    """Split on top-level `##` headings; the preamble (title, intro) is section 0."""
    out, cur = [], {"heading": "(preamble)", "lines": []}
    for line in text.splitlines():
        if line.startswith("## "):
            out.append(cur)
            cur = {"heading": line[3:].strip(), "lines": []}
        else:
            cur["lines"].append(line)
    out.append(cur)
    for i, s in enumerate(out):
        s["index"] = i
        body = "\n".join(s["lines"])
        s["tokens"] = len(body) / CHARS_PER_TOKEN
        s["verdict"], s["why"] = classify(s["heading"], s["lines"], s["tokens"])
    return out


def classify(heading: str, lines: list[str], tokens: float) -> tuple[str, str]:
    content = [l for l in lines if l.strip()]
    if not content:
        return "keep", "empty"
    rule_share = sum(1 for l in content if RULE_LINE.search(l)) / len(content)
    numeric_share = sum(1 for l in content if NUMERIC.search(l)) / len(content)
    fenced = sum(1 for l in content if l.startswith("```")) // 2
    tables = sum(1 for l in content if l.startswith("|"))
    if heading == "(preamble)" and tokens < RULE_MAX:
        return "keep", "title and orientation"
    if tokens > RULE_MAX:
        return "move", f"{tokens:,.0f} tokens; too long to be a per-turn rule"
    if KEEP_HEAD.search(heading) and not re.search(r"research memory|session log|session \"|\bresults?\b", heading, re.I):
        return "keep", "standing rule by heading"
    if LOG_HEAD.search(heading) and tokens > 120:
        return "move", "log or findings by heading"
    if fenced or tables > 3:
        return "move", "code blocks or tables are reference"
    if rule_share >= 0.4:
        return "keep", f"{rule_share:.0%} rule-shaped lines"
    return "move", f"{rule_share:.0%} rule-shaped lines, {numeric_share:.0%} numeric"


def slug(heading: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", heading.lower()).strip("-")
    return s[:60] or "section"


def first_sentence(lines: list[str]) -> str:
    for l in lines:
        t = l.strip().lstrip("-*#> ").strip()
        if len(t) > 20 and not t.startswith(("|", "```")):
            return re.split(r"(?<=[.!?])\s", t, maxsplit=1)[0][:140]
    return ""


def hoisted(secs: list[dict]) -> list[tuple[str, str]]:
    """(heading, body) of every `###` subsection in a moved section whose heading reads like a user-stated rule."""
    out = []
    for s in secs:
        if s["verdict"] != "move":
            continue
        cur, body = None, []
        for line in s["lines"] + ["### "]:
            if line.startswith("### "):
                if cur and USER_RULE.search(cur):
                    out.append((cur, "\n".join(body).strip("\n")))
                cur, body = line[4:].strip(), []
            elif cur is not None:
                body.append(line)
    return out


def report(path: Path, secs: list[dict]) -> None:
    total = sum(s["tokens"] for s in secs)
    keep = sum(s["tokens"] for s in secs if s["verdict"] == "keep")
    print(f"{path}: {total:,.0f} tokens in {len(secs)} sections; "
          f"{'over' if total > 8_000 else 'under'} the 8k line where doctor flags it")
    for s in secs:
        print(f"  [{s['index']:>2}] {s['verdict']:4} {s['tokens']:>7,.0f}  {s['heading'][:64]}  ({s['why']})")
    print(f"proposed: keep {keep:,.0f} tokens (budget {KEEP_BUDGET:,}), move {total - keep:,.0f} into docs. "
          f"Cache reads alone: {total * 0.1:,.0f} -> {keep * 0.1:,.0f} token-equivalents per request.")
    hoist = hoisted(secs)
    if hoist:
        print(f"user-stated rules inside moved sections, copied into CLAUDE.md on --apply ({sum(len(b) for _, b in hoist) / CHARS_PER_TOKEN:,.0f} tokens):")
        for h, _ in hoist:
            print(f"  {h[:100]}")
    if keep > KEEP_BUDGET:
        print(f"kept sections still exceed {KEEP_BUDGET:,} tokens: tighten their prose by hand after applying.")


def apply(path: Path, secs: list[dict], out_dir: Path) -> None:
    text = path.read_text()
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H%M")
    backup = out_dir / f"CLAUDE.md.{stamp}.before-diet"
    backup.write_text(text)
    moved = []
    for s in secs:
        if s["verdict"] != "move":
            continue
        name = f"{s['index']:02d}-{slug(s['heading'])}.md"
        body = "\n".join(s["lines"]).strip("\n")
        (out_dir / name).write_text(f"# {s['heading']}\n\n{body}\n")
        moved.append((name, s))
    index_lines = [f"# {path.parent.name}: memory index", "",
                   "One line per file. Read a file when the task touches its subject; do not read all of them.", ""]
    for name, s in moved:
        index_lines.append(f"- `{name}` ({s['tokens']:,.0f} tok): {s['heading']}. {first_sentence(s['lines'])}")
    (out_dir / "INDEX.md").write_text("\n".join(index_lines) + "\n")
    kept = []
    for s in secs:
        if s["verdict"] == "keep":
            kept.append(("" if s["heading"] == "(preamble)" else f"## {s['heading']}\n") + "\n".join(s["lines"]).strip("\n") + "\n")
    hoist = hoisted(secs)
    if hoist:
        kept.append("## Standing rules recorded during sessions\n" +
                    "\n".join(f"### {h}\n{b}\n" for h, b in hoist))
    rel = out_dir.relative_to(path.parent) if out_dir.is_relative_to(path.parent) else out_dir
    pointer = (f"## Memory lives in `{rel}/`\n"
               f"Before proposing an experiment, a design, or a claim about what was already tried, read `{rel}/INDEX.md` "
               f"and then only the files whose subject matches. {len(moved)} files, "
               f"{sum(s['tokens'] for _, s in moved):,.0f} tokens in total; this file carries the rules that apply every turn. "
               f"New findings go into a new file there plus one index line, never into this file.\n")
    path.write_text("\n".join(kept) + "\n" + pointer)
    after = len(path.read_text()) / CHARS_PER_TOKEN
    print(f"applied: CLAUDE.md {len(text) / CHARS_PER_TOKEN:,.0f} -> {after:,.0f} tokens; {len(moved)} files in {out_dir}; "
          f"backup {backup}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("path", type=Path)
    ap.add_argument("--keep", type=int, nargs="*", default=[], help="section indexes to keep regardless")
    ap.add_argument("--move", type=int, nargs="*", default=[], help="section indexes to move regardless")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", type=Path, help="docs directory (default <repo>/docs/memory)")
    args = ap.parse_args()
    secs = sections(args.path.read_text())
    for i in args.keep:
        secs[i]["verdict"], secs[i]["why"] = "keep", "kept by flag"
    for i in args.move:
        secs[i]["verdict"], secs[i]["why"] = "move", "moved by flag"
    report(args.path, secs)
    if args.apply:
        apply(args.path, secs, args.out or args.path.parent / "docs" / "memory")
    return 0


if __name__ == "__main__":
    sys.exit(main())
