#!/usr/bin/env python3
"""Flag machine-sounding text the agent just wrote, once, with the specific hits.

PostToolUse on Write/Edit/MultiEdit: scores the written text with
evals/tells.py and, over the threshold, feeds the hits back so the agent
rewrites them. PreToolUse on Bash: scores the message of a `git commit -m`
and denies it once with the hits.

Each file is flagged at most once per session, and commits once per session,
so a quoted tell (a style guide, a test fixture) can never trap the agent.
Thresholds sit above the human baseline in evals/RESULTS.md: pre-2022 docs
from four projects run p90 1.4 hits per 1k words, commits 0.2% with any hit.
Disable with AGENTMAXX_TELLS=0.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "evals")]  # installed copy sits next to this file
from tells import EXT_KIND, score  # noqa: E402

STATE = Path(os.environ.get("AGENTMAXX_HOME", os.path.expanduser("~/.local/share/agentmaxx"))) / "tells"
# minimum hits and density before a file is flagged
LIMITS = {"prose": (3, 3.0), "ui": (3, 0.0), "code": (2, 0.0), "commit": (1, 0.0)}
EMOJI_SUBJECT = re.compile(r"^[\U0001F300-\U0001FAFF✅✨⭐⚡]")


def once(session: str, key: str) -> bool:
    """True the first time (session, key) is seen."""
    STATE.mkdir(parents=True, exist_ok=True)
    mark = STATE / hashlib.sha1(f"{session}:{key}".encode()).hexdigest()
    if mark.exists():
        return False
    mark.touch()
    return True


def over(r: dict) -> bool:
    hits, density = LIMITS[r["kind"]]
    return r["count"] >= hits and r["density"] >= density


def describe(r: dict) -> str:
    return "; ".join(f"{name}: {', '.join(dict.fromkeys(found))[:80]}" for name, found in r["hits"].items())


def commit_message(command: str) -> str | None:
    """The message of a `git commit` in this command, from -m/--message or a heredoc fed to it."""
    line = re.search(r"^[^\n]*?\bgit\b[^|;&\n<]*?\bcommit\b[^\n]*", command, re.M)
    if not line or line.group(0).lstrip().startswith(("#", "echo", "print")):
        return None
    tag = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", line.group(0))
    if tag:
        body = re.search(rf"\n(.*?)\n\s*{tag.group(1)}\b", command[line.end():], re.S)
        return body.group(1) if body else None
    segment = next((seg for seg in re.split(r"&&|\|\||;", line.group(0)) if re.search(r"\bcommit\b", seg)), "")
    try:
        argv = shlex.split(segment)
    except ValueError:
        return None
    if "git" not in argv:
        return None
    parts = [argv[i + 1] for i, a in enumerate(argv[:-1]) if re.fullmatch(r"-[a-zA-Z]*m|--message", a)]
    parts += [a.split("=", 1)[1] for a in argv if a.startswith("--message=")]
    return "\n\n".join(parts) or None


def repo_uses_emoji(cwd: str) -> bool:
    log = subprocess.run(["git", "log", "-30", "--format=%s"], cwd=cwd, capture_output=True, text=True).stdout
    subjects = log.splitlines()
    return bool(subjects) and sum(bool(EMOJI_SUBJECT.match(s)) for s in subjects) >= len(subjects) / 3


def check_write(tool_input: dict) -> dict | None:
    path = tool_input.get("file_path", "")
    kind = EXT_KIND.get(Path(path).suffix.lower())
    if not kind:
        return None
    if kind == "prose":
        try:
            text = Path(path).read_text(errors="ignore")  # density only means something over the whole doc
        except OSError:
            return None
    else:
        edits = tool_input.get("edits") or [tool_input]
        text = tool_input.get("content") or "\n".join(e.get("new_string", "") for e in edits)
    r = score(text, kind)
    return r if over(r) else None


def main() -> int:
    if os.environ.get("AGENTMAXX_TELLS") == "0":
        return 0
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    tool, tool_input = event.get("tool_name"), event.get("tool_input") or {}
    session = event.get("session_id", "")
    if event.get("hook_event_name") == "PreToolUse" and tool == "Bash":
        message = commit_message(tool_input.get("command", ""))
        if not message:
            return 0
        r = score(message, "commit", repo_uses_emoji(event.get("cwd") or "."))
        if over(r) and once(session, "commit"):
            json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                              "permissionDecisionReason": "agentmaxx tells: the commit message reads as machine-written ("
                                              + describe(r) + "). Say what changed and why in plain words, then commit again."}},
                      sys.stdout)
        return 0
    if event.get("hook_event_name") == "PostToolUse" and tool in ("Write", "Edit", "MultiEdit"):
        r = check_write(tool_input)
        if r and once(session, tool_input.get("file_path", "")):
            json.dump({"decision": "block",
                       "reason": f"agentmaxx tells: {tool_input.get('file_path')} has {r['count']} machine-writing tells ("
                       + describe(r) + "). Rewrite those parts plainly; keep everything else."}, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
