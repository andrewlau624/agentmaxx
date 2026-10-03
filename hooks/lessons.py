#!/usr/bin/env python3
"""Cross-session lessons: turn user corrections into rules the next session sees.

Hook modes (stdin = hook event JSON, stdout = context added for the model):
  session-start   inject this repo's lessons plus global ones, capped
  prompt          if the user's message reads as a correction, tell the
                  model how to record the reusable rule

CLI:
  lessons.py add [--global] TEXT    record a lesson (deduped)
  lessons.py list [--global]
  lessons.py vote ID up|down        helpful/harmful counter; down x2 retires it
  lessons.py rm ID

Design follows ACE (arXiv 2510.04618) and the memory-poisoning results:
lessons are one-line records edited individually, never rewritten as a
whole; only the model acting on a user's correction (or the user) adds them;
harmful votes retire them; injection is capped so the file can't bloat
every prompt.

A repo is keyed by its root commit, so every clone and worktree of the same
project shares one lesson file.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("AGENTMAXX_HOME", Path.home() / ".local/share/agentmaxx")) / "lessons"
INJECT_CHARS = int(os.environ.get("AGENTMAXX_LESSONS_CHARS", "1500"))
RECORD = re.compile(r"^- \[(L\d+) h=(\d+) x=(\d+) ([\d-]+)\] (.+)$")
CORRECTION = re.compile(
    r"^(no\b|nope\b|wrong\b|stop\b)|\b(that'?s (wrong|not (what|right))|you (forgot|missed|didn'?t|keep|always|never)|"
    r"i (said|told you|asked)|don'?t (do|use|add|ever)|never (do|use)|always (use|do|add|run)|"
    r"instead of|not like that|why did you)\b",
    re.IGNORECASE,
)


def repo_key(cwd: str) -> str | None:
    try:
        out = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=cwd,
                             capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    roots = out.stdout.split()
    return roots[-1][:12] if out.returncode == 0 and roots else None


def path_for(cwd: str, global_scope: bool) -> Path | None:
    if global_scope:
        return HOME / "global.md"
    key = repo_key(cwd)
    return HOME / f"repo-{key}.md" if key else None


def load(path: Path) -> list[dict]:
    if not path or not path.exists():
        return []
    items = []
    for line in path.read_text().splitlines():
        m = RECORD.match(line)
        if m:
            items.append(dict(id=m[1], h=int(m[2]), x=int(m[3]), date=m[4], text=m[5]))
    return items


def save(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"- [{i['id']} h={i['h']} x={i['x']} {i['date']}] {i['text']}" for i in items)
    path.write_text(body + ("\n" if body else ""))


def _norm(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def add(path: Path, text: str) -> str:
    text = " ".join(text.split())[:300]
    items = load(path)
    words = _norm(text)
    for item in items:
        other = _norm(item["text"])
        if words and len(words & other) / len(words | other) > 0.6:
            item["text"], item["date"] = text, time.strftime("%Y-%m-%d")
            save(path, items)
            return f"updated {item['id']}"
    next_id = max((int(i["id"][1:]) for i in items), default=0) + 1
    items.append(dict(id=f"L{next_id}", h=0, x=0, date=time.strftime("%Y-%m-%d"), text=text))
    save(path, items)
    return f"added L{next_id}"


def render(cwd: str) -> str:
    sections = []
    for scope, path in (("this repo", path_for(cwd, False)), ("all repos", path_for(cwd, True))):
        items = sorted(load(path), key=lambda i: (i["h"] - i["x"], i["date"]), reverse=True)
        if items:
            sections.append((scope, items))
    if not sections:
        return ""
    lines, used = ["Lessons from past corrections (follow them; they override defaults):"], 0
    for scope, items in sections:
        for item in items:
            line = f"- ({scope}, {item['id']}) {item['text']}"
            if used + len(line) > INJECT_CHARS:
                break
            lines.append(line)
            used += len(line)
    return "\n".join(lines)


def hook(mode: str) -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    cwd = event.get("cwd") or os.getcwd()
    me = f"python3 {Path(__file__).resolve()}"
    if mode == "session-start":
        text = render(cwd)
        if text:
            print(text)
    elif mode == "prompt":
        prompt = event.get("prompt", "")
        if len(prompt) < 600 and CORRECTION.search(prompt):
            print(
                "The user may be correcting you. After addressing it, if the correction is a reusable rule "
                "(a preference or convention, not a one-off fix), record it as one imperative line: "
                f"`{me} add \"<rule>\"` (add --global if it applies beyond this repo). Skip this if it's one-off."
            )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "hook":
        return hook(argv[1])
    global_scope = "--global" in argv
    argv = [a for a in argv if a != "--global"]
    path = path_for(os.getcwd(), global_scope)
    if path is None:
        print("not in a git repo; use --global")
        return 1
    if argv[:1] == ["add"] and len(argv) > 1:
        print(add(path, " ".join(argv[1:])))
    elif argv[:1] == ["list"]:
        print(path.read_text() if path.exists() else "(none)", end="")
    elif argv[:1] == ["vote"] and len(argv) == 3:
        items = load(path)
        for item in items:
            if item["id"] == argv[1]:
                item["h" if argv[2] == "up" else "x"] += 1
        save(path, [i for i in items if i["x"] < 2 or i["x"] <= i["h"]])
    elif argv[:1] == ["rm"] and len(argv) == 2:
        save(path, [i for i in load(path) if i["id"] != argv[1]])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
