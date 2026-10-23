#!/usr/bin/env python3
"""PostToolUse hook: shrink large Bash output before it enters context.

Every byte of a tool result is re-read on every later turn, so a 100KB test
log costs 100KB x remaining turns. This keeps what the model acts on (errors,
failures, tracebacks, summary lines, head and tail), folds runs of
near-identical lines into one line with a count, and saves the full output
to a file the model can grep instead of re-running the command.

Two thresholds, chosen from what the command was (replay over 6,207 real
outputs, evals/squeeze_replay.py):

* Noisy commands (test runners, package managers, builds, git status/log,
  ls/find/tree, docker, make) squeeze above NOISY_THRESHOLD. Nothing in the
  middle of a pytest log or an npm install is worth re-reading for 100 turns.
* Everything else (sed/cat/grep dumps, python heredocs, curl, unknown
  commands) is content the model asked to see; it squeezes only above
  THRESHOLD, so the agent isn't pushed into re-running the command.

Before either threshold, lossless-ish filters drop known filler (ANSI codes,
pytest progress dots, pip/npm download chatter, git hint lines, diff index
lines, ls -l permission columns) and secret-looking values are redacted.

With AGENTMAXX_SQUEEZE_ROUTER=1, outputs that parse as JSON are routed through
tools/better-compress instead (headroom when installed, else a vendored JSON
crusher); everything else keeps the path below.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import sys
import tempfile

THRESHOLD = int(os.environ.get("AGENTMAXX_SQUEEZE_THRESHOLD", "8000"))
BUDGET = int(os.environ.get("AGENTMAXX_SQUEEZE_BUDGET", "6000"))
NOISY_THRESHOLD = int(os.environ.get("AGENTMAXX_SQUEEZE_NOISY_THRESHOLD", "3000"))
NOISY_BUDGET = int(os.environ.get("AGENTMAXX_SQUEEZE_NOISY_BUDGET", "2000"))
HEAD, TAIL = 15, 40

SIGNAL = re.compile(
    r"error|exception|traceback|fail|panic|fatal|assert|warning: unused|"
    r"^\s*File \"|^\s+at |^E\s|-->|\bFAILED\b|\bpassed\b|\bfailed\b|^Ran \d+|^OK\b",
    re.IGNORECASE,
)
NORMALIZE = re.compile(r"0x[0-9a-f]+|\d+(\.\d+)?|'[^']*'|\"[^\"]*\"", re.IGNORECASE)
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")

# Commands whose output is mostly chatter around a verdict. Anything not listed
# is treated as content (sed, cat, grep, python heredocs, curl, ssh, unknown).
NOISY = {
    "pytest", "unittest", "jest", "vitest", "mocha", "tox", "nox",
    "pip", "pip3", "npm", "pnpm", "yarn", "bun", "cargo", "go", "mvn", "gradle", "brew", "apt", "apt-get",
    "make", "cmake", "ninja", "tsc", "webpack", "vite", "esbuild", "docker", "docker-compose", "kubectl",
    "ls", "find", "tree", "du", "wc", "ps", "lsof", "mkdir", "cp", "mv", "rm", "touch", "chmod",
    "pre-commit", "ruff", "flake8", "pylint", "mypy", "eslint", "prettier", "black", "isort",
}
NOISY_GIT = {"status", "log", "fetch", "pull", "push", "clone", "add", "commit", "checkout", "switch", "stash", "branch", "rebase", "merge"}
NOISY_PY_MODULES = {"pytest", "unittest", "pip", "build", "ruff", "mypy", "flake8", "tox", "nox"}
WRAPPERS = {"timeout", "sudo", "env", "nice", "time", "command", "exec", "nohup", "caffeinate", "uv", "npx", "bunx", "poetry", "pipenv", "hatch"}
FILTERS = {"head", "tail", "grep", "rg", "sort", "uniq", "cut", "wc", "tr", "tee", "awk", "sed", "xargs", "column", "less", "cat"}

REDACT = [
    (re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "[redacted:aws-key]"),
    (re.compile(r"\b(?:ghp|gho|ghs|ghr|ghu)_[A-Za-z0-9]{36,}\b|\bgithub_pat_[A-Za-z0-9_]{22,}\b"), "[redacted:github-token]"),
    (re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{20,}\b"), "[redacted:slack-token]"),
    (re.compile(r"\bsk-(?:ant-|proj-|live-|test-)[A-Za-z0-9_-]{20,}\b"), "[redacted:api-key]"),
    (re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b"), "[redacted:google-key]"),
    (re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"), "[redacted:gitlab-token]"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "[redacted:jwt]"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[redacted:private-key]"),
    (re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._~+/=-]{16,}"), r"\1[redacted:bearer]"),
    (re.compile(r"(://[^/\s:@]+:)[^@\s/]{6,}(@)"), r"\1[redacted]\2"),
]

LS_LONG = re.compile(r"^([-dlbcps])[-rwxsStT]{9}[@+.]?\s+\d+\s+\S+\s+\S+\s+(\d+)\s+(\w{3}\s+\d{1,2}\s+[\d:]+)\s+(.+)$")
DROP_ALWAYS = re.compile(
    r"^\s*(?:[.FEsxX]+\s*(?:\[\s*\d+%\])?|"                      # pytest progress
    r"(?:Collecting|Downloading|Using cached|Requirement already satisfied|Preparing metadata|Installing collected packages|Attempting uninstall|Uninstalling|Successfully uninstalled|Resolved \d+ packages|Prepared \d+ packages|Audited \d+ packages|Building wheels|Created wheel|Stored in directory)\b.*|"
    r"(?:npm (?:warn|WARN) (?:deprecated|cleanup|config).*)|"
    r"(?:[━█▓▒░]{5,}.*|.*\d{1,3}%\s*[━█▓▒░|]{3,}.*)|"              # progress bars
    r"\(use \"git [^\"]*\"[^)]*\)|"                                 # git status hints
    r"index [0-9a-f]{6,}\.\.[0-9a-f]{6,}(?: [0-7]{6})?|"           # diff index lines
    r"(?:new|deleted) file mode [0-7]{6}|(?:old|new) mode [0-7]{6}|"
    r"(?:cachedir|rootdir|configfile|plugins|platform [a-z]+ -- Python .*pytest-\d.*|collected \d+ items?|collecting \.\.\.)\s*:?.*|"
    r"total \d+)\s*$"
)


def _shape(line: str) -> str:
    return NORMALIZE.sub("#", line.strip())


def fold(lines: list[str], max_period: int = 4) -> list[str]:
    """Collapse repeating blocks of 1..max_period lines with the same shape.

    Interleaved logs (warning, source line, debug line, repeat) repeat as a
    block, not line by line, so periods above 1 matter in practice.
    """
    shapes = [_shape(line) for line in lines]
    out: list[str] = []
    i = 0
    while i < len(lines):
        best_p, best_reps = 1, 1
        for p in range(1, max_period + 1):
            reps = 1
            while shapes[i + reps * p:i + (reps + 1) * p] == shapes[i:i + p] and i + (reps + 1) * p <= len(lines):
                reps += 1
            if reps >= 3 and reps * p > best_reps * best_p:
                best_p, best_reps = p, reps
        if best_reps >= 3:
            out.extend(lines[i:i + best_p])
            out.append(f"[... block above repeated {best_reps - 1} more times with different numbers/strings ...]")
            last = i + (best_reps - 1) * best_p
            out.extend(lines[last:last + best_p])
            i += best_reps * best_p
        else:
            out.append(lines[i])
            i += 1
    return out


def simple_commands(command: str) -> list[list[str]]:
    """Split a shell command line into argv-like word lists, one per simple command.

    Good enough for classification: heredoc bodies and quoted strings only add
    words that never match a known command name.
    """
    out = []
    piped = False
    for part in re.split(r"(\|\||&&|;|\||\n)", command):
        if part in ("||", "&&", ";", "|", "\n"):
            piped = part == "|"
            continue
        words = part.strip().split()
        while words:
            w = words[0]
            if w in ("cd", "timeout") or (w in ("uv", "poetry", "pipenv", "hatch") and words[1:2] == ["run"]):
                words = words[2:]
            elif re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", w) or w in WRAPPERS or w.startswith("-"):
                words = words[1:]
            else:
                break
        if words:
            out.append(["|"] + words if piped else words)
    return out


def is_noisy(command: str) -> bool:
    """True when every producing command in the line is a known noisy command."""
    producers = []
    for words in simple_commands(command):
        piped, words = words[0] == "|", words[1:] if words[0] == "|" else words
        name = os.path.basename(words[0]).lower()
        if piped and name in FILTERS:
            continue  # `| head`, `| grep` filter a producer already seen
        producers.append((name, words))
    if not producers:
        return False
    for name, words in producers:
        if name in NOISY:
            continue
        if name == "git" and len(words) > 1 and words[1] in NOISY_GIT:
            continue
        if name.startswith("python") and len(words) > 2 and words[1] == "-m" and words[2] in NOISY_PY_MODULES:
            continue
        return False
    return True


def filter_lines(lines: list[str], command: str) -> list[str]:
    """Drop filler the model never acts on. Keeps every line that could carry a verdict."""
    out: list[str] = []
    ls_long = sum(1 for l in lines if LS_LONG.match(l)) >= 3
    blank_run = 0
    for line in lines:
        line = ANSI.sub("", line).rstrip()
        if not line:
            blank_run += 1
            if blank_run > 1:
                continue
        else:
            blank_run = 0
        if DROP_ALWAYS.match(line) and not SIGNAL.search(line):
            continue
        if ls_long and (m := LS_LONG.match(line)):
            kind, size, date, name = m.groups()
            line = f"{'d' if kind == 'd' else ' '}{int(size):>9} {date} {name}"
        out.append(line)
    while out and not out[-1]:
        out.pop()
    return out


def redact(text: str) -> tuple[str, int]:
    count = 0
    for pattern, repl in REDACT:
        text, n = pattern.subn(repl, text)
        count += n
    return text, count


def squeeze(text: str, spill_path: str | None, budget: int = BUDGET, command: str = "") -> str:
    lines = fold(filter_lines(text.splitlines(), command))
    if len("\n".join(lines)) <= budget:
        body = lines
    else:
        # Verdict lines first (errors, failures, summaries, with two lines of context), up to twice the
        # budget; head and tail fill whatever is left. A noisy log with 40 failures keeps the failures.
        keep, used = set(), 0
        for n, line in enumerate(lines):
            if SIGNAL.search(line) and used < 2 * budget:
                ctx = range(max(0, n - 2), min(len(lines), n + 3))
                used += sum(len(lines[k]) + 1 for k in ctx if k not in keep)
                keep.update(ctx)
        keep |= set(range(min(HEAD, len(lines)))) | set(range(max(0, len(lines) - TAIL), len(lines)))
        budget = max(budget, used)
        body, last, used = [], -1, 0
        for n in sorted(keep):
            if used > budget:
                body.append("[... budget reached ...]")
                break
            if n != last + 1:
                body.append(f"[... {n - last - 1} lines omitted ...]")
            body.append(lines[n])
            used += len(lines[n]) + 1
            last = n
    note = f"[agentmaxx: output squeezed from {len(text):,} chars"
    if spill_path:
        note += f"; full output saved to {spill_path} (grep it instead of re-running)"
    return "\n".join(body) + "\n" + note + "]"


def spill(text: str) -> str | None:
    try:
        root = os.path.join(tempfile.gettempdir(), "agentmaxx-out")
        os.makedirs(root, exist_ok=True)
        path = os.path.join(root, hashlib.sha1(text.encode()).hexdigest()[:12] + ".log")
        with open(path, "w") as fh:
            fh.write(text)
        return path
    except OSError:
        return None


def _try_router(text: str, command: str, budget: int) -> str | None:
    """Route JSON outputs through better-compress. None on any failure."""
    if text.lstrip()[:1] not in ("{", "["):
        return None
    try:
        json.loads(text)
    except ValueError:
        return None
    try:
        tool = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "tools", "better-compress", "better_compress.py")
        spec = importlib.util.spec_from_file_location("better_compress_hook", tool)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(mod)
        out, info = mod.compress_text(text, command=command, budget=budget)
    except (OSError, ImportError, AttributeError, AssertionError, ValueError, TypeError) as exc:
        # A hook must never fail the tool call, but a missing or broken backend should be visible.
        print(f"[agentmaxx squeeze] router unavailable, using built-in squeeze: {exc}", file=sys.stderr)
        return None
    if info.get("backend") not in ("passthrough", "none") and len(out) < len(text):
        return out
    return None


def process(text: str, command: str, write_spill=spill) -> str | None:
    """Return the replacement for one output stream, or None when it should pass through untouched."""
    text, redacted = redact(text)
    noisy = is_noisy(command)
    threshold, budget = (NOISY_THRESHOLD, NOISY_BUDGET) if noisy else (THRESHOLD, BUDGET)
    if len(text) > threshold:
        routed = _try_router(text, command, budget) if os.environ.get("AGENTMAXX_SQUEEZE_ROUTER") == "1" else None
        out = routed if routed is not None else squeeze(text, write_spill(text), budget, command)
    elif noisy and len(text) > 500:
        out = "\n".join(filter_lines(text.splitlines(), command))
        if len(out) > len(text) - 200:
            out = text  # not worth a rewrite
    else:
        out = text
    if redacted:
        out += f"\n[agentmaxx: {redacted} secret-looking value{'s' if redacted > 1 else ''} redacted]"
    return out if out != text or redacted else None


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "--text":
        # opencode plugin mode: {"command": ..., "output": ...} in, {"output": ...} out.
        try:
            event = json.load(sys.stdin)
        except json.JSONDecodeError:
            return 0
        out = process(event.get("output") or "", event.get("command") or "")
        json.dump({"output": out} if out is not None else {}, sys.stdout)
        return 0
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    response = event.get("tool_response")
    if not isinstance(response, dict):
        return 0
    command = (event.get("tool_input") or {}).get("command", "")
    changed = False
    for key in ("stdout", "stderr"):
        text = response.get(key)
        if isinstance(text, str) and text:
            out = process(text, command)
            if out is not None:
                response[key] = out
                changed = True
    if changed:
        json.dump({"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": response}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
