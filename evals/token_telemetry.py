#!/usr/bin/env python3
"""Token telemetry across local agent stores.

Baseline measurement for contract/tooling changes: per-session requests,
input/cache/output tokens, tool-result volume, and cost over a time window,
aggregated from every provider that keeps local usage data.

Sources:
    opencode  ~/.local/share/opencode/opencode.db   (SQLite)
    claude    ~/.claude/projects/**/*.jsonl          (transcript JSONL)
    codex     ~/.codex/sessions/**/rollout-*.jsonl    (rollout JSONL)

Usage:
    python3 evals/token_telemetry.py [--days N] [--json] [--source S]

Read-only everywhere: SQLite opens in read-only mode, JSONL files stream.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


OPENCODE_DB = Path.home() / ".local/share/opencode/opencode.db"
CLAUDE_PROJECTS = Path.home() / ".claude/projects"
CODEX_SESSIONS = Path.home() / ".codex/sessions"


def new_session(source: str, project: str, **fields) -> dict:
    session = {
        "source": source,
        "project": project[:18],
        "model": "",
        "agent": "",
        "subagent": False,
        "cost": 0.0,
        "tokens_input": 0,
        "tokens_output": 0,
        "tokens_reasoning": 0,
        "tokens_cache_read": 0,
        "tokens_cache_write": 0,
        "time_updated": 0.0,
        "turns": 0,
        "tool_result_bytes": 0,
    }
    session.update(fields)
    return session


def iso_to_epoch(value: str | None) -> float:
    if not value:
        return 0.0
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


# ---------------------------------------------------------------- opencode

def load_opencode(days_window: float) -> list[dict]:
    if not OPENCODE_DB.exists():
        return []

    uri = f"file:{OPENCODE_DB}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = conn.execute(
            """
            SELECT id, slug, directory, model, agent, cost,
                   tokens_input, tokens_output, tokens_reasoning,
                   tokens_cache_read, tokens_cache_write,
                   time_created, time_updated, parent_id
            FROM session
            WHERE time_updated >= ?
            ORDER BY cost DESC
            """,
            (days_window,),
        ).fetchall()
    finally:
        conn.close()

    by_id = {}
    sessions = []
    for (
        sid, slug, directory, model, agent, cost,
        t_in, t_out, t_reason, t_cr, t_cw,
        created, updated, parent_id,
    ) in rows:
        s = new_session(
            "opencode",
            Path(directory).name if directory else "?",
            title=slug,
            directory=directory,
            model=model or "",
            agent=agent or "",
            cost=cost,
            tokens_input=t_in,
            tokens_output=t_out,
            tokens_reasoning=t_reason,
            tokens_cache_read=t_cr,
            tokens_cache_write=t_cw,
            time_updated=(updated or 0) / 1000,
            subagent=parent_id is not None,
        )
        by_id[sid] = s
        sessions.append(s)

    conn = sqlite3.connect(uri, uri=True)
    try:
        for sid, data in conn.execute("SELECT session_id, data FROM message"):
            session = by_id.get(sid)
            if session is None:
                continue
            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                continue
            if msg.get("role") == "assistant":
                session["turns"] += 1

        for sid, data in conn.execute(
            "SELECT session_id, data FROM part"
            " WHERE data LIKE '%\"type\":\"tool\"%'"
        ):
            session = by_id.get(sid)
            if session is None:
                continue
            try:
                output = (json.loads(data).get("state") or {}).get("output")
            except json.JSONDecodeError:
                continue
            if isinstance(output, str):
                session["tool_result_bytes"] += len(output)
    finally:
        conn.close()

    return sessions


# ------------------------------------------------------------------ claude

def _tool_result_bytes(content) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(
            len(block.get("text", ""))
            for block in content
            if isinstance(block, dict) and block.get("type") == "text"
        )
    return 0


def load_claude(cutoff: float) -> list[dict]:
    """Parse Claude Code transcript JSONL files.

    Assistant lines carry per-request usage; user lines carry tool_result
    blocks whose text length approximates tool-result volume.
    """
    if not CLAUDE_PROJECTS.is_dir():
        return []

    sessions: dict[str, dict] = {}

    for path in CLAUDE_PROJECTS.rglob("*.jsonl"):
        for line in path.open(errors="ignore"):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            timestamp = iso_to_epoch(record.get("timestamp"))
            if timestamp and timestamp < cutoff:
                continue

            message = record.get("message") or {}
            record_type = record.get("type")

            if record_type == "assistant":
                sid = record.get("sessionId") or path.stem
                session = sessions.get(sid)
                if session is None:
                    session = new_session(
                        "claude",
                        path.parent.name.rsplit("-", 1)[-1],
                        time_updated=timestamp,
                    )
                    sessions[sid] = session
                session["time_updated"] = max(session["time_updated"], timestamp)
                session["turns"] += 1

                usage = message.get("usage") or {}
                session["tokens_input"] += usage.get("input_tokens", 0) or 0
                session["tokens_output"] += usage.get("output_tokens", 0) or 0
                session["tokens_cache_read"] += (
                    usage.get("cache_read_input_tokens", 0) or 0
                )
                session["tokens_cache_write"] += (
                    usage.get("cache_creation_input_tokens", 0) or 0
                )
                session["cost"] += record.get("costUSD") or 0.0

            elif record_type == "user":
                sid = record.get("sessionId") or path.stem
                session = sessions.get(sid)
                if session is None:
                    session = new_session(
                        "claude",
                        path.parent.name.rsplit("-", 1)[-1],
                        time_updated=timestamp,
                    )
                    sessions[sid] = session
                content = message.get("content")
                if isinstance(content, list):
                    for block in content:
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "tool_result"
                        ):
                            session["tool_result_bytes"] += _tool_result_bytes(
                                block.get("content")
                            )

    return list(sessions.values())


# ------------------------------------------------------------------- codex

def load_codex(cutoff: float) -> list[dict]:
    """Parse Codex rollout JSONL token_count events (best effort).

    Rollout formats vary between codex versions; everything is defensive and
    a source that yields nothing simply contributes no rows.
    """
    if not CODEX_SESSIONS.is_dir():
        return []

    sessions: dict[str, dict] = {}

    for path in CODEX_SESSIONS.rglob("*.jsonl"):
        if path.stat().st_mtime < cutoff - 86400:
            continue

        sid = path.stem
        for line in path.open(errors="ignore"):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            payload = record.get("payload") or {}
            if payload.get("type") != "token_count":
                continue

            info = payload.get("info") or {}
            totals = (
                info.get("total_token_usage")
                or info.get("last_token_usage")
                or {}
            )
            if not totals:
                continue

            session = sessions.get(sid)
            if session is None:
                session = new_session(
                    "codex",
                    path.parent.parent.name,
                    time_updated=path.stat().st_mtime,
                )
                sessions[sid] = session

            cached = totals.get("cached_input_tokens", 0) or 0
            raw_input = totals.get("input_tokens", 0) or 0
            session["tokens_input"] = max(session["tokens_input"], raw_input)
            session["tokens_cache_read"] = max(
                session["tokens_cache_read"], cached
            )
            session["tokens_output"] = max(
                session["tokens_output"], totals.get("output_tokens", 0) or 0
            )
            cost_info = info.get("cost") or {}
            if isinstance(cost_info, dict):
                session["cost"] = max(
                    session["cost"], cost_info.get("total_usd", 0) or 0.0
                )
            session["turns"] += 1

    return list(sessions.values())


# ------------------------------------------------------------------ report

def fmt_int(n: float) -> str:
    return f"{int(n):,}"


def print_table(sessions: list[dict], days: int) -> None:
    header = (
        f"{'date':<11} {'src':<4} {'project':<18} {'sub':<4} {'turns':>5} "
        f"{'input':>9} {'cache_rd':>10} {'cache_wr':>9} "
        f"{'output':>8} {'tool_kb':>8} {'cost $':>8}"
    )
    print(header)
    print("-" * len(header))

    totals = {
        key: 0
        for key in (
            "turns", "tokens_input", "tokens_cache_read",
            "tokens_cache_write", "output", "tool_result_bytes", "cost",
        )
    }

    for s in sessions:
        date = (
            time.strftime("%Y-%m-%d", time.localtime(s["time_updated"]))
            if s["time_updated"]
            else "?"
        )
        output = s["tokens_output"] + s["tokens_reasoning"]
        row = (
            f"{date:<11} {s['source']:<4} {s['project']:<18} "
            f"{'yes' if s['subagent'] else '':<4} "
            f"{s['turns']:>5} {fmt_int(s['tokens_input']):>9} "
            f"{fmt_int(s['tokens_cache_read']):>10} "
            f"{fmt_int(s['tokens_cache_write']):>9} "
            f"{fmt_int(output):>8} "
            f"{s['tool_result_bytes'] / 1024:>8.0f} "
            f"{s['cost']:>8.2f}"
        )
        print(row)

        totals["turns"] += s["turns"]
        totals["tokens_input"] += s["tokens_input"]
        totals["tokens_cache_read"] += s["tokens_cache_read"]
        totals["tokens_cache_write"] += s["tokens_cache_write"]
        totals["output"] += output
        totals["tool_result_bytes"] += s["tool_result_bytes"]
        totals["cost"] += s["cost"]

    print("-" * len(header))
    print(
        f"{'TOTAL':<11} {'':<4} {'':<18} {'':<4} "
        f"{fmt_int(totals['turns']):>5} {fmt_int(totals['tokens_input']):>9} "
        f"{fmt_int(totals['tokens_cache_read']):>10} "
        f"{fmt_int(totals['tokens_cache_write']):>9} "
        f"{fmt_int(totals['output']):>8} "
        f"{totals['tool_result_bytes'] / 1024:>8.0f} "
        f"{totals['cost']:>8.2f}"
    )

    uncached = totals["tokens_input"] + totals["output"]
    cached = totals["tokens_cache_read"]
    if uncached + cached > 0:
        hit_rate = cached / (cached + uncached) * 100
        print(
            f"\ncache hit rate {hit_rate:.0f}%   "
            f"tool results {totals['tool_result_bytes'] / 1024 / 1024:.1f} MB   "
            f"({len(sessions)} sessions, last {days}d)"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--source",
        choices=["all", "opencode", "claude", "codex"],
        default="all",
    )
    args = parser.parse_args()

    cutoff = time.time() - args.days * 86400
    sessions: list[dict] = []
    if args.source in ("all", "opencode"):
        sessions += load_opencode(cutoff * 1000)
    if args.source in ("all", "claude"):
        sessions += load_claude(cutoff)
    if args.source in ("all", "codex"):
        sessions += load_codex(cutoff)

    sessions.sort(key=lambda s: s["cost"], reverse=True)

    if args.json:
        print(json.dumps(sessions, indent=2))
        return 0

    if not sessions:
        print(f"no sessions found in the last {args.days}d")
        return 0

    print_table(sessions, args.days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
