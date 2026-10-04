# Results

Measured 2026-10-03 on Claude Code 2.1.288. Everything here is reproducible
with the scripts in this directory. Two kinds of evidence:

- Bench: real headless `claude -p` runs on `bench/fixture`, graded by
  hidden tests the agent never sees. 6 tasks (bugfix, feature, noisy debug,
  read-only question, spec-heavy coupon stacking, cross-file validation),
  3 reps each, per-task medians, then averaged across tasks so every task
  weighs the same. Cost is `total_cost_usd` from the run's JSON.
- Replay: 14 days of the author's real transcripts (339 sessions, ~10k
  API requests), deduplicated per API response.

## Where the money goes (replay)

| Line | Share of weighted cost |
|---|---|
| Cache reads | 58% |
| Cache writes | 32% |
| Output | 10% |

Corrected 2026-10-03: the first version priced every cache write at 1.25x, but
79% of writes here use the 1h TTL, billed at 2x (`python3 evals/doctor.py`,
550 sessions over 14 days). The earlier split was 65/24/11.

The median request carried **266k tokens** of context; 66% of requests ran
above 200k. Sessions started with a **~86k-token fixed prefix** (tool
schemas, skill listings, injected context), 30% of all context billed.
Auto-compaction fired 4 times in 339 sessions: on 1M-context models it waits
until ~967k.

So the bill is resident context × turns. Output-side tricks (terse prose)
touch the smallest line.

## Bench: cost per task (Sonnet 5.5)

| Arm | Pass | Median $/task vs base |
|---|---|---|
| `base`: tool search off (what a proxy `ANTHROPIC_BASE_URL` silently does) | 18/18 | — |
| `v1`: old agentmaxx (110-line contract + MCP better-* server) | 12/12 | **+89%** |
| `v1` contract, tool search on, no MCP | 18/18 | −1% |
| `ts`: tool search on | 18/18 | −16% |
| `ts` + lean contract | 18/18 | −15% |
| **`v2`: ts + lean contract + guard/squeeze/verify hooks** | **18/18** | **−18%** |

Why v1 lost: the model never called a single better-* MCP tool (native
Grep/Read/Edit covered everything), and the MCP server connecting after the
first request changed the tool list, so the first two requests were full
cache misses (36.6k and 41.9k tokens written, 0 read). The long contract
alone also ate almost all of tool search's savings.

Bootstrap 90% CIs on the cost ratio (resampling tasks, then reps; `python3
evals/bench/analyze.py`, added later): `v2` −31% to −11%, `ts` −30% to −8%,
`v1` +16% to +205%. These exclude zero.

Same bench on Haiku 4.5, where mistakes happen:

| Arm | Pass | Median $/task vs base |
|---|---|---|
| `base` | 17/18 (t1 failed after 30 turns) | — |
| `v2` | **18/18** | −11% (90% CI −33% to +19%: not significant) |

