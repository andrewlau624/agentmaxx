# Evals

Scores two A/B arms of Claude Code transcripts by weighted token cost.

This is a **test utility, not a tool**. It has no `registry.yaml` entry, is not
installed into any provider, and is never injected into a repo's contract — an
agent should never run it mid-task. It exists so a change to the contract or the
`better-*` tools can be judged against a measurement instead of intuition.

```bash
python3 -m evals "~/.claude/projects/PROJECT/control-*.jsonl" \
                 "~/.claude/projects/PROJECT/treatment-*.jsonl"
```

Run from the repository root. Each glob is one arm — the same task run with and
without the change under test. Pass several transcripts per arm to average over
repeated runs; `n=1` is not enough to trust a percentage.

## Why a weighted index

Raw token counts mislead. The four token types differ in price by ~50x:

| Token | Weight |
|---|---|
| Raw input | 1.0 |
| Cache write | 1.25 |
| Cache read | 0.1 |
| Output | 5.0 |

The first A/B in this repo had the treatment arm reading **more** cached tokens
than the control and still coming out ~38% cheaper, because it wrote far less
cache and emitted a shorter answer. Comparing raw totals would have reported the
opposite result.

## Reading the output

`cache_read` is the line that usually dominates, and it scales as
`turns x prefix`. So a change helps only if it cuts one of those two: fewer round
trips, or less content resident in context. A change that trims bytes per call
but adds a call is a regression — this is what the index is for.
