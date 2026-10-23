#!/usr/bin/env python3
"""Route text to the best compressor for its shape, with a stdlib-only fallback.

JSON crushes best with headroom's table-izer; logs, diffs, and prose are
handled by the vendored builtin (which reuses hooks/squeeze.py when it can);
`--run` executes shell commands under lowfat when it is installed. Every
backend is optional: unknown shapes, missing dependencies, and backend
failures all degrade to the builtin, and the builtin degrades to head+tail.
Never returns empty, never expands its input.

    better_compress.py [--file PATH | stdin] [--command CMD] [--budget N]
                       [--backend auto|headroom|builtin] [--json]
    better_compress.py [--budget N] [--timeout N] [--json] --run COMMAND [ARGS ...]
                       (--run must come last; everything after it is the command)

`make compress-deps` installs the optional backends (headroom into
~/.agentmaxx/.venv, lowfat into ~/.local/bin).
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BUDGET = 6000
RUN_TIMEOUT = 120

# Commands lowfat ships bundled filters for (lowfat info).
LOWFAT_CMDS = {"git", "docker", "ls", "find", "grep", "tree"}

LOGLINE = re.compile(r"^\s*\[?(?:\d{4}[-/]\d{2}[-/]\d{2}|\d{2}:\d{2}(?::\d{2})?|"
                     r"(?:DEBUG|INFO|WARN(?:ING)?|ERROR|FATAL|TRACE))\b")


def _agentmaxx_root() -> Path | None:
    here = Path(__file__).resolve()
    for root in (here.parent.parent.parent, Path.home() / ".agentmaxx"):
        if (root / "hooks" / "squeeze.py").is_file():
            return root
    return None


_squeeze = None
_squeeze_tried = False


def _load_squeeze():
    """hooks/squeeze.py as a module, or None when this tool travels alone."""
    global _squeeze, _squeeze_tried
    if _squeeze_tried:
        return _squeeze
    _squeeze_tried = True
    root = _agentmaxx_root()
    if root is None:
        return None
    try:
        spec = importlib.util.spec_from_file_location("squeeze_impl", root / "hooks" / "squeeze.py")
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(mod)
        _squeeze = mod
    except Exception:
        _squeeze = None
    return _squeeze


def classify(text: str, command: str = "") -> str:
    """json, diff, log, or text. Cheap checks first; JSON parse last."""
    stripped = text.lstrip()
    if stripped[:1] in ("{", "["):
        try:
            json.loads(text)
            return "json"
        except ValueError:
            pass
    lines = text.splitlines()
    head = lines[:200]
    if sum(1 for l in head if l.startswith(("diff --git", "@@", "+++ ", "--- "))) >= 2:
        return "diff"
    if command:
        sq = _load_squeeze()
        if sq is not None and sq.is_noisy(command):
            return "log"
    if len(lines) >= 10 and sum(1 for l in head if LOGLINE.match(l)) / min(len(lines), 200) > 0.3:
        return "log"
    return "text"


def _short(value: str, limit: int = 120) -> str:
    return value if len(value) <= limit else value[:limit] + "..."


def _scalar_type(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "num"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return f"list[{len(value)}]"
    if isinstance(value, dict):
        return f"dict[{len(value)}]"
    return "?"


def _crush_rows(rows: list[dict], budget: int) -> str:
    sample = rows[:300]
    keys = list(dict.fromkeys(k for r in sample for k in r))
    keys = [k for k in keys if any(r.get(k) is not None for r in sample)]
    if not keys:
        return f"[{len(rows)} empty objects]"
    types = {}
    for k in keys:
        first = next((r[k] for r in sample if r.get(k) is not None), None)
        types[k] = _scalar_type(first)
    header = f"[{len(rows)} rows]{{{','.join(f'{k}:{types[k]}' for k in keys)}}}"
    body: list[str] = []
    for r in rows:
        slim = {k: (_short(r[k]) if isinstance(r.get(k), str) else r.get(k)) for k in keys}
        body.append(json.dumps(slim, separators=(",", ":"), default=str))
    lines = _fit_rows(body, budget - len(header) - 1)
    return header + "\n" + "\n".join(lines)


def _fit_rows(rows: list[str], budget: int) -> list[str]:
    """Head rows plus a few tail rows, so truncation keeps both ends."""
    out, used, tail_n = [], 0, min(5, len(rows))
    for i, row in enumerate(rows):
        if used + len(row) + 1 > budget and i < len(rows) - tail_n:
            rest = len(rows) - i - tail_n
            out.append(f"[... {rest} rows omitted ...]")
            out.extend(rows[len(rows) - tail_n:])
            return out
        out.append(row)
        used += len(row) + 1
    return out


def _summarize(value, depth: int = 0):
    if isinstance(value, str):
        return _short(value, 200)
    if isinstance(value, list):
        if not value or depth > 1:
            return f"<list[{len(value)}]>"
        return f"<list[{len(value)}]> first: {_short(json.dumps(value[0], default=str), 120)}"
    if isinstance(value, dict):
        ks = list(value)[:6]
        more = f"+{len(value) - 6} more" if len(value) > 6 else ""
        return f"<dict[{len(value)}: {','.join(ks)}{more}]>"
    return json.dumps(value, default=str)


def crush_json_text(text: str, budget: int) -> str | None:
    """SmartCrusher-style table-izing with stdlib only. None when not JSON."""
    try:
        obj = json.loads(text)
    except ValueError:
        return None
    if isinstance(obj, list) and obj and all(isinstance(r, dict) for r in obj):
        return _crush_rows(obj, budget)
    compact = json.dumps(obj, separators=(",", ":"), default=str)
    if len(compact) <= budget:
        return compact
    if isinstance(obj, dict):
        lines = [f"{k}: {_summarize(v)}" for k, v in obj.items()]
    elif isinstance(obj, list):
        lines = [f"[{i}] {_summarize(v)}" for i, v in enumerate(obj)]
    else:
        return compact[:budget] + f"\n[... {len(compact) - budget} chars omitted ...]"
    return "\n".join(_fit_rows(lines, budget))


def _minimal_cut(text: str, budget: int) -> str:
    lines = text.splitlines()
    if len(text) <= budget:
        return text
    head, tail = lines[:15], lines[-25:]
    omitted = len(lines) - len(head) - len(tail)
    return "\n".join(head + [f"[... {omitted} lines omitted ...]"] + tail)


def spill_text(text: str) -> str | None:
    sq = _load_squeeze()
    if sq is not None:
        return sq.spill(text)
    try:
        root = os.path.join(tempfile.gettempdir(), "agentmaxx-out")
        os.makedirs(root, exist_ok=True)
        import hashlib
        path = os.path.join(root, hashlib.sha1(text.encode()).hexdigest()[:12] + ".log")
        with open(path, "w") as fh:
            fh.write(text)
        return path
    except OSError:
        return None


def builtin_compress(text: str, kind: str, command: str, budget: int, spill_path: str | None) -> str:
    if kind == "json":
        crushed = crush_json_text(text, budget)
        if crushed is not None:
            return crushed
    sq = _load_squeeze()
    if sq is not None:
        return sq.squeeze(text, spill_path, budget, command)
    return _minimal_cut(text, budget)


_headroom = None
_headroom_tried = False


def load_headroom():
    """The headroom package: plain import, else the agentmaxx-managed venv."""
    global _headroom, _headroom_tried
    if _headroom_tried:
        return _headroom
    _headroom_tried = True
    with contextlib.redirect_stderr(io.StringIO()):
        try:
            import headroom as hr
            _headroom = hr
            return hr
        except ImportError:
            pass
        venv = os.environ.get("AGENTMAXX_VENV") or str(Path.home() / ".agentmaxx" / ".venv")
        for site in sorted(Path(venv).glob("lib/python*/site-packages")):
            sys.path.insert(0, str(site))
            try:
                import headroom as hr
                _headroom = hr
                return hr
            except ImportError:
                continue
    return None


def headroom_compress(text: str) -> str | None:
    """None when headroom is absent, fails, or does not shrink the input."""
    hr = load_headroom()
    if hr is None:
        return None
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            cfg = hr.CompressConfig(compress_user_messages=True)
            out = hr.compress([{"role": "user", "content": text}], config=cfg)
        msgs = getattr(out, "messages", None) or []
        got = msgs[0].get("content", "") if msgs else ""
        if not got.strip() or len(got) >= len(text):
            return None
        return got
    except Exception:
        return None


def lowfat_path() -> str | None:
    return shutil.which("lowfat")


def wrap_argv(argv: list[str], lowfat: str | None) -> list[str]:
    """Prefix argv with lowfat when it has a bundled filter for the command."""
    if lowfat and argv and os.path.basename(argv[0]).lower() in LOWFAT_CMDS:
        return [lowfat, *argv]
    return argv


def run_command(argv: list[str], timeout: int = RUN_TIMEOUT) -> dict:
    """Run argv (via lowfat when covered), capturing combined output. Fail-open."""
    wrapped = wrap_argv(argv, lowfat_path())
    try:
        proc = subprocess.run(wrapped, capture_output=True, text=True, timeout=timeout, errors="replace")
        return {"text": proc.stdout + proc.stderr, "via_lowfat": wrapped != argv,
                "returncode": proc.returncode, "timeout": False}
    except FileNotFoundError:
        return {"text": f"command not found: {argv[0]}", "via_lowfat": False, "returncode": 127, "timeout": False}
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or "") + (e.stderr or "")
        return {"text": out or f"command timed out after {timeout}s", "via_lowfat": wrapped != argv,
                "returncode": 124, "timeout": True}


def compress_text(text: str, command: str = "", budget: int = BUDGET,
                  backend: str = "auto", spill: bool = True) -> tuple[str, dict]:
    """Compress text, routing by kind. Returns (output, info); never raises."""
    kind = classify(text, command)
    info = {"kind": kind, "backend": "passthrough", "input_chars": len(text)}
    if len(text) <= budget:
        return text, info
    # Logs/diffs/prose go straight to the builtin: headroom's base package
    # leaves code protected and logs untouched (measured, not assumed).
    if backend == "auto":
        order = ["headroom", "builtin"] if kind == "json" else ["builtin"]
    elif backend == "builtin":
        order = ["builtin"]
    else:
        order = [backend, "builtin"]
    spill_path = spill_text(text) if spill else None
    result: str | None = None
    for name in dict.fromkeys(order):
        try:
            if name == "headroom":
                result = headroom_compress(text)
            else:
                result = builtin_compress(text, kind, command, budget, spill_path)
            if result and result.strip() and len(result) < len(text):
                info["backend"] = name
                break
            result = None
        except Exception:
            result = None
    if result is None:
        return text, info
    if info["backend"] == "headroom" and len(result) > budget:
        # Headroom takes no budget; the builtin engines already fit themselves
        # (and squeeze's over-budget verdict lines are authoritative, not slack).
        result = _minimal_cut(result, budget)
        info["refit"] = True
    note = f"[better-compress: {kind} via {info['backend']} {len(text):,} -> {len(result):,} chars"
    if spill_path:
        note += f"; full output saved to {spill_path} (grep it instead of re-running)"
    info["output_chars"] = len(result)
    return result + "\n" + note + "]", info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--file", help="compress this file instead of stdin")
    ap.add_argument("--command", default="", help="command that produced the text (log detection)")
    ap.add_argument("--budget", type=int, default=BUDGET)
    ap.add_argument("--backend", choices=("auto", "headroom", "builtin"), default="auto")
    ap.add_argument("--json", action="store_true", help="emit {output, kind, backend, ...}")
    ap.add_argument("--timeout", type=int, default=RUN_TIMEOUT)
    ap.add_argument("--run", nargs=argparse.REMAINDER, help="run COMMAND, compress its output")
    args = ap.parse_args(argv)

    run = args.run
    if run and run[0] == "--":
        run = run[1:]
    if run:
        res = run_command(run, args.timeout)
        out, info = compress_text(res["text"], command=run[0], budget=args.budget, backend=args.backend)
        info.update({k: res[k] for k in ("via_lowfat", "returncode", "timeout")})
    else:
        if args.file:
            text = Path(args.file).read_text(errors="replace")
        elif not sys.stdin.isatty():
            text = sys.stdin.read()
        else:
            ap.error("nothing to compress: pipe stdin or pass --file/--run")
        out, info = compress_text(text, command=args.command, budget=args.budget, backend=args.backend)
    if args.json:
        json.dump({"output": out, **info}, sys.stdout)
    else:
        sys.stdout.write(out if out.endswith("\n") else out + "\n")
        print(f"# kind={info['kind']} backend={info['backend']}", file=sys.stderr)
    return res["returncode"] if run else 0


if __name__ == "__main__":
    raise SystemExit(main())
