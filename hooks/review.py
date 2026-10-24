#!/usr/bin/env python3
"""Stop hook: a fresh-context review of this session's diff before the agent declares done.

The agent that wrote the code grades its own work badly (self-review without
an external signal doesn't help, Huang et al. 2024), but a reviewer that has
never seen the conversation does find missed requirements and wrong behaviour
(RETRACE; Anthropic's "fresh-context verifier" practice). So when the session
edited code, this hook hands the task statement and the uncommitted diff to a
separate `claude -p` process with read-only tools and asks for correctness and
requirement gaps only, as JSON. Non-empty list: block once with the gaps.
Empty list, reviewer failure, or timeout: let the stop through silently, so a
broken reviewer never traps the agent.

Fires at most once per session (like verify's block) and never when:
  - stop_hook_active (the agent is already answering a block),
  - AGENTMAXX_REVIEW=0,
  - the session is headless (`claude -p`: CLAUDE_CODE_ENTRYPOINT=sdk-cli, or the
    transcript's user records say entrypoint sdk-cli) -- the bench runs that way
    and the reviewer itself runs that way, so this is the recursion guard,
  - the session edited no code (same signal as verify.py's edited_this_session),
  - the diff is empty, or over REVIEW_MAX_LINES after dropping lockfiles and
    files with more than 400 changed lines (a reviewer can't hold more).

Reviewer model: AGENTMAXX_REVIEW_MODEL (default sonnet). Timeout: 150 s.
Raw reviewer output is kept under $AGENTMAXX_HOME/review/<session>.raw for
later measurement.
"""
from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(os.environ.get("AGENTMAXX_HOME", os.path.expanduser("~/.local/share/agentmaxx")), "review")
MODEL = os.environ.get("AGENTMAXX_REVIEW_MODEL", "sonnet")
TIMEOUT = int(os.environ.get("AGENTMAXX_REVIEW_TIMEOUT", "150"))
MAX_FILE_LINES = 400      # a file with more changed lines than this is dropped from the review
MAX_TOTAL_LINES = 600     # more than this in total and the review is skipped
TASK_CHARS = 1200
MAX_GAPS = 5
LOCKFILE = re.compile(
    r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|bun\.lockb?|Cargo\.lock|poetry\.lock|uv\.lock"
    r"|Pipfile\.lock|go\.sum|composer\.lock|Gemfile\.lock|flake\.lock|.*\.lock)$")
NOT_TYPED = ("<command-", "<local-command", "<system-reminder", "<task-notification", "[Request interrupted")
# Read-only tool surface for the reviewer; `claude -p --help` on 2.1.x documents --tools
# (built-in set) and --allowedTools (permission allowlist; `Bash(git diff:*)` is the prefix form).
TOOLS = "Read,Grep,Glob,Bash"
ALLOWED = "Read,Grep,Glob,Bash(git diff:*),Bash(git log:*),Bash(git show:*)"

PROMPT = """You are reviewing a code change with no prior knowledge of how it was made.

Step 1. Read the DIFF below and, from the diff alone, write down what problem it solves and what behaviour it changes. Do not look at the TASK yet.
Step 2. Now read the TASK (what the user asked for) and compare it with your reconstruction.
Step 3. Report ONLY correctness or requirement gaps:
  - wrong behaviour (the code does not do what it is meant to do, including edge cases the task names),
  - a requirement in the task that the diff does not meet,
  - a caller or test elsewhere in the repo that this change breaks (use Grep/Read to check callers),
  - a changed code path that no test exercises when the task or repo convention expects one.
Do NOT report style, naming, formatting, comments, documentation, performance that was not asked for, or nice-to-haves. Do not invent gaps: when the work is sound, the correct answer is an empty list, and an empty list is the expected answer for most sound changes.

Respond with JSON only, no prose before or after: a list of at most {max_gaps} objects
[{{"file": "<path>", "line": <int or null>, "gap": "<one sentence, concrete>"}}]
or [] when there are no gaps.

TASK:
{task}

DIFF:
{diff}
{closing}"""


