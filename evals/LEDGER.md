# Optimization ledger

Running log for the loop in `prompts/ultra-optimize-loop.md`. Newest iteration
last. Every number has the command that produced it.

Cost is the weighted index: input 1, cache write 1.25 (5m) or 2 (1h), cache
read 0.1, output 5.

Bench spend so far: $26.6 (estimates are logged before each batch; actuals after).

## Iteration 1 (2026-10-03): price what sits in context

Picked because it was free (replay, no bench spend) and it ranks the seed
queue: read dedupe, huge-Read squeezing, cache TTL, and tool-result decay all
depend on numbers nobody had.

Command: `python3 evals/residency.py --days 14` (550 sessions, 11,787 requests).

- Writes were underpriced. 79% of cache writes on this machine are 1h
  writes (`cache_creation.ephemeral_1h_input_tokens`), billed at 2x input, not
  1.25x. Re-priced: cache read 58%, cache write 32%, output 10%
  (`python3 evals/doctor.py`). RESULTS.md had 65/24/11.
- Tool results are 10.2% of the bill as residency (tokens x requests they
  stay resident, at read price, cut at compaction). Bash 8.1%, WebSearch 0.8%,
  Read 0.8%, WebFetch 0.1%. This machine does not run the squeeze hook.
- Read dedupe: dropped. 26 of 618 Reads (4%) repeat an unchanged
  file+range; they are 0.0% of the bill. A dedupe hook can't pay for itself.
- Huge Reads and web content: deprioritized. Read + WebSearch + WebFetch
  are 1.7% of the bill together.
- Cache TTL: keep 1h for human-paced work. Verified in the 2.1.288
  binary: `CLAUDE_CODE_PROMPT_CACHE_TTL` = `5m` | `1h`; unset means 1h on a
  subscription, 5m on API key/Bedrock/Vertex; subagents default to 5m
  (`CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`). Replaying real request gaps
  (10,791 under 5m, 369 between 5m and 1h, 75 over 1h): 5m everywhere would
  cost **+19%** (`simulate_ttl` in doctor.py). Shipped: doctor now replays both
  TTLs and recommends a switch when the other one is >3% cheaper.
- Idle >1h rewrites are 7.0% of the bill (65 events). No TTL fixes these;
  the whole context is rewritten on resume. Only a smaller context on resume
  would, which is the compact-window line.

Decision: ship `evals/residency.py`, doctor TTL check and 1h pricing, tests in
`evals/test_residency.py`. Bug found by the test: Edits didn't clear ranged
Reads, which doubled the repeat count (8% -> 4%).

## Iteration 2 (2026-10-03): what cache reads are made of

Picked because iteration 1 left 80% of resident context unexplained, and the
answer decides whether anything besides compaction moves the 58% read line.

Method: attribute each request's context growth from usage deltas.
Thinking is stored with an empty body in transcripts, so hidden output =
`output_tokens` minus visible text and tool input (chars / 3.6). The model
reproduces 104% of actual cache-read tokens on main sessions, so the
accounting closes.

- Prior thinking stays in context. On 549 turns with >2k hidden output,
  548 grew the next request by billed output, not visible output. The 2.1.288
  binary sends `context_management.edits: [{type: "clear_thinking_20251015",
  keep: "all"}]`, hardcoded. No setting clears old thinking.
- Composition of cache reads (`python3 evals/residency.py`, all sessions
  incl. subagents): tool results, prompts and injections 34.5%; prefix
  (system, tools, post-compact summary) 29.9%; thinking 21.1%; visible
  assistant text and tool calls 14.5%.
- Thinking is ~18% of the bill: 58% of billed output is hidden (5.8% of
  the bill as output) plus 21% of reads (12% of the bill as residency).
  The levers are `CLAUDE_CODE_EFFORT_LEVEL`, `MAX_THINKING_TOKENS`,
  `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` (names verified in the binary,
  semantics not yet). Every one trades quality, so it needs a bench where
  quality can drop.
