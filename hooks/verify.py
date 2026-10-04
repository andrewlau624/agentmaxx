#!/usr/bin/env python3
"""Stop hook: before the agent declares done, run the project's tests.

Self-review without an external signal doesn't improve results (Huang et al.,
ICLR 2024); test feedback does (Reflexion). So this gate only fires when
the session edited files and a test command is known, and it blocks at most
once per stop: the second stop (stop_hook_active) always goes through, so
a pre-existing failure can't trap the agent in a loop.

Pre-existing failures don't count: at SessionStart a baseline run starts in
the background, and the gate blocks only on failures that baseline didn't
have. If the baseline isn't ready (or the runner's output can't be parsed
into test ids), any failure blocks, once.

Before the tests, a ratchet over the lines this session added: new skips
without a ticket, new lint/type suppressions, swallowed exceptions, vacuous
asserts, and deleted assertions in tests. Lines that already matched in the
uncommitted diff at SessionStart don't count, so legacy code never blocks.

A gate that couldn't run is not a pass: a timeout or a runner that was
already broken at SessionStart goes through, but says so to the user.

Test command, first match wins:
  1. $AGENTMAXX_VERIFY_CMD
  2. first line of .agentmaxx/verify in the repo
  3. autodetect: pytest / unittest / npm test / cargo test / go test
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
TIMEOUT = int(os.environ.get("AGENTMAXX_VERIFY_TIMEOUT", "120"))
TAIL_LINES = 40
STATE = os.path.join(os.environ.get("AGENTMAXX_HOME", os.path.expanduser("~/.local/share/agentmaxx")), "verify")
FAILED_ID = re.compile(
    r"^(?:FAIL|ERROR): (\S+ \(\S+\))"          # unittest
    r"|^(?:FAILED|ERROR) (\S+)"                   # pytest -q / -rf
    r"|^--- FAIL: (\S+)"                          # go test
    r"|^test (\S+) \.\.\. FAILED"                  # cargo test
    r"|^\s+[✕×] (.+?)(?: \(\d+ m?s\))?$",           # jest / vitest
    re.MULTILINE,
)

TICKET = re.compile(r"#\d+|\b[A-Z][A-Z0-9]+-\d+\b|https?://")
CHEATS = [
    ("skip without a ticket", re.compile(
        r"pytest\.mark\.(skip|xfail)|pytest\.(skip|xfail)\(|unittest\.skip|\.skipTest\(|@skip\b"
        r"|\b(it|test|describe)\.skip\(|\bx(it|describe|test)\(|\bt\.Skip(Now|f)?\(|#\[ignore\]"), True),
    # Blanket forms only: a suppression naming its rule (`noqa: E402`) is usually deliberate.
    ("blanket suppression", re.compile(
        r"#\s*noqa(?!:)|#\s*type:\s*ignore(?!\[)|eslint-disable(-next-line|-line)?\s*(\*/)?\s*$|@ts-(ignore|nocheck)"
        r"|nosemgrep\s*$|//\s*nolint\s*$|NOSONAR"), False),
    ("swallowed exception", re.compile(
        r"^\s*except\s*(\(?\s*(Base)?Exception\b[^:]*)?:\s*(pass|\.\.\.)\s*$|catch\s*(\(\w*\))?\s*\{\s*\}"), False),
    ("vacuous assert", re.compile(r"^\s*assert\s+True\b|self\.assertTrue\(True\)|expect\(true\)\.toBe\(true\)"), False),
]
ASSERTION = re.compile(r"^\s*(assert\b|self\.assert\w*\(|expect\(|t\.(Error|Fatal)|assert_eq!|assert!)")
# Patterns quoted in a string (fixtures, regexes, docs) aren't the real thing.
STRING_LITERAL = re.compile(r"""("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|`(?:\\.|[^`\\])*`)""")
CODE_FILE = re.compile(r"\.(py|pyi|js|jsx|ts|tsx|mjs|cjs|go|rs|java|kt|rb|php|cs|swift|c|cc|cpp|h|hpp)$")
TEST_FILE = re.compile(r"(^|/)(tests?/|test_[^/]*$|[^/]*_test\.\w+$|[^/]*\.(test|spec)\.\w+$)")


