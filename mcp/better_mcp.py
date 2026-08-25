#!/usr/bin/env python3
"""MCP stdio server exposing agentmaxx better-* tools.

Lets hosts without a plugin system (Claude Code, Codex) register the tools
natively: the model sees them as first-class tools with schemas instead of
having to remember bash invocations from the contract text.

Transport: newline-delimited JSON-RPC 2.0 on stdin/stdout (MCP stdio).
Implemented with the standard library only — same zero-dependency rule as
the rest of agentmaxx.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

TOOLS_ROOT = Path(__file__).resolve().parent.parent / "tools"

PROTOCOL_VERSION = "2024-11-05"
CALL_TIMEOUT_SECONDS = 180


def _schema(properties: dict, required: list[str]) -> dict:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }


def _str(desc: str) -> dict:
    return {"type": "string", "description": desc}


def _int(desc: str) -> dict:
    return {"type": "integer", "description": desc}


TOOLS = [
    {
        "name": "better_context",
        "description": (
            "Search the repository and return matching source with "
            "surrounding context in ONE call. Prefer over grep+read."
        ),
        "inputSchema": _schema(
            {
                "query": {
                    "type": "array",
                    "items": _str("search keywords"),
                    "description": "one or more search keywords",
                },
                "path": _str("directory to search"),
                "max_hits": _int("maximum matches"),
                "context_lines": _int("surrounding context lines"),
                "max_output_chars": _int("output size cap"),
            },
            ["query"],
        ),
        "script": "better-context/better_context.py",
        "flags": {
            "query": None,
            "path": "--path",
            "max_hits": "--max-hits",
            "context_lines": "--context-lines",
            "max_output_chars": "--max-output-chars",
        },
    },
    {
        "name": "better_grep",
        "description": (
            "Ranked repository code search; multiple unrelated patterns "
            "in one call."
        ),
        "inputSchema": _schema(
            {
                "query": {
                    "type": "array",
                    "items": _str("pattern"),
                    "description": "search patterns",
                },
                "path": _str("directory to search"),
                "type": _str("file extension filter, e.g. py"),
                "max_results": _int("result cap"),
            },
            ["query"],
        ),
        "script": "better-grep/better_grep.py",
        "flags": {
            "query": None,
            "path": "--path",
            "type": "--type",
            "max_results": "--max-results",
        },
    },
    {
        "name": "better_cat",
        "description": (
            "Read bounded file ranges. Spec format: 'path', 'path:12-40', "
            "'path:12'."
        ),
        "inputSchema": _schema(
            {
                "spec": {
                    "type": "array",
                    "items": _str("file spec"),
                    "description": "file specs",
                },
                "max_output_chars": _int("output size cap"),
            },
            ["spec"],
        ),
        "script": "better-cat/better_cat.py",
        "flags": {"spec": None, "max_output_chars": "--max-output-chars"},
    },
    {
        "name": "better_find",
        "description": "Find files by glob name pattern, bounded results.",
        "inputSchema": _schema(
            {
                "path": _str("directory to search"),
                "name": _str("glob pattern, e.g. '*.py'"),
                "type": _str("'f' files or 'd' directories"),
            },
            [],
        ),
        "script": "better-find/better_find.py",
        "flags": {"path": None, "name": "--name", "type": "--type"},
    },
    {
        "name": "better_explore",
        "description": (
            "Run FIRST when starting cold on an unfamiliar repo: ranks "
            "candidate files so you read the right one instead of burning "
            "context on dead-end greps."
        ),
        "inputSchema": _schema(
            {
                "task": _str("task or question description"),
                "path": _str("repository root"),
                "num_candidates": _int("candidates to rank"),
                "max_searches": _int("search budget"),
            },
            ["task"],
        ),
        "script": "better-explore/better_explore.py",
        "flags": {
            "task": None,
            "path": "--path",
            "num_candidates": "--num-candidates",
            "max_searches": "--max-searches",
        },
    },
    {
        "name": "better_edit",
        "description": (
            "Apply a batch of exact-string edits across files, atomic "
            "(all succeed or nothing is written)."
        ),
        "inputSchema": _schema(
            {
                "edits": _str(
                    "JSON array of {path, old, new, replace_all?} objects"
                ),
            },
            ["edits"],
        ),
        "script": "better-edit/better_edit.py",
        "flags": {"edits": None},
    },
]

BY_NAME = {tool["name"]: tool for tool in TOOLS}


def call_tool(name: str, arguments: dict) -> tuple[str, bool]:
    tool = BY_NAME.get(name)
    if tool is None:
        return f"unknown tool: {name}", True
    if not TOOLS_ROOT.is_dir():
        return f"tools not installed at {TOOLS_ROOT}; run agentmaxx install", True

    argv = ["python3", str(TOOLS_ROOT / tool["script"])]
    for key, flag in tool["flags"].items():
        value = arguments.get(key)
        if value is None or value == []:
            continue
        if flag is None:
            if isinstance(value, list):
                argv.extend(str(item) for item in value)
            else:
                argv.append(str(value))
        else:
            argv.extend([flag, str(value)])

    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=CALL_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return f"{name} timed out after {CALL_TIMEOUT_SECONDS}s", True

    if result.returncode != 0:
        text = (
            f"exit {result.returncode}: "
            f"{result.stderr.strip() or 'no stderr'}\n{result.stdout}"
        )
        return text, True
    return result.stdout, False


def handle(request: dict) -> dict | None:
    method = request.get("method")
    request_id = request.get("id")

    if request_id is None:
        return None  # notification — nothing to answer

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "agentmaxx", "version": "1.0.0"},
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": tool["name"],
                        "description": tool["description"],
                        "inputSchema": tool["inputSchema"],
                    }
                    for tool in TOOLS
                ]
            },
        }

    if method == "tools/call":
        params = request.get("params") or {}
        text, is_error = call_tool(
            params.get("name", ""), params.get("arguments") or {}
        )
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": text}],
                "isError": is_error,
            },
        }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


def main() -> int:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