Hook firings across all v2 bench runs: the first verify gate (block on any
failing test) fired 20 times, almost all on the fixture's pre-existing
failure, and each block bought an extra turn (−14% instead of −18%). The
shipped gate snapshots failures at session start and blocks only on new
ones; it fired 0 times, because no run broke a passing test. So the bench
shows it costs nothing; it does not show it improves quality. The evidence
for that is external (Reflexion: test feedback lifts pass rates; Huang et al.:
self-review without a test signal doesn't).

## Long sessions: auto-compact window (replay)

Replaying every session's real context growth with compaction at window W
(summary 12k tokens, compaction call billed as a full cache read plus
summary output, then a cache rewrite):

| Window | Total bill | Compactions |
|---|---|---|
| ~1M (default on `[1m]` models) | −3% | 2 |
| 400k | −23% | 83 |
| **300k (installed default)** | **−25%** | 282 |
| 200k | −26% | 684 |
| 150k | +4% (thrashes: 86k prefix + 33k buffer) | 2,560 |

Quality, measured since: on the 10 real-repo tasks, Haiku 4.5 with
compaction forced at ~40k tokens (`CLAUDE_CODE_AUTO_COMPACT_WINDOW=100000`,
the minimum, plus `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=40`) passed 13/21 vs
17/20 without (one-sided Fisher p = 0.09), and cost +19% (90% CI −9% to
+49%) because every compaction rewrites the cache. The losses were on tasks
that need detail held across many steps. This is far more aggressive than
any real window, but it points the same way as the research: compaction
costs quality, so `doctor` no longer recommends windows below 300k.

Earlier note: quality is not simulated. The research says smaller context helps (Chroma
"context rot", lost-in-the-middle; Anthropic's context editing +29%), but
each compaction can drop detail, which is why the default is 300k, not 200k.

## What sits in context (replay)

`python3 evals/residency.py --days 14`. A tool result's cost is its tokens
times the requests it stays resident for, at read price, until the next
compaction.

| Source | Share of weighted bill |
|---|---|
| All tool results | 10.2% |
| Bash | 8.1% |
| WebSearch | 0.8% |
| Read | 0.8% |
| WebFetch | 0.1% |

Tool results are a minority of what the cache re-reads. Splitting every
request's context growth by source (`composition()` in the same script; it
reproduces 104% of the actual cache-read tokens):

| Source | Share of cache reads |
|---|---|
| Tool results, prompts, hook and system injections | 34.5% |
| Prefix: system prompt, tools, post-compaction summary | 29.9% |
| Thinking from earlier turns | 21.1% |
| Assistant text and tool-call inputs | 14.5% |

Thinking stays resident: Claude Code 2.1.288 sends `clear_thinking` with
`keep: "all"`, and on 548 of 549 heavy-thinking turns the next request grew
by the full billed output. Transcripts store thinking with an empty body, so
it is counted as billed output minus visible text. Counting both its output
price and its residency, thinking is about 18% of the bill.

Repeat Reads of an unchanged file and range: 26 of 618 (4%), 0.0% of the
bill. A read-dedupe hook is not worth building.

## Cache TTL (replay)

`CLAUDE_CODE_PROMPT_CACHE_TTL` takes `5m` or `1h` (checked in the 2.1.288
binary; unset means 1h on a subscription, 5m on an API key or cloud
provider). Replaying the real gaps between requests: 10,791 under 5 minutes,
369 between 5 minutes and an hour, 75 over an hour. Forcing 5m would rewrite
the whole context on each of the 369 and cost **+19%** despite cheaper writes.
`doctor` runs this replay on your own transcripts and recommends switching
only when the other TTL is more than 3% cheaper. Rewrites after more than an
hour idle cost 7.0% of the bill, and no TTL setting avoids them.

## Machine-writing tells: sources and measurement

Sourced catalogs in `evals/tells-sources/`: prose (10 sources, including
Wikipedia's "Signs of AI writing", Kobak, Liang, Reinhart, Juzek & Ward,
Freeburg), UI (17, including Anthropic's frontend-design skill and Krebs'
design-slop-cop detector), code/commits/PRs/security reports (23, including
10 arXiv studies and curl's posts). Every entry has a fetched URL and a
verbatim quote; 12 quotes were re-fetched and checked by hand. Every rule in
`evals/tells.py` names its source ids or "measured".

Measured on 209 docs Claude 5.x wrote on this machine vs 334 pre-2022 human
docs (`python3 evals/tells_mine.py`; catalogs and style guides excluded
because they quote the tells):

| Signal | Model | Human |
|---|---|---|
| GPT-4-era word lists (Kobak, Reinhart, Juzek, Wikipedia), per 1k words | 0.006-0.105 | 0.008-0.647 |
| Spaced em dash, docs containing one | 60 / 209 | 3 / 334 |
| `→` in prose, docs | 34 / 209 | 0 / 334 |
| Line opening with a bold label and colon, docs | 66 / 209 | 24 / 334 |
| Inline-header list items, docs | 114 / 209 | 53 / 334 |

The published word lists are real but describe GPT-4/4o; on this output
they occur at the human rate. Freeburg is the one source that measured
Claude directly (Opus 4.6: 9.09 em dashes per 1k words vs a human mean of
3.23), and it matches what separates here.

With only the strong rules counting (formatting rules reported but not
triggering), the tells gate would flag 22% of the model docs and 1% of the
human docs; counting inline-header lists too raised the human rate to
6-14%. Re-scoring the bench's generation outputs: no prose doc reaches the
gate; 13 of 30 generated pages use the cream background near `#F4F1EA`
that Anthropic's own frontend-design skill lists as a second-order default.
The old regex list had called those pages clean.

Blind judge, topic-matched (`python3 evals/tells_judge.py --matched --n 20`,
then `--variant` for the third arm; $4.06). For 20 pre-2021 human docs,
Opus 5.5 wrote a twin from the same project, title and headings. Sonnet 5.5
saw each excerpt alone and gave P(machine):

| Arm | Judge AUC vs human | Regex AUC | Mean P(machine) |
|---|---|---|---|
| Human | | | 0.07 |
| Opus, no guide | 0.84 | 0.52 | 0.15 |
| Opus + human-voice skill | 0.99 | 0.42 | 0.25 |
| Opus + skill without "How people actually write" | 0.91 | 0.47 | |

The skill made the writing easier to spot, not harder: the judge scored the
skill twin above the plain twin in 15 of 19 pairs, AUC difference 90% CI
+0.08 to +0.23. The phrases it cited are the register that section asks
for ("few people remember which number goes with which name, though, and
you don't need to"). Removing the section helped in 10 of 19 pairs (5
worse), which isn't significant; it still doesn't beat no guide. The regex
detector can't separate these docs at all (AUC ~0.5). The judge ranks well
but is badly calibrated: it called 1 of 58 model docs machine-written at
P >= 0.5, so it can't serve as a gate. It invented 13 of 267 quotes, which
the script drops. An unmatched first pass (model docs about the bench
fixture) gave AUC 1.00 from topic alone and is not reported.

## Effort level (bench, negative)

Sonnet 5.5, `v2` arm, 10 real-repo tasks x 3 reps per arm.
`CLAUDE_CODE_EFFORT_LEVEL=low` and `medium` vs unset: pass 26/30 in all
three; cost 90% CI −9% to +8% (low) and −7% to +9% (medium). Thinking
stayed ~60% of output in every arm. Not a lever for Sonnet in headless
runs. Opus is untested.

## Bash output squeezer (replay)

`hooks/squeeze.py` replayed over 8,829 real Bash outputs: it touched the 8.3%
over 8k chars, cut Bash result volume **36%** and resident Bash tokens
(chars × remaining turns) **28%**. In 70 of 734 squeezed outputs at least one
error-looking line exceeded the 6k budget; the full output is always saved to
a file the model is told to grep, so nothing is unrecoverable. On the bench's
noisy-debug task: 138,870 → 1,634 chars with the failing assertion and the
`available=1` clue intact. Agents already pipe through `tail` most of the
time, so the bench shows little per-task change; the win is on the long tail.

## Guard false positives (replay)

`hooks/guard.py` replayed over 14,350 real Bash/Read/Write/Edit calls from 30
days. The first version would have denied 3.3% (pushes to main in solo repos,
heredoc bodies that merely mention `.env`, `rm -rf $SP/x` with SP set in the
same command). After fixes: **0.47%**. Of those, 61 are reads like `cat .env`
and `grep KEY .env` that printed live secrets into the transcript, which is
what it should stop. 6 are `git reset --hard`, `git clean -f`, and one
force-push. Added 2026-10-03: one-liners that print a secrets file (`python3 -c
"print(open('.env').read())"`, `node -e` likewise) or dump the environment,
uploads of secrets files (`curl -d @.env`, `-F f=@~/.aws/credentials`),
writes into `.git/hooks/` or `.husky/`, and `git config core.hooksPath`.
A one-liner that reads `.env` into a client config without printing it is
allowed; the first version flagged three of those. Replayed over 14,846 calls
from 30 days (`python3 evals/guard_replay.py`): 0.45% denied, none of them
from the new rules. Push-to-main protection is opt-in (`AGENTMAXX_GUARD_PROTECT_MAIN=1`).
Verified live: under `bypassPermissions` the deny still holds and the model
reports the reason.

## Learning across sessions (bench)

Session 1 does a task, the user corrects a convention, session 2 is a fresh
process on a fresh clone doing a different task. Same lean contract both arms.

| Convention | Without lessons | With lessons | Session-2 cost |
|---|---|---|---|
| "commit finished work with a `shopkit: ` prefix" (not inferable) | 0/5 | **5/5** | $0.095 vs $0.097 |
| "CHANGELOG entry under ## Unreleased" (partly inferable) | 2/4 | **4/4** | $0.101 vs $0.088 |

In every lessons run the model recorded the rule itself after the
correction nudge, as one imperative line.

## Correctness bugs fixed along the way

- `token_telemetry.py` and `transcript.py` counted every content-block line,
  each repeating its response's usage: Claude totals were inflated ~2.3x.
  Telemetry also reported $0 for every Claude session (no `costUSD` in
  modern transcripts) and computed hit rate with output in the denominator.
- `better-trace` reported `len(found)` (dict keys) as `total_found` and
  crashed with `UnboundLocalError` when the search failed; a failed search
  now reports the error instead of "no callers".
- `make stage` wipes `~/.agentmaxx`, so runtime state (lessons, verify
  baselines) lives in `~/.local/share/agentmaxx`.

## What didn't help, or wasn't tested

- Old README numbers ("prefix −40%, cache hit 86%") came from the
  double-counting telemetry; disregard them.
- Terse-output contracts: external A/B (JetBrains, 86 tasks) found −8.5%;
  RTK-style command rewriting found +7.6% cost. Not re-tested here.
- Haiku subagents: plausible, not benchmarked.
- n=3 per cell. Differences under ~10% on a single task are noise; the
  across-task averages above are the claim.
