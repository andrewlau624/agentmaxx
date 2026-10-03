#!/usr/bin/env python3
"""PostToolUse hook: shrink large Bash output before it enters context.

Every byte of a tool result is re-read on every later turn, so a 100KB test
log costs 100KB x remaining turns. This keeps what the model acts on (errors,
failures, tracebacks, summary lines, head and tail), folds runs of
near-identical lines into one line with a count, and saves the full output
to a file the model can grep instead of re-running the command.

Output under THRESHOLD chars passes through untouched: squeezing small
outputs saves little and risks the re-run loop that makes naive compressors
cost more than they save.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import tempfile

THRESHOLD = int(os.environ.get("AGENTMAXX_SQUEEZE_THRESHOLD", "8000"))
BUDGET = int(os.environ.get("AGENTMAXX_SQUEEZE_BUDGET", "6000"))
HEAD, TAIL = 15, 40

SIGNAL = re.compile(
    r"error|exception|traceback|fail|panic|fatal|assert|warning: unused|"
    r"^\s*File \"|^\s+at |^E\s|-->|\bFAILED\b|\bpassed\b|\bfailed\b|^Ran \d+|^OK\b",
    re.IGNORECASE,
)
NORMALIZE = re.compile(r"0x[0-9a-f]+|\d+(\.\d+)?|'[^']*'|\"[^\"]*\"", re.IGNORECASE)


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


def squeeze(text: str, spill_path: str | None) -> str:
    lines = fold(text.splitlines())
    if len("\n".join(lines)) <= BUDGET:
        body = lines
    else:
        keep = set(range(min(HEAD, len(lines)))) | set(range(max(0, len(lines) - TAIL), len(lines)))
        for n, line in enumerate(lines):
            if SIGNAL.search(line):
                keep.update(range(max(0, n - 2), min(len(lines), n + 3)))
        body, last, used = [], -1, 0
        for n in sorted(keep):
            if used > BUDGET:
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


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if event.get("tool_name") != "Bash":
        return 0
    response = event.get("tool_response")
    if not isinstance(response, dict):
        return 0
    changed = False
    for key in ("stdout", "stderr"):
        text = response.get(key)
        if isinstance(text, str) and len(text) > THRESHOLD:
            response[key] = squeeze(text, spill(text))
            changed = True
    if changed:
        json.dump({"hookSpecificOutput": {"hookEventName": "PostToolUse", "updatedToolOutput": response}}, sys.stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main())