- Bash tool inputs are as resident as Bash outputs (char count: 10.9% vs
  12.4% of reads). Mostly heredocs writing files or scripts. Edit inputs are
  0.1%: whole-file writes dominate. Possible contract line, needs a bench.
- Claude Code has idle-triggered tool-result clearing
  (`clear_tool_uses_20250919`, fires after an idle gap, when the cache is
  cold anyway) behind a server flag. Not user-tunable.

Decision: ship `composition()` in residency.py with a test. No config change.

## Iteration 3, part 1 (2026-10-03): deterministic tell detector

Picked while a background agent mines real bug-fix commits for hard bench
tasks (queue item 1). The detector costs no bench spend and the generation
benchmark needs it.

Built `evals/tells.py`: regex rules for prose, commit messages, UI markup and
code (added lines of a diff), with density per 1k words, per file, or per 100
lines, plus sentence-length variation for prose. Tests in
`evals/test_tells.py`.

Human baseline, pre-2022 text from requests, flask, httpx, fastapi (blobless
clones; `python3 evals/tells_baseline.py`):

| Medium | Sample | Result |
|---|---|---|
| Commit messages | 1,600 | 0.2% contain any tell |
| Docs (.md/.rst, >200 words) | 91 | p50 0.0, p90 1.4 tells per 1k words |
| Python diffs | 115 | p50 0.0, p90 0.0 per 100 added lines |

Two rules misfired on human text and were narrowed. "Let's" is normal in
tutorials, so narration now means "let me" and its kin. `new_x` locals are
ordinary, so version-suffix names only count on definitions (`def
parse_v2`). Emoji commit prefixes are allowed when the repo's own history
uses them (fastapi uses gitmoji: 369 of 400 hits came from it).

Not yet known: model output density on the same detector. That comes from
the generation tasks in the bench.

## Iteration 3, part 2: hard tasks from real bug fixes

10 tasks in `evals/bench/real/` (sqlparse, mistune, boltons; fixes from
2022-2026), mined by a subagent and checked by `verify.py` plus a dry run of
`run.py`'s grader with the reference fix applied: 10/10 fail without it and
pass with it. `run.py` now runs repo tasks from a `git archive` of the parent
commit with history re-initialized, discards agent edits to the hidden test
files before applying them, and requires the full suite to pass.

Calibration batch, estimate ~$5.50: arm `v2`, Haiku 4.5 x 2 reps and Sonnet
5.5 x 1 rep on all 10 real tasks. Goal: find tasks and a model with pass
rates between 20% and 80%.

## Iteration 3, part 3: guard gaps (while the calibration batch runs)

Closed four gaps from the seed list: secrets printed by interpreter
one-liners, environment dumps from one-liners, secrets files uploaded with
curl `@file`, and git hook persistence. The guard split commands on `;`
before tokenizing, which cut quoted one-liners in half, so one-liners are now
checked on the whole command first. `evals/guard_replay.py` replays real
calls: 14,846 calls over 30 days, 0.45% denied (was 0.47% on 14,350). The
first one-liner rule flagged node scripts that read `.env` into a client
config without printing it; it now requires the read to be printed.

Not done: supply-chain scan of `.claude/` and `.mcp.json` in fresh clones
(Claude Code's folder trust prompt covers the first launch; unclear what a
hook adds), prompt-injection scanning of WebFetch/MCP output.

## Iteration 3, part 4: Codex and opencode parity

Keys verified by a subagent against Codex 0.142.5 and opencode 1.18.31
(bad-typed configs, source, docs); details in `evals/parity-research.md`.

Shipped: opencode `tool_output.max_bytes: 8000` (default 51200), merged into
`~/.config/opencode/opencode.json` without overriding a user value. Same
mechanism as squeeze (tail kept, full output to a file). Replay of the 8k
tail cap on 9,833 real Bash outputs: 771 truncated, 23% less Bash result
volume. Tested with a throwaway HOME.

