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

Two lines matter more than the totals.

**`weighted_cost`** is the comparison. A change helps only if it cuts round trips
or content resident in context; trimming bytes per call while adding a call is a
regression, which is what the index exists to catch.

**`cache_hit_rate`** is `cache_read / (cache_read + cache_write)` — the share of
the cacheable prefix served from cache instead of rewritten. Read it before
trusting a `weighted_cost` delta, because it separates the two arms failing for
different reasons from the change actually working:

| Rate | Meaning |
|---|---|
| ~0.95 | Prefix stays warm; cost tracks what the agent does |
| ~0.5 | Prefix is rewritten about as often as it is read |
| ~0.0 | No cache reuse at all |

The default cache TTL is 5 minutes. A session parked longer than that re-pays
its entire prefix as both uncached input (1.0x) and a fresh write (1.25x) before
any work happens — so a low rate means the session's *shape* is the cost, and no
amount of tool-output trimming will move it. In the worst real session measured
here, cache writes were 71% of weighted cost and uncached re-sends another 19%;
cache reads were 7%. Compare arms only when their hit rates are close.
