"""Compare two A/B arms of transcripts by weighted token cost.

An arm is one or more transcripts — the same task run with and without
the change under test. Reporting the weighted index rather than raw
token counts matters: an arm can read far more cached tokens and still
be cheaper, which is exactly what the first A/B in this repo showed.
"""

from __future__ import annotations

from pathlib import Path

from evals.transcript import SessionUsage, parse_sessions, total


def compare_arms(control: list[Path], treatment: list[Path]) -> dict:
    if not control or not treatment:
        raise ValueError("both arms need at least one transcript")

    control_total = total(parse_sessions(control))
    treatment_total = total(parse_sessions(treatment))
    baseline = control_total.weighted_cost

    savings = (
        (baseline - treatment_total.weighted_cost) / baseline
        if baseline
        else 0.0
    )

    return {
        "control": _summarize(control_total),
        "treatment": _summarize(treatment_total),
        "weighted_savings_pct": round(savings * 100, 1),
    }


def _summarize(usage: SessionUsage) -> dict:
    return {
        "sessions": usage.session,
        "turns": usage.turns,
        "raw": usage.raw,
        "cache_write": usage.cache_write,
        "cache_read": usage.cache_read,
        "output": usage.output,
        "weighted_cost": round(usage.weighted_cost, 1),
    }
