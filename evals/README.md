# Evals

Measurement, not tooling: nothing here is installed into an agent's toolbelt.
Every hook, setting and skill in agentmaxx was measured here before it shipped,
and the ones that did not help are recorded too. Results and method:
[RESULTS.md](RESULTS.md). Decision log, one entry per iteration with cost and
outcome: [LEDGER.md](LEDGER.md). The quality study (what actually goes wrong in
real sessions, and the literature on fixing it): [quality-research.md](quality-research.md).

## Headline results

| Question | Answer | Where |
|---|---|---|
| Does the shipped setup cut cost at equal quality? | −18% per task, 18/18 pass, 90% CI −31% to −11% (Sonnet 5.5, 6 tasks, 3 reps) | RESULTS, bench |
| Did the old MCP `better-*` server help? | No. +89%: the model never called a tool, and the late MCP connect forced cache rewrites | RESULTS, bench |
| Where does the money go? | Cache reads 48%, cache writes 38%, output 14%; ~86k-token fixed prefix is 30% of billed context | RESULTS, replay |
| Does the guard block real work? | 0.45% of 14,846 real calls denied, 61 of them reads that printed live secrets | `guard_replay.py` |
| Does the squeezer destroy evidence? | Touches 0.3% of 6,541 outputs at shipped thresholds, keeps 91% of error and verdict lines; 0 of 693 squeezed outputs re-run | `squeeze_replay.py` |
| Do lessons change the next session? | Rule followed 5/5 with lessons, 0/5 without | `bench/learn.py` |
| Effort level? | Sonnet: no effect. Opus: `low` −32% but costs a pass, `medium` −1%. Not shipped | RESULTS, LEDGER 4, 21 |
| Cheaper subagents? | Sonnet subagents −22% at equal pass; off by default for quality | RESULTS, LEDGER 7, 11 |
| Compaction window? | 400k saves 12.6% over 30 days; forced early compaction cost Haiku 4 passes of 21 | RESULTS, LEDGER 9 |
| What goes wrong in real sessions? | 68 corrections in 1,851 prompts: 23 misreads, 0 command loops; the research "nothing passes" loop ran 59 times | quality-research |
| Are the shipped quality skills used? | 8 of them had 0 invocations in 30 days; moved to `skills-optional/` | LEDGER 23 |

Not measured yet: the `review` hook's false-positive rate and the effect of the
`research` skill and query log; both need 30 days of transcripts after install.

## Scripts

| Script | What it answers |
|---|---|
| `doctor.py` (`agentmaxx doctor`) | Where this machine's tokens go, and which settings would move them |
| `token_telemetry.py` (`make telemetry`) | Per-session tokens and API-equivalent cost, all providers |
| `bench/run.py` | Live A/B: real `claude -p` runs on a fixture repo or the real-repo tasks, graded by hidden tests |
| `bench/analyze.py` | Per-task medians and bootstrap CIs over `results.jsonl` |
| `bench/learn.py` | Does a correction in one session change the next session? |
| `guard_replay.py`, `squeeze_replay.py` | Replay a hook over this machine's real tool calls and outputs |
| `corrections.py --days N` | Find user corrections in transcripts, by type, with within-session repeats |
| `compress_bench.py` | Compressor backends on real outputs |
| `tells.py`, `tells_mine.py` | Machine-writing tells, sourced and measured against this machine's docs |
| `python3 -m evals` | Weighted-cost comparison of two sets of existing transcripts |

`bench/` spends real tokens (~$0.05-0.15 per Sonnet run) and isolates runs
with `--setting-sources project,local`, so your own hooks and plugins don't
leak in. Arms live in `bench/arms.json`; add one and run
`python3 evals/bench/run.py base yourarm --reps 3`, then
`python3 evals/bench/analyze.py evals/bench/results.jsonl base`.

## Comparing existing transcripts

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