Not ported, with reasons. Codex `model_auto_compact_token_limit` is capped
at 90% of a 272k window, so it already compacts near 245k and 300000 is a
no-op. Codex tool search is always on. Codex `tool_output_token_limit`
(default 10000) cuts the middle, saves nothing, and also hits file reads:
park until a Codex bench exists. Codex hooks exist but need per-user approval
in `/hooks`; a squeeze port is possible via PostToolUse `continue:false`,
parked for the same reason. opencode has no Stop-equivalent that can block,
so verify.py has no port.

## Iteration 3 result: calibration ($8.67 actual vs $5.50 estimated)

`v2` arm on the 10 real tasks. Haiku 4.5: 17/20 pass, median ~$0.33/run,
14-81 turns. Sonnet 5.5: 9/10, ~$0.10/run, 5-17 turns. Sonnet is ~3.5x
cheaper per task than Haiku here because Haiku flails for 40+ turns.
Failures: mistune-emphasis-mod3 (Haiku 1/2), mistune-list-directive-markers
(Haiku 1/2), boltons-indexedset-slice-after-remove (Haiku 1/2, Sonnet 0/1).
Checked the Sonnet indexedset failure by hand: its fix normalizes negative
indexes but `x[-20:]` on a 9-item set still reaches `islice` with -11 and
raises ValueError. A real bug, not a strict grader.

So the real tasks separate models a little but Sonnet still passes 90%.
Quality claims on Sonnet need either more reps on the 3 hard tasks or
harder tasks; noted for the queue.

## Iteration 4: effort level on Sonnet

Hypothesis: `CLAUDE_CODE_EFFORT_LEVEL=low` (or medium) cuts weighted cost
per task by >=15% at equal pass rate on the real tasks. Arms v2, v2_low,
v2_medium (verified values: low|medium|high|xhigh), 3 reps each, Sonnet,
10 real tasks. Estimate 80 runs x ~$0.11 = ~$9; cumulative ~$18.

Result ($8.65 actual): no effect. Pass 26/30 in every arm (same tasks
fail: indexedset, tzcast). Cost vs v2, 90% CI: low -9% to +8%, medium -7%
to +9%. Hidden (thinking) share of output from the run transcripts: low 59%,
default 61%, medium 62%, so the setting barely changes how much Sonnet 5.5
thinks in agentic -p runs. A one-shot probe (digit-sum count) gave 199 vs
239 output tokens at low vs xhigh on Sonnet and 91 vs 171 on Opus, all
correct. Decision: park. The 18% thinking share was measured on interactive
Opus sessions; an Opus effort batch (~$12) would push spend near the $40
cap, so it waits for a go-ahead.

## Iteration 5: tell density on generation tasks (runs alongside 4)

Hypothesis: loading the skills (`v2s`) or the tells gate (`v2t`) lowers tell
density on generated docs, UI and commit messages versus `v2` and `ts`,
costing <=3% more per task. Tasks g1-g6 (README section, landing page,
settings screen, ADR, security review, fix + commit) on the fixture, Sonnet,
3 reps. Estimate 72 runs x ~$0.08 = ~$6; cumulative ~$24.

Also added a bootstrap 90% CI to analyze.py. The published Haiku result
(v2 -11%) has a CI of -33% to +19%, so it is not significant; RESULTS.md
now says so. The Sonnet v2 result holds (-31% to -11%).

Result ($8.44 + $0.83 rerun). Sonnet 5.5 output is close to tell-free on
the regex detector in every arm: total hits over 18 documents per arm were
ts 11, v2 4, v2s 18, v2t 3. Pass 18/18 in each arm; mean cost
$0.112-0.120. One landing page inspected by hand: warm neutral palette, no
gradients, specific headings. The remaining tells there (fragment
marketing headings) need a reader, not a regex.

