#!/usr/bin/env python3
"""Cross-session lessons: turn user corrections into rules the next session sees.

Hook modes (stdin = hook event JSON, stdout = context added for the model):
  session-start   inject this repo's lessons plus global ones, capped
  prompt          if the user's message reads as a correction, tell the
                  model how to record the reusable rule, with the message
                  being corrected quoted as evidence
  failure         PostToolUseFailure: inject the 1-3 lessons whose words
                  overlap the error/command, each at most once per session

CLI:
  lessons.py add [--global] [--evidence TEXT] TEXT    record a lesson (deduped)
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
import shlex
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("AGENTMAXX_HOME", Path.home() / ".local/share/agentmaxx")) / "lessons"
# Injected once per session (SessionStart), so this is ~1.4k tokens resident, not per turn.
# 1500 dropped 12 of 18 lessons in a repo with nine of its own, including every global one.
INJECT_CHARS = int(os.environ.get("AGENTMAXX_LESSONS_CHARS", "5000"))
RECORD = re.compile(r"^- \[(L\d+) h=(\d+) x=(\d+) ([\d-]+)\] (.+)$")
# Provenance: the assistant text the correction was aimed at, kept on an
# indented line under the record so old one-line files still parse.
EVIDENCE = re.compile(r"^  evidence: (.+)$")
EVIDENCE_CHARS = 160
# Tuned on a hand-labelled set of 73 typed prompts (evals/test_corrections.py):
# an opener like "no"/"wait"/"actually"/"still" counts only with a correction
# shape right after it, so bare "no", "no <url>", "no X?" and "wait yesterday
# i was sick" stay out while "no i meant", "wait but you're", "still not a
# fan" and "its not loading" come in.
CORRECTION = re.compile(
    r"^(?:no|nope|nah|wrong)\b(?![\s,.!-]*(?:\S+\s+)?https?://)(?!.{0,120}\?\s*$)[\s,.!-]*\w"
    r"|^(?:stop|undo|shorter)\b"
    r"|^(?:wait|actually|hold on)\b[\s,.!-]*(?:but|no|not|i|i'?m|im|you|you'?re|the|on|it|it'?s|its|this|that|edit|please|"
    r"stop|don'?t|use|we|let'?s|just|make)\b"
    r"|^still\b[\s,]*(?:not|no|a lot|too|the same|same|broken|wrong|doesn'?t|isn'?t|says|shows|has|have|fails|failing|getting|seeing)\b"
    r"|^just (?:do|run|fix)\b"
    r"|^it'?s (?:not|still)\b"
    r"|^this is not\b"
    r"|\b(?:that'?s (?:wrong|not (?:what|right))|you (?:forgot|missed|didn'?t|keep|always|never)|you'?re (?:forgetting|ignoring|missing|not)|"
    r"i (?:said|told you|asked (?:you|for)|meant|didn'?t (?:ask|say|want))|don'?t (?:do|use|add|ever)|never (?:do|use)|always (?:use|do|add|run)|"
    r"instead of|not like that|why did you|not a (?:big )?fan|stop (?:saying|asking|doing|using|adding)|too (?:long|verbose))\b",
    re.IGNORECASE,
)
# Words too common to tie a failure to a lesson on their own.
MATCH_STOP = set("the and for with this that not use run file files when from never always repo you your are was were "
                 "have has into then than error failed failure command line does don doesn before after instead only also "
                 "all any can will should must here there like make sure just want need them they what which while "
                 "about because been being but did each how its let may more most other our out own same some such "
                 "too very who why would could tool input output exit code status returned "
                 # path pieces and Python noise that matched unrelated lessons on a real KeyError ("claude" from ~/.claude)
                 "claude users documents projects python python3 json print type name text path data true false none "
                 "import module object list dict str int key value self return def call traceback".split())


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
            continue
        e = EVIDENCE.match(line)
        if e and items:
            items[-1]["evidence"] = e[1]
    return items


def save(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i in items:
        lines.append(f"- [{i['id']} h={i['h']} x={i['x']} {i['date']}] {i['text']}")
        if i.get("evidence"):
            lines.append(f"  evidence: {i['evidence']}")
    body = "\n".join(lines)
    path.write_text(body + ("\n" if body else ""))


def _norm(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def add(path: Path, text: str, evidence: str | None = None) -> str:
    text = " ".join(text.split())[:300]
    evidence = " ".join((evidence or "").split())[:EVIDENCE_CHARS]
    items = load(path)
    words = _norm(text)
    for item in items:
        other = _norm(item["text"])
        if words and len(words & other) / len(words | other) > 0.6:
            item["text"], item["date"] = text, time.strftime("%Y-%m-%d")
            if evidence:
                item["evidence"] = evidence
            save(path, items)
            return f"updated {item['id']}"
    next_id = max((int(i["id"][1:]) for i in items), default=0) + 1
    item = dict(id=f"L{next_id}", h=0, x=0, date=time.strftime("%Y-%m-%d"), text=text)
    if evidence:
        item["evidence"] = evidence
    items.append(item)
    save(path, items)
    return f"added L{next_id}"


def last_assistant_text(transcript_path: str, limit: int = EVIDENCE_CHARS) -> str:
    """First `limit` chars of the newest assistant text in the transcript (the thing being corrected)."""
    if not transcript_path:
        return ""
    try:
        with open(transcript_path, "rb") as fh:
            fh.seek(0, os.SEEK_END)
            fh.seek(max(0, fh.tell() - 262144))
            tail = fh.read().decode("utf-8", errors="ignore")
    except OSError:
        return ""
    for line in reversed(tail.splitlines()):
        if '"assistant"' not in line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("type") != "assistant":
            continue
        content = (r.get("message") or {}).get("content")
        if isinstance(content, list):
            content = " ".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        if isinstance(content, str) and content.strip():
            return " ".join(content.split())[:limit]
    return ""


def matching(cwd: str, text: str, limit: int = 3) -> list[tuple[str, dict]]:
    """Lessons whose distinctive words overlap `text`, best first: [(scope, item)]."""
    words = {w for w in _norm(text) if len(w) >= 3 and w not in MATCH_STOP}
    if not words:
        return []
    scored = []
    for scope, path in (("this repo", path_for(cwd, False)), ("all repos", path_for(cwd, True))):
        for item in load(path):
            shared = {w for w in _norm(item["text"]) if len(w) >= 3 and w not in MATCH_STOP} & words
            if shared:
                scored.append((len(shared), item["h"] - item["x"], scope, item))
    scored.sort(key=lambda s: (s[0], s[1]), reverse=True)
    return [(scope, item) for _, _, scope, item in scored[:limit]]


def _fired_path(session_id: str) -> Path | None:
    sid = re.sub(r"[^A-Za-z0-9_-]", "", session_id or "")[:80]
    return HOME / "fired" / f"{sid}.json" if sid else None


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
            evidence = last_assistant_text(event.get("transcript_path", ""))
            ev_arg = f" --evidence {shlex.quote(evidence)}" if evidence else ""
            print(
                "The user may be correcting you. After addressing it, if the correction is a reusable rule "
                "(a preference or convention, not a one-off fix), record it as one imperative line: "
                f"`{me} add{ev_arg} \"<rule>\"` (add --global if it applies beyond this repo). "
                "Keep the --evidence text as given: it is the message being corrected. Skip this if it's one-off."
            )
    elif mode == "failure":
        tool_input = event.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            tool_input = {}
        text = " ".join(str(x) for x in (str(event.get("error") or "")[:300], tool_input.get("command", ""),
                                          tool_input.get("file_path", "")))
        hits = matching(cwd, text)
        fired_path = _fired_path(event.get("session_id", ""))
        fired: list[str] = []
        if fired_path and fired_path.exists():
            try:
                fired = json.loads(fired_path.read_text())
            except (OSError, json.JSONDecodeError):
                fired = []
        fresh = [(scope, item) for scope, item in hits if f"{scope}:{item['id']}" not in fired]
        if not fresh:
            return 0
        if fired_path:
            fired_path.parent.mkdir(parents=True, exist_ok=True)
            fired_path.write_text(json.dumps(fired + [f"{scope}:{item['id']}" for scope, item in fresh]))
        note = "Lessons that match this failure:\n" + "".join(
            f"- ({scope}, {item['id']}) {item['text']}\n" for scope, item in fresh)
        json.dump({"hookSpecificOutput": {"hookEventName": "PostToolUseFailure", "additionalContext": note}}, sys.stdout)
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "hook":
        return hook(argv[1])
    global_scope = "--global" in argv
    argv = [a for a in argv if a != "--global"]
    evidence = None
    if "--evidence" in argv:
        i = argv.index("--evidence")
        evidence = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
    path = path_for(os.getcwd(), global_scope)
    if path is None:
        print("not in a git repo; use --global")
        return 1
    if argv[:1] == ["add"] and len(argv) > 1:
        print(add(path, " ".join(argv[1:]), evidence))
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
