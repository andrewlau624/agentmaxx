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
        if has("pytest.ini") or has("conftest.py") or has("pyproject.toml") and "pytest" in open(os.path.join(cwd, "pyproject.toml")).read():
            return "python3 -m pytest -q -x"
        if any(f.startswith("test") and f.endswith(".py") for d in ("tests", "test") if has(d) for f in os.listdir(os.path.join(cwd, d))):
            start = "tests" if has("tests") else "test"
            return f"python3 -m unittest discover -s {start} -t . -q"
    return None


def failing_ids(output: str) -> set[str]:
    return {next(g for g in m.groups() if g) for m in FAILED_ID.finditer(output)}


def run_tests(command: str, cwd: str) -> tuple[int, str] | None:
    try:
        proc = subprocess.run(command, shell=True, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        return None
    return proc.returncode, proc.stdout + proc.stderr


def tree_fingerprint(cwd: str) -> str | None:
    """Hash of the working tree's changes, so an unchanged tree isn't re-tested every stop."""
    try:
        diff = subprocess.run("git diff HEAD; git ls-files --others --exclude-standard", shell=True, cwd=cwd,
                              capture_output=True, text=True, timeout=10).stdout
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
    if not command:
        return 0
    fingerprint = tree_fingerprint(cwd)
    seen_path = baseline_path(event.get("session_id", "")) + ".verified"
    try:
        if fingerprint and open(seen_path).read() == fingerprint:
            return 0  # nothing changed since the last stop we verified
    except OSError:
        pass
    result = run_tests(command, cwd)
    if fingerprint:
        os.makedirs(STATE, exist_ok=True)
        with open(seen_path, "w") as fh:
            fh.write(fingerprint)
    if result is None or result[0] == 0:
        return 0
    code, output = result
    now = failing_ids(output)
    try:
        with open(baseline_path(event.get("session_id", ""))) as fh:
            before = json.load(fh)
    except (OSError, json.JSONDecodeError):
        before = None
    if before is not None and now and before["failing"] and now <= set(before["failing"]):
        return 0  # only failures that were already there before this session
    new = sorted(now - set(before["failing"])) if before and now else []
    tail = "\n".join(output.strip().splitlines()[-TAIL_LINES:])
    reason = (
        f"agentmaxx verify: `{command}` fails after your edits (exit {code})"
        + (f"; newly failing: {', '.join(new[:10])}" if new else "")
        + ". Fix it if your change caused it; if it's unrelated and pre-existing, say so in your final answer."
        + f"\n\n{tail}"
    )
    json.dump({"decision": "block", "reason": reason}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