def load_verify():
    spec = importlib.util.spec_from_file_location("agentmaxx_verify", os.path.join(HERE, "verify.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def headless(transcript_path: str) -> bool:
    """True for `claude -p` sessions (bench runs, and this hook's own reviewer)."""
    if os.environ.get("CLAUDE_CODE_ENTRYPOINT") == "sdk-cli":
        return True
    try:
        with open(transcript_path, errors="ignore") as fh:
            for line in fh:
                if '"user"' not in line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("type") != "user":
                    continue
                return r.get("entrypoint") == "sdk-cli" or r.get("promptSource") == "sdk"
    except OSError:
        pass
    return False


def task_statement(transcript_path: str, limit: int = TASK_CHARS) -> str:
    """The first prompt the user typed (same rules as evals/corrections.py prompts())."""
    try:
        with open(transcript_path, errors="ignore") as fh:
            for line in fh:
                if '"user"' not in line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if r.get("type") != "user" or r.get("isMeta") or r.get("isSidechain"):
                    continue
                content = (r.get("message") or {}).get("content")
                if isinstance(content, list):
                    if any(b.get("type") == "tool_result" for b in content if isinstance(b, dict)):
                        continue
                    content = "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
                if not isinstance(content, str) or not content.strip() or content.lstrip().startswith(NOT_TYPED):
                    continue
                text = content.strip()
                return text if len(text) <= limit else text[:limit].rstrip() + " [...]"
    except OSError:
        pass
    return ""


def _git(cwd: str, *args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                              errors="replace", timeout=15).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None


def _untracked_lines(cwd: str, path: str) -> int:
    try:
        with open(os.path.join(cwd, path), "rb") as fh:
            if b"\0" in fh.read(8000):
                return MAX_FILE_LINES + 1  # binary: never reviewable
            fh.seek(0)
            return sum(1 for _ in fh)
    except OSError:
        return MAX_FILE_LINES + 1


def collect_diff(cwd: str, max_file: int = MAX_FILE_LINES, max_total: int = MAX_TOTAL_LINES) -> str | None:
    """Staged + unstaged + untracked changes as one unified diff, minus lockfiles and
    files with more than max_file changed lines. None when nothing is reviewable
    or the total is over max_total lines."""
    numstat = _git(cwd, "diff", "HEAD", "--numstat", "--no-color", "--no-ext-diff")
    untracked = _git(cwd, "ls-files", "--others", "--exclude-standard")
    if numstat is None or untracked is None:
        return None
    tracked: list[str] = []
    total = 0
    for row in numstat.splitlines():
        parts = row.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        if added == "-" or LOCKFILE.search(path):
            continue  # binary or lockfile
        changed = int(added) + int(deleted)
        if changed == 0 or changed > max_file:
            continue
        tracked.append(path)
        total += changed
    new: list[str] = []
    for path in untracked.splitlines():
        if not path or LOCKFILE.search(path):
            continue
        n = _untracked_lines(cwd, path)
        if n == 0 or n > max_file:
            continue
        new.append(path)
        total += n
    if not tracked and not new:
        return None
    if total > max_total:
        return None
    parts = []
    if tracked:
        parts.append(_git(cwd, "diff", "HEAD", "--no-color", "--no-ext-diff", "--", *tracked) or "")
    for path in new:
        parts.append(_git(cwd, "diff", "--no-index", "--no-color", "--no-ext-diff", "--", "/dev/null", path) or "")
    diff = "\n".join(p for p in parts if p.strip())
    return diff or None


def parse_gaps(raw: str) -> list[dict] | None:
    """The reviewer's JSON list, dug out of whatever surrounds it. None when unparseable."""
    if not raw:
        return None
    text = raw.strip()
    # `--output-format json` wraps the answer in a result envelope.
    try:
        envelope = json.loads(text)
        if isinstance(envelope, dict) and "result" in envelope:
            text = str(envelope.get("result") or "").strip()
    except json.JSONDecodeError:
        pass
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
    candidates = [text]
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end > start:
        candidates.append(text[start:end + 1])
    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            data = data.get("gaps", data.get("result", []))
        if not isinstance(data, list):
            continue
        gaps = []
        for item in data:
            if not isinstance(item, dict):
                continue
            gap = str(item.get("gap") or item.get("issue") or item.get("description") or "").strip()
            if not gap:
                continue
            gaps.append({"file": str(item.get("file") or "?"), "line": item.get("line"), "gap": gap})
        return gaps[:MAX_GAPS]
    return None


def run_reviewer(prompt: str, cwd: str, timeout: int = TIMEOUT) -> str | None:
    claude = shutil.which("claude")
    if not claude:
        return None
    env = dict(os.environ, AGENTMAXX_REVIEW="0", AGENTMAXX_VERIFY="0")
    env.pop("CLAUDECODE", None)  # the CLI refuses to start nested inside another session
    cmd = [claude, "-p", "--model", MODEL, "--output-format", "json", "--no-session-persistence",
           "--tools", TOOLS, "--allowedTools", ALLOWED, "--permission-mode", "dontAsk", prompt]
    try:
        result = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True,
                                errors="replace", timeout=timeout, stdin=subprocess.DEVNULL)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout if result.returncode == 0 or result.stdout.strip() else None


def reason(gaps: list[dict]) -> str:
    lines = []
    for g in gaps:
        where = g["file"] if g.get("line") in (None, "", 0) else f"{g['file']}:{g['line']}"
        lines.append(f"- {where} {g['gap']}")
    n = len(gaps)
    return (f"Fresh-context review found {n} gap{'s' if n != 1 else ''}:\n" + "\n".join(lines)
            + "\nFix the real ones or say why each is not a gap, then finish.")


def state_path(session_id: str, suffix: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", session_id or "nosession")
    return os.path.join(STATE, safe + suffix)


def already_reviewed(session_id: str) -> bool:
    return os.path.exists(state_path(session_id, ".reviewed"))


def mark_reviewed(session_id: str, raw: str | None) -> None:
    try:
        os.makedirs(STATE, exist_ok=True)
        with open(state_path(session_id, ".reviewed"), "w") as fh:
            fh.write("1")
        if raw is not None:
            with open(state_path(session_id, ".raw"), "w") as fh:
                fh.write(raw)
    except OSError:
        pass


def decide(event: dict, run=run_reviewer) -> dict | None:
    """The hook's decision for one Stop event, or None to let the stop through."""
    if event.get("stop_hook_active") or os.environ.get("AGENTMAXX_REVIEW") == "0":
        return None
    transcript = event.get("transcript_path", "")
    sid = event.get("session_id", "")
    if headless(transcript) or already_reviewed(sid):
        return None
    if not load_verify().edited_this_session(transcript):
        return None
    cwd = event.get("cwd") or os.getcwd()
    diff = collect_diff(cwd)
    if diff is None:
        return None
    task = task_statement(transcript) or "(the user's request was not recorded; judge the diff on its own terms)"
    closing = (event.get("last_assistant_message") or "").strip()
    if closing:
        closing = ("\nTHE AGENT'S CLOSING MESSAGE (its own claim, not evidence; the diff wins when they disagree):\n"
                   + closing[:1000])
    prompt = PROMPT.format(max_gaps=MAX_GAPS, task=task, diff=diff, closing=closing)
    raw = run(prompt, cwd)
    mark_reviewed(sid, raw)
    gaps = parse_gaps(raw or "")
    if not gaps:
        return None
    return {"decision": "block", "reason": reason(gaps)}


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    out = decide(event)
    if out:
        print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