def diff_lines(cwd: str) -> tuple[list[tuple[str, int, str]], dict[str, int]] | None:
    """Added (file, line, text) in the uncommitted tree, untracked files included,
    plus the net count of assertion lines removed per test file."""
    try:
        diff = subprocess.run("git diff HEAD -U0 --no-color --no-ext-diff", shell=True, cwd=cwd,
                              capture_output=True, text=True, errors="replace", timeout=10)
        untracked = subprocess.run("git ls-files --others --exclude-standard -z", shell=True, cwd=cwd,
                                   capture_output=True, text=True, errors="replace", timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if diff.returncode != 0:
        return None
    added: list[tuple[str, int, str]] = []
    removed_asserts: dict[str, int] = {}
    old_path, path, line_no = "", "", 0
    for line in diff.stdout.splitlines():
        if line.startswith("--- "):
            old_path = line[6:] if line.startswith("--- a/") else ""
        elif line.startswith("+++ "):
            path = line[6:] if line.startswith("+++ b/") else ""
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            line_no = int(m.group(1)) if m else 0
        elif line.startswith("+") and path:
            added.append((path, line_no, line[1:]))
            if TEST_FILE.search(path) and CODE_FILE.search(path) and ASSERTION.search(line[1:]):
                removed_asserts[path] = removed_asserts.get(path, 0) - 1
            line_no += 1
        elif line.startswith("-") and TEST_FILE.search(path or old_path) and CODE_FILE.search(path or old_path) and ASSERTION.search(line[1:]):
            removed_asserts[path or old_path] = removed_asserts.get(path or old_path, 0) + 1
    for rel in filter(None, untracked.stdout.split("\0")):
        try:
            with open(os.path.join(cwd, rel), errors="replace") as fh:
                for i, text in enumerate(fh.read(200_000).splitlines(), 1):
                    added.append((rel, i, text))
        except (OSError, IsADirectoryError):
            continue
    return added, {k: v for k, v in removed_asserts.items() if v > 0}


def cheat_findings(cwd: str, baseline: set[str] | None = None) -> list[str] | None:
    """Ratchet findings on added lines, minus any that matched at SessionStart."""
    lines = diff_lines(cwd)
    if lines is None:
        return None
    added, removed_asserts = lines
    found = []
    prev = ("", 0, "")
    for path, no, text in added:
        if not CODE_FILE.search(path):
            continue
        if prev[0] == path and prev[1] == no - 1 and re.match(r"\s*except\b[^:]*:\s*$", prev[2]) and re.fullmatch(r"\s*(pass|\.\.\.)\s*", text):
            text = f"{prev[2].strip()} {text.strip()}"  # two-line `except:` / `pass`
        prev = (path, no, text)
        code = STRING_LITERAL.sub('""', text)
        for label, pattern, ticket_ok in CHEATS:
            if pattern.search(code) and not (ticket_ok and TICKET.search(text)):
                key = f"{path}: {label}: {text.strip()[:120]}"  # cheat_keys() form
                if baseline is None or key not in baseline:
                    found.append(f"{path}:{no} {label}: {text.strip()[:120]}")
                break
    for path, n in removed_asserts.items():
        key = f"{path}: removed {n} assertion(s)"
        if baseline is None or key not in baseline:
            found.append(key)
    return found


def cheat_keys(findings: list[str]) -> list[str]:
    """Line-number-free keys, so a baseline still matches after lines shift."""
    return [re.sub(r"^([^:]+):\d+ ", r"\1: ", f) for f in findings]


def edited_this_session(transcript_path: str) -> bool:
    try:
        with open(transcript_path, errors="ignore") as fh:
            for line in fh:
                if '"tool_use"' not in line:
                    continue
                for block in (json.loads(line).get("message") or {}).get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = block.get("name", "")
                        command = (block.get("input") or {}).get("command", "")
                        if name in EDIT_TOOLS or re.search(r"\bsed -i|\bpatch\b|>\s*\S+\.(py|ts|js|go|rs)\b", command):
                            return True
    except (OSError, json.JSONDecodeError):
        return False
    return False


def detect(cwd: str) -> str | None:
    if os.environ.get("AGENTMAXX_VERIFY_CMD"):
        return os.environ["AGENTMAXX_VERIFY_CMD"]
    pinned = os.path.join(cwd, ".agentmaxx", "verify")
    if os.path.isfile(pinned):
        first = open(pinned).readline().strip()
        return first or None
    has = lambda *p: os.path.exists(os.path.join(cwd, *p))
    if has("package.json"):
        try:
            scripts = json.load(open(os.path.join(cwd, "package.json"))).get("scripts", {})
        except (OSError, json.JSONDecodeError):
            scripts = {}
        test = scripts.get("test", "")
        if test and "no test specified" not in test:
            return "npm test --silent"
    if has("Cargo.toml") and shutil.which("cargo"):
        return "cargo test -q"
    if has("go.mod") and shutil.which("go"):
        return "go test ./..."
    if has("tests") or has("test"):
        start = "tests" if has("tests") else "test"
        configured = has("pytest.ini") or has("pyproject.toml") and "pytest" in open(os.path.join(cwd, "pyproject.toml")).read()
        if configured or has("conftest.py"):
            return "python3 -m pytest -q -x"
        if has(start, "conftest.py"):
            return f"python3 -m pytest -q -x {start}"  # no testpaths config: don't collect stray *_test.py elsewhere
        if any(f.startswith("test") and f.endswith(".py") for f in os.listdir(os.path.join(cwd, start))):
            # -t . needs the start dir to be a package; without __init__.py, discovery imports it as top level.
            top = " -t ." if has(start, "__init__.py") else ""
            return f"python3 -m unittest discover -s {start}{top} -q"
    return None


def failing_ids(output: str) -> set[str]:
    return {next(g for g in m.groups() if g) for m in FAILED_ID.finditer(output)}


def run_tests(command: str, cwd: str) -> tuple[int, str] | None:
    try:
        proc = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return None
    return proc.returncode, proc.stdout + proc.stderr


def tree_fingerprint(cwd: str) -> str | None:
    """Hash of the working tree's changes, so an unchanged tree isn't re-tested every stop."""
    try:
        diff = subprocess.run("git diff HEAD; git ls-files --others --exclude-standard", shell=True, cwd=cwd,
                              capture_output=True, text=True, errors="replace", timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    # Test runs create caches; counting them would make every stop look changed.
    kept = [line for line in diff.splitlines() if not re.search(r"__pycache__|\.pyc$|\.pytest_cache|node_modules/|\.cache/", line)]
    return hashlib.sha1("\n".join(kept).encode()).hexdigest()


def baseline_path(session_id: str) -> str:
    return os.path.join(STATE, re.sub(r"[^\w-]", "", session_id or "none") + ".json")


def start_baseline(event: dict) -> int:
    """SessionStart: record which tests already fail, without blocking startup."""
    cwd = event.get("cwd") or os.getcwd()
    command = detect(cwd)
    if not command or os.environ.get("AGENTMAXX_VERIFY") == "0" or event.get("source") not in (None, "startup", "clear"):
        return 0
    os.makedirs(STATE, exist_ok=True)
    existing = cheat_findings(cwd)
    if existing is not None:
        with open(baseline_path(event.get("session_id", "")) + ".ratchet", "w") as fh:
            json.dump(cheat_keys(existing), fh)
    subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "baseline-worker", baseline_path(event.get("session_id", "")), cwd, command],
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    return 0


def baseline_worker(path: str, cwd: str, command: str) -> int:
    result = run_tests(command, cwd)
    if result is not None:
        code, output = result
        with open(path, "w") as fh:
            json.dump({"code": code, "failing": sorted(failing_ids(output))}, fh)
    return 0


def main() -> int:
    if sys.argv[1:2] == ["baseline-worker"]:
        return baseline_worker(*sys.argv[2:5])
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if event.get("hook_event_name") == "SessionStart":
        return start_baseline(event)
    if event.get("stop_hook_active") or os.environ.get("AGENTMAXX_VERIFY") == "0":
        return 0
    cwd = event.get("cwd") or os.getcwd()
    if not edited_this_session(event.get("transcript_path", "")):
        return 0
    command = detect(cwd)
    sid = event.get("session_id", "")
    fingerprint = tree_fingerprint(cwd)
    seen_path = baseline_path(sid) + ".verified"
    try:
        if fingerprint and open(seen_path).read() == fingerprint:
            return 0  # nothing changed since the last stop we verified
    except OSError:
        pass
    try:
        with open(baseline_path(sid) + ".ratchet") as fh:
            ratchet_base: set[str] | None = set(json.load(fh))
    except (OSError, json.JSONDecodeError):
        ratchet_base = None
    cheats = cheat_findings(cwd, ratchet_base) or []
    result = run_tests(command, cwd) if command else None
    if fingerprint:
        os.makedirs(STATE, exist_ok=True)
        with open(seen_path, "w") as fh:
            fh.write(fingerprint)
    problems, notices = [], []
    if cheats:
        problems.append(
            "agentmaxx verify: your edits add patterns that make checks pass without fixing anything:\n"
            + "\n".join(f"  - {c}" for c in cheats[:15])
            + "\nRemove them and fix the cause. If one is genuinely right (e.g. a test that was wrong), "
            "keep it and say why in your final answer."
        )
    if command and result is None:
        notices.append(f"agentmaxx verify: `{command}` timed out after {TIMEOUT}s; this stop is unverified.")
    elif result is not None and result[0] != 0:
        test_problem, notice = judge_failure(command, result, sid)
        if test_problem:
            problems.append(test_problem)
        if notice:
            notices.append(notice)
    out: dict = {}
    if problems:
        out = {"decision": "block", "reason": "\n\n".join(problems)}
    if notices:
        out["systemMessage"] = " ".join(notices)
    if out:
        json.dump(out, sys.stdout)
    return 0


def judge_failure(command: str, result: tuple[int, str], sid: str) -> tuple[str | None, str | None]:
    """(block reason, user notice) for a failing test run, given the SessionStart baseline."""
    code, output = result
    now = failing_ids(output)
    try:
        with open(baseline_path(sid)) as fh:
            before = json.load(fh)
    except (OSError, json.JSONDecodeError):
        before = None
    if before is not None and now and before["failing"] and now <= set(before["failing"]):
        return None, None  # only failures that were already there before this session
    if before is not None and not now and not before["failing"] and before.get("code") == code:
        return None, f"agentmaxx verify: `{command}` was already failing to run before this session (exit {code}); this stop is unverified."
    new = sorted(now - set(before["failing"])) if before and now else []
    tail = "\n".join(output.strip().splitlines()[-TAIL_LINES:])
    return (
        f"agentmaxx verify: `{command}` fails after your edits (exit {code})"
        + (f"; newly failing: {', '.join(new[:10])}" if new else "")
        + ". Fix it if your change caused it; if it's unrelated and pre-existing, say so in your final answer."
        + f"\n\n{tail}"
    ), None


if __name__ == "__main__":
    sys.exit(main())
