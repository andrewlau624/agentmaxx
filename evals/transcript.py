"""Parse Claude Code transcript JSONL into weighted token-cost metrics.

A test utility, not an agent-facing tool: it lives outside `tools/`, has
no `registry.yaml` entry, and is never injected into a repo's contract.
An agent should not run it mid-task — it exists to score an A/B run
after the fact.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


# Relative per-token price, normalized to raw input = 1.0. Cache reads are
# nearly free; output is the most expensive token you can emit.
COST_WEIGHTS = {
    "raw": 1.0,
    "cache_write": 1.25,
    "cache_read": 0.1,
    "output": 5.0,
}


@dataclass(frozen=True)
class SessionUsage:
    session: str
    turns: int
    raw: int
    cache_write: int
    cache_read: int
    output: int

    @property
    def cache_hit_rate(self) -> float:
        """Share of cacheable prefix served from cache rather than rewritten.

        A session that keeps its prefix warm reads it back many times per
        write, so this sits near 1.0. It falls toward 0.5 when the prefix is
        re-written about as often as it is read — the signature of a session
        left idle past the cache TTL, where each return re-pays the whole
        prefix. Cost then tracks session shape, not tool choice.
        """
        cacheable = self.cache_read + self.cache_write

        return self.cache_read / cacheable if cacheable else 0.0

    @property
    def weighted_cost(self) -> float:
        return (
            self.raw * COST_WEIGHTS["raw"]
            + self.cache_write * COST_WEIGHTS["cache_write"]
            + self.cache_read * COST_WEIGHTS["cache_read"]
            + self.output * COST_WEIGHTS["output"]
        )


def parse_session(path: Path) -> SessionUsage:
    """Aggregate token usage across every assistant turn in one transcript.

    Streams the file line by line: transcripts routinely run to hundreds
    of megabytes, so nothing here may load one whole.
    """
    raw = cache_write = cache_read = output = turns = 0

    with path.open() as handle:
        for line in handle:
            line = line.strip()

            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not isinstance(entry, dict):
                continue

            message = entry.get("message")

            if not isinstance(message, dict):
                continue

            usage = message.get("usage")

            if not isinstance(usage, dict):
                continue

            turns += 1
            raw += usage.get("input_tokens") or 0
            cache_write += usage.get("cache_creation_input_tokens") or 0
            cache_read += usage.get("cache_read_input_tokens") or 0
            output += usage.get("output_tokens") or 0

    return SessionUsage(
        session=path.stem,
        turns=turns,
        raw=raw,
        cache_write=cache_write,
        cache_read=cache_read,
        output=output,
    )


def parse_sessions(paths: list[Path]) -> list[SessionUsage]:
    return [parse_session(path) for path in paths]


def total(sessions: list[SessionUsage]) -> SessionUsage:
    """Sum several sessions into one aggregate, e.g. a single A/B arm."""
    if not sessions:
        return SessionUsage("(none)", 0, 0, 0, 0, 0)

    return SessionUsage(
        session=f"{len(sessions)} sessions",
        turns=sum(session.turns for session in sessions),
        raw=sum(session.raw for session in sessions),
        cache_write=sum(session.cache_write for session in sessions),
        cache_read=sum(session.cache_read for session in sessions),
        output=sum(session.output for session in sessions),
    )
