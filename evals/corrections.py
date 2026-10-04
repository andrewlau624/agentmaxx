#!/usr/bin/env python3
"""How often you correct the agent, and whether the same correction comes back.

A falling correction rate is the closest thing to an intelligence metric
that real sessions give for free. A correction that recurs in a later
session is a lesson that didn't stick. Uses the lessons hook's CORRECTION
pattern, so it counts correction-like prompts, not proven mistakes.

    python3 evals/corrections.py [--days N]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
_spec = importlib.util.spec_from_file_location("lessons", Path(__file__).resolve().parent.parent / "hooks" / "lessons.py")
lessons = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lessons)

NOT_TYPED = ("<command-", "<local-command", "<system-reminder", "<task-notification", "[Request interrupted",
             "Caveat:", "Stop hook", "<user-prompt-submit-hook", "This session is being continued")
STOP = set("that this with from your have what when then them they just like dont didnt want also into "
           "about there here make made should would could does need still again".split())


def prompts(path: Path) -> list[tuple[float, str]]:
    """(epoch, text) for each prompt the user typed in one main-session transcript."""
    out = []
    try:
        lines = path.open(errors="ignore")
    except OSError:
        return out
    with lines:
        for line in lines:
            if '"user"' not in line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("type") != "user" or r.get("isMeta") or r.get("isSidechain"):
                continue
            if r.get("entrypoint") == "sdk-cli" or r.get("promptSource") == "sdk":
                return []  # headless `claude -p` (bench runs): nobody typed these
            content = (r.get("message") or {}).get("content")
            if isinstance(content, list):
                if any(b.get("type") == "tool_result" for b in content if isinstance(b, dict)):
                    continue
                content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
            if not isinstance(content, str) or not content.strip() or content.lstrip().startswith(NOT_TYPED):
                continue
            try:
                at = datetime.fromisoformat(r.get("timestamp", "").replace("Z", "+00:00")).timestamp()
            except ValueError:
                continue
            out.append((at, content.strip()))
    return out


def keywords(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z][a-z0-9_.-]{3,}", text.lower()) if w not in STOP}


# The lessons hook nudges on these too, but in typed prompts they're mostly
# brainstorming ("what if instead of...") or questions, not corrections.
IDEATION = re.compile(r"\b(instead of|why did you)\b", re.IGNORECASE)


def is_correction(text: str) -> bool:
    return len(text) < 600 and bool(lessons.CORRECTION.search(IDEATION.sub(" ", text)))


def recurrences(corrections: list[tuple[float, str, str]]) -> list[tuple[str, str]]:
    """(earlier, later) pairs: a correction that repeats one from an earlier session."""
    pairs = []
    ordered = sorted(corrections)
    for i, (_, session, text) in enumerate(ordered):
        words = keywords(text)
        for _, prev_session, prev in ordered[:i]:
            shared = words & keywords(prev)
            if prev_session != session and len(shared) >= 2 and len(shared) / len(words | keywords(prev)) >= 0.4:
                pairs.append((prev, text))
                break
    return pairs


def scan(days: int, root: Path = PROJECTS) -> dict:
    cutoff = time.time() - days * 86400
    weeks: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    corrections = []
    for path in root.rglob("*.jsonl"):
        if "subagents" in path.parts or path.stat().st_mtime < cutoff:
            continue
        for at, text in prompts(path):
            if at < cutoff:
                continue
            week = datetime.fromtimestamp(at).strftime("%G-W%V")
            weeks[week][1] += 1
            if is_correction(text):
                weeks[week][0] += 1
                corrections.append((at, path.stem, text))
    return {"weeks": dict(sorted(weeks.items())), "corrections": corrections, "repeats": recurrences(corrections)}


def report(stats: dict) -> list[str]:
    total = sum(n for _, n in stats["weeks"].values())
    if not total:
        return ["  no typed prompts found"]
    lines = [f"  {len(stats['corrections'])} correction-like prompts in {total:,} typed ({len(stats['corrections']) / total:.1%})"]
    lines += [f"    {w}: {c}/{n} ({c / n:.1%})" for w, (c, n) in stats["weeks"].items()]
    repeats = stats["repeats"]
    lines.append(f"  repeated from an earlier session: {len(repeats)}"
                 + (" (lessons that didn't stick, or were never recorded)" if repeats else ""))
    for prev, later in repeats[:3]:
        lines.append(f"    \"{later[:90]}\"  ~  \"{prev[:60]}\"")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=28)
    args = parser.parse_args()
    print(f"Corrections, last {args.days}d")
    print("\n".join(report(scan(args.days))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
