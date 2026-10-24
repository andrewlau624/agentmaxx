#!/usr/bin/env python3
"""Per-repo research log: deny near-duplicate web searches, including ones from earlier sessions.

PreToolUse on WebSearch and WebFetch. Every query and URL is appended to an
append-only log keyed by repo (root commit, like lessons.py), so the log is
shared by every clone and worktree. On each WebSearch the query is normalised
(lowercase, `site:` and punctuation stripped, stopwords dropped, word set) and
compared by Jaccard with the repo's earlier queries. A near-duplicate is denied
with a reason that names the prior query and date and asks for a new angle.
Each prior match is denied at most once per session, so a deliberate re-run
goes through on the second try. WebFetch is only deduped on the exact URL
within the same session: adjacent doc pages across sessions are legitimate.

Why: in 30 days of transcripts, 12% of swing-trader searches had a >=0.5
Jaccard twin in a different session, and the worst chain was 13 queries in one
frame with a noun swapped (evals/quality-research.md). Nothing remembered what
had already been looked up.

CLI:
  research_log.py recent [CWD] [N]   print the last N (default 30) queries for the repo

Disable with AGENTMAXX_RESEARCH_LOG=0.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.environ.get("AGENTMAXX_HOME", Path.home() / ".local/share/agentmaxx")) / "research"
SAME_SESSION = float(os.environ.get("AGENTMAXX_RESEARCH_SAME", "0.8"))
CROSS_SESSION = float(os.environ.get("AGENTMAXX_RESEARCH_CROSS", "0.6"))
MAX_ENTRIES = 2000
MIN_WORDS = 3  # one- or two-word queries are too short for Jaccard to mean anything
STOP = {"the", "a", "an", "of", "in", "for", "to", "and", "on", "with", "is", "are", "how", "what",
        "or", "vs", "by", "at", "from", "do", "does", "it", "that", "this", "be", "as", "can", "i"}
# A query that adds one of these to a prior frame is the angle change the deny asks for; let it run.
ANGLE = {"reddit", "forum", "forums", "hn", "twitter", "blog", "complaints", "experience", "review", "reviews",
         "criticism", "critique", "critics", "skeptic", "debunk", "fail", "fails", "failure", "failures", "flaw",
         "flaws", "limitation", "limitations", "pitfall", "pitfalls", "drawback", "drawbacks", "problem", "problems",
         "alternative", "alternatives", "versus", "instead", "paper", "arxiv", "ssrn", "study", "github", "issue",
         "issues", "docs", "documentation", "changelog"}
SITE = re.compile(r"\bsite:\S+", re.IGNORECASE)
REASON = ("Near-duplicate of a query already run ({date}, \"{prior}\"). Change the angle: search for why it "
          "fails or alternatives, pivot the source type (paper / docs / forum / issue tracker), or narrow to "
          "the specific claim you still need. Re-run the same call if you really need it again.")


def repo_key(cwd: str) -> str:
    """Root commit like lessons.py; a path hash outside git so research is still logged."""
    try:
        out = subprocess.run(["git", "rev-list", "--max-parents=0", "HEAD"], cwd=cwd,
                             capture_output=True, text=True, timeout=5)
        roots = out.stdout.split()
        if out.returncode == 0 and roots:
            return roots[-1][:12]
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "dir-" + hashlib.sha1(os.path.realpath(cwd).encode()).hexdigest()[:12]


def path_for(cwd: str) -> Path:
    return HOME / f"repo-{repo_key(cwd)}.jsonl"


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    items = []
    for line in path.read_text().splitlines():
        try:
            items.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return items


def append(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    items = load(path)
    if len(items) > MAX_ENTRIES:
        path.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items[-MAX_ENTRIES:]))


def words(query: str) -> frozenset[str]:
    return frozenset(re.findall(r"[a-z0-9]+", SITE.sub(" ", query.lower())))


def normalise(query: str) -> frozenset[str]:
    return words(query) - STOP


def jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


def decide(items: list[dict], session: str, tool: str, text: str) -> dict | None:
    """The prior entry this call duplicates, or None if it may run."""
    if tool == "WebFetch":
        for it in items:
            if it.get("kind") == "fetch" and it.get("session") == session and it.get("text") == text:
                return it
        return None
    raw = words(text)
    norm = raw - STOP
    if len(norm) < MIN_WORDS:
        return None
    already = {(it.get("prior_ts"), it.get("prior_text")) for it in items
               if it.get("kind") == "deny" and it.get("session") == session}
    best, best_j = None, 0.0
    for it in items:
        if it.get("kind") != "search" or (it.get("ts"), it.get("text")) in already:
            continue
        prior_raw = words(it.get("text", ""))
        if (raw - prior_raw) & ANGLE:
            continue
        j = jaccard(norm, prior_raw - STOP)
        bar = SAME_SESSION if it.get("session") == session else CROSS_SESSION
        if j >= bar and j > best_j:
            best, best_j = it, j
    return best


def deny_reason(prior: dict) -> str:
    date = time.strftime("%Y-%m-%d", time.localtime(prior.get("ts", 0)))
    return REASON.format(date=date, prior=prior.get("text", "")[:160])


def hook() -> int:
    if os.environ.get("AGENTMAXX_RESEARCH_LOG") == "0":
        return 0
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    tool = event.get("tool_name") or ""
    if event.get("hook_event_name") != "PreToolUse" or tool not in ("WebSearch", "WebFetch"):
        return 0
    inp = event.get("tool_input") or {}
    text = (inp.get("query") if tool == "WebSearch" else inp.get("url")) or ""
    text = " ".join(text.split())
    if not text:
        return 0
    session = event.get("session_id") or ""
    path = path_for(event.get("cwd") or os.getcwd())
    items = load(path)
    prior = decide(items, session, tool, text)
    now = time.time()
    if prior is not None:
        append(path, dict(kind="deny", ts=now, session=session, text=text,
                          prior_ts=prior.get("ts"), prior_text=prior.get("text")))
        reason = deny_reason(prior) if tool == "WebSearch" else (
            f"Already fetched this URL in this session (\"{text[:160]}\"); the content is in context. "
            "Re-run the same call if you really need it again.")
        json.dump({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                          "permissionDecisionReason": reason}}, sys.stdout)
        return 0
    append(path, dict(kind="search" if tool == "WebSearch" else "fetch", ts=now, session=session, text=text))
    return 0


def recent(cwd: str, n: int) -> str:
    items = [i for i in load(path_for(cwd)) if i.get("kind") in ("search", "fetch")][-n:]
    if not items:
        return "(no research logged for this repo)"
    lines = []
    for it in items:
        date = time.strftime("%Y-%m-%d", time.localtime(it.get("ts", 0)))
        tag = "search" if it.get("kind") == "search" else "fetch "
        lines.append(f"{date} {tag} {it.get('text', '')}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if not argv or argv[:1] == ["hook"]:
        return hook()
    if argv[:1] == ["recent"]:
        cwd = argv[1] if len(argv) > 1 and not argv[1].isdigit() else os.getcwd()
        n = int(argv[-1]) if len(argv) > 1 and argv[-1].isdigit() else 30
        print(recent(cwd, n))
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