The model invoked no skill in any run (tools were only Bash, Read, Write),
so `v2s` differs from `v2` only by the skill listing in the prompt. Its 18
hits were mostly bold-label bullets, and the skills themselves were written
in bold-label bullets and em dashes, so I rewrote all skill bodies without
them. Rerun on the prose tasks: 8 hits vs 16 before, v2 2; per-run counts
range 0-6, so this is noise at n=9.

Decisions: tells gate parked (nothing to catch on Sonnet's bench output; on
this machine's interactive history it would fire on 40% of doc writes, so
the place to test it is Opus interactive-style tasks). Skill text cleanup
shipped (no cost, removes the contradiction). Anti-tell skills can't be the
enforcement path because they aren't loaded unprompted.

Next for tells: an LLM-judge pass with human references, since regex hits
are at the floor for Sonnet.

Stop-rule count: iterations 4 and 5 shipped nothing measurable.

## Iteration 7: subagents (replay + two probes, $0.78)

Replay, 14 days: subagents are 13.5% of the bill (136 sessions; 84% of that
on Opus). First-request context p50 by type: fork 256k (inherits the
parent, by design), general-purpose 65k, Explore 54k; main sessions 18k.

Probe: `claude -p` with this machine's settings, one general-purpose
subagent that replies "ok". Main 60k, subagent 53.5k. Same with
`ENABLE_TOOL_SEARCH=true`: main 27k, subagent 20.9k. This machine's
settings.json routes through a local proxy (`ANTHROPIC_BASE_URL`), which
turns tool search off, so every MCP schema rides in each subagent's prefix.
Replaying non-fork subagents with a 32.6k smaller prefix: 1.7% of the bill.
`make install` already sets the variable and `doctor` already recommends
it here, so nothing new to ship.

Parked: routing subagents to a cheaper model (`CLAUDE_CODE_SUBAGENT_MODEL`)
needs a bench where subagents do real work; the current tasks don't spawn
any.

## Iteration 8: fixed prefix

`ENABLE_TOOL_SEARCH=true claude -p /context` on this machine: 17.1k at
start. System prompt 1.3k, system tools 3.6k, MCP tools 0.8k (22.6k
deferred), MCP instructions 0.8k, skills 10k (109 skills: user 7.6k,
built-in 2.2k, claude.ai sync 0.5k, claude-mem 0.4k).

The skill listing budget is a setting (verified in the 2.1.288 settings
schema): `skillListingBudgetFraction`, default 0.01 of the context window
in characters, which on a 1M model is ~10k tokens; most user skills are
already truncated to their names. `skillOverrides` per skill takes on,
name-only, user-invocable-only, off.

Replay: `skill_listing` attachments (623, p50 1.8k tokens) cost 2.3% of
the bill as residency. In 14 days the model invoked 9 skills on its own;
the user typed /loop 50 times. Hiding a skill is a judgement call, so this
ships as doctor advice, not a default: when the listing is over 1.5% of the
bill, doctor names the skills Claude actually invoked and the
`skillOverrides` setting. Upper bound on the saving: 2.3%.

## Queue (expected % of bill x confidence / cost to test)

Remaining budget before the $40 pause: ~$10 after the regression run.

1. Subagent share of the bill and subagent prefix size (free replay).
2. Fixed prefix audit with `/context` (cheap; prefix p50 22k).
3. Compact window live measurement and compaction quality (largest modeled
   lever, doctor says 200k saves 22% here; long tasks are expensive to run,
   needs budget).
4. LLM-judge pass for tells with human references (regex floor on Sonnet).
5. Opus effort batch (~$12; needs a go-ahead past the $40 cap).
6. Harder tasks: more real fixes where Sonnet fails (only indexedset and
   tzcast fail now).
7. Prompt-injection scan of WebFetch/MCP output; `.claude/` supply-chain
   check for fresh clones.

Done: hard tasks (10 real), tells detector, guard gaps, Codex/opencode key
verification, effort on Sonnet (negative), tells bench (floor).
Dropped: read dedupe (0.0%). Deprioritized: Read/Web squeezing (1.7% total).
