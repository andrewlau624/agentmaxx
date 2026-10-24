# Quality research: smarter sessions, fewer loops, more perspective

Researched 2026-10-23. Two inputs: (1) a mine of this machine's transcripts, last 30 days
(151 real main-thread sessions, 47,949 events, 714 subagent files; headless bench runs
excluded the way `evals/corrections.py:50-51` does); (2) published evidence, 2024-2026,
URLs inline. Cost is out of scope here; see `savings-research.md` for that.

## What actually goes wrong on this machine

### Corrections (68 in 1,851 typed prompts)

`evals/corrections.py --days 30` finds 43; a broader regex (`wait|actually|still|undo|
just do|why did you`) finds 25 more it misses. Hand-categorised:

| failure type | count | repos |
|---|---:|---|
| misread the request | 23 | 7 (all three trading repos, Documents, School, riftlab, rook-labs) |
| conversational "no" / disputes / false positive | 22 | |
| wrong assumption, acted on unchecked state | 7 | 5 |
| stopped short, asked or proposed instead of doing | 6 | 4 |
| repeated a mistake already corrected (within session) | 4 | design feedback, Kalshi/Polymarket venue mixup |
| scope creep | 3 | |
| verification claimed but false ("its not laoding", "you broke other agents") | 2 | |
| stuck in a command loop | 0 | |

Examples: `no i meant with the minute/seconds idea`; `no two repos app and server`;
`my real fills were be betting it all on accident - dont use that as data`;
`no continue now do it all at once idk why you wait so long`; `stop saying kalshi im
not using kalshi im doing polymarket`.

Miner precision ~70%, recall low, and `recurrences()` (`corrections.py:80-91`) only
compares across sessions, so the literal within-session repeats above score 0.

### Loops: none at the command level

Same Bash command run 3+ times with 2+ failures: 2/151 sessions, both artefacts (a
normalisation collision; Chrome stderr noise on successful screenshots). Edit-then-revert:
1 pair in 170 Edits, a real blast-radius miss in riftlab. Near-identical consecutive
WebFetch: 9 pairs, 8 of them adjacent doc pages. Bash heredoc edits (auto mode) are
invisible to Edit-based detectors, so these are floors, but nothing suggests a thrash problem.

The loop the user feels is a conclusion loop. Assistant turns ending "no strategy passed /
fails the bar / no edge": trading-lab 35, llm-trader 15, swing-trader 9. User replies
"keep going / find something / think outside the box / other ideas": swing-trader 34,
trading-lab 17, llm-trader 15. Example pair: `I don't have an untested idea with real
potential. Your project has already run about 1,000 tests` -> `no like tests including
like for very confident picks...`. swing-trader's CLAUDE.md already carries four hand-added
rules against this (never test the same idea in a new costume; branch before you test; go
two levels down before calling the root dead; every do-not-redo row names what was `not
tested`), each added after the loop circled back. Nothing structural enumerates the
hypothesis space or forces an unvisited angle before the loop picks its next study.

### Research search: phrasing is varied, angles are not

85 sessions/files with 5+ WebSearch, 1,192 queries (swing-trader 304, trading-lab 226,
Documents 191, llm-trader 153). Within a session, mean pairwise Jaccard median 0.07 and no
session where half the queries are near-duplicates. But:

- 59/85 sessions never searched for counter-evidence (failure cases, limitations, criticism).
  Angle counts per session: 0:4, 1:16, 2:27, 3:20, 4:13, 5:5.
- Cross-session re-search of the same query (Jaccard >= 0.5, same repo): swing-trader 12%,
  trading-lab 6%, llm-trader 4%. Same paper looked up 10-04 and 10-18; same Schwab margin
  question 09-24 and 09-29.
- Worst chain: a swing-trader subagent ran 13 `site:usethinkscript.com <strategy noun>
  backtest` queries, one frame with the noun swapped.

### Quality skills never fire

Skill calls in 30 days: loop 15, page-rules 6, hallmark 6, deep-research 4, dataviz 3,
spec-first 1. assumption-check, explore, test-first, investigate, verify-pr, code-review,
safe-change, simplify, security-review: 0. Of 100 sessions with 5+ file writes (counting
heredocs), 99 used no quality skill. AskUserQuestion: 23 calls total.

### Verification gap is narrow but mis-aimed

260 implementation-flavoured "done/fixed/passes" claims; 10 (4%) had no run or check in
the preceding 10 tool calls, all "I edited it, you deploy it" hand-offs. The real
failures ("its not loading", "you broke other agents and champs like mages") happened when
a check ran but did not cover the user's path.

## What the evidence says works

Graded: measured (a number), practice (vendor description), null/negative.

### Research breadth

- STORM (https://arxiv.org/html/2402.14207): perspectives discovered from the structure of
  *adjacent* topics, then per-perspective grounded Q&A. Measured: unique sources 99.8 vs
  54.4 without perspectives vs 39.6 without the iterative conversation. The iterative
  follow-up grounded in what was just read is the larger lever.
- Co-STORM (https://arxiv.org/pdf/2408.15232): a moderator that asks questions from
  retrieved-but-unused information beats adding more expert personas. One expert plus a
  moderator captures most of the gain.
- Failing to Falsify (ICLR 2026, https://www.alphaxiv.org/abs/2604.02485): ratio of
  disconfirming to confirming probes correlates rho=0.75 with success; a one-line
  falsification instruction raised rule discovery 42% -> 56%.
- Stopping: RAAC (https://arxiv.org/pdf/2608.15191) and Don't Stop Early
  (https://arxiv.org/pdf/2604.24978): define per-requirement sufficiency criteria before
  the first search; stop when criteria are covered and the last searches add no new
  sources. Fixes both over- and under-searching.
- Anthropic multi-agent research (https://www.anthropic.com/engineering/multi-agent-research-system):
  per-subagent objective, boundaries, forbidden overlap, output format; vague briefs caused
  duplicate searches; agents preferred SEO farms over papers until told otherwise.
- Negative: generic multi-query rewriting is near zero on precise queries
  (https://arxiv.org/html/2604.01733v1); more personas beyond ~3 without a gap-finder add little.

### Loop recovery

- 82% of failed CLI-agent trajectories keep going after recovery is impossible
  (https://arxiv.org/pdf/2607.09510); OpenHands ships a stuck detector
  (https://docs.openhands.dev/sdk/guides/agent-stuck-detector). Relevant in general; the
  local data shows no command-level loops, so this is low priority here.

### Verification and self-critique

- Same-context self-review hurts: Self-Refine -1.4 to -1.8 pp on SWE-bench Verified;
  fresh-context verification that reconstructs the task from the diff gains +3.6 to +7.0 pp
  on the same backbone (RETRACE, https://arxiv.org/pdf/2608.08950). Models have a 45-79%
  blind spot for their own prior reasoning (Self-Correction Bench).
- Reflexion's gain (80 -> 91 HumanEval) is conditioned on a test failure, i.e. an external
  signal. Generic "reflect on your answer" steps are not supported.
- Anthropic: give Claude a check it can run; show evidence not assertions; a fresh-context
  reviewer told to report only correctness and requirement gaps, because a gap-hunting
  reviewer reports gaps even when the work is sound (https://code.claude.com/docs/en/best-practices).

### Reading the request

- ClarifyCodeBench (https://arxiv.org/html/2607.00711v2): Claude Sonnet 4.5 asks 0.29
  clarification turns vs ~1.65 ideal; catches a second ambiguity <10% of the time;
  thinking mode did not help. Clarity Is Not Assumed (https://arxiv.org/html/2604.21505):
  ambiguity detection precision ~50%, so the cheap move is to restate the reading and
  proceed, asking only when readings diverge materially. The local "stopped short" count
  says the user overrides most pauses, so default to check-and-proceed, not ask.

### Lessons memory

- Failure-derived memory items transfer best (ReasoningBank +8.3 pp, fewer steps,
  https://arxiv.org/pdf/2509.25140). ACE (https://arxiv.org/html/2510.04618v2) names
  brevity bias and context collapse: detail belongs in on-demand items, not always-loaded
  rules. Honest Lying (https://arxiv.org/pdf/2605.29463): a wrong inferred cause with two
  agreeing votes becomes entrenched; only store a cause when the error text is present.
- Best item shape: trigger (tool / file glob / error string / task type) -> rule ->
  evidence (session, command, output) -> hits, last fired -> scope.

### Harness (verified against https://code.claude.com/docs/en/hooks, Oct 2026)

33 events including PostToolUseFailure, SubagentStart/Stop, PostToolBatch. `additionalContext`
is accepted on UserPromptSubmit, PreToolUse, PostToolUse, PostToolUseFailure, Stop,
SubagentStart/Stop, SessionStart. Stop can block with a reason (cap 8 continuations,
`CLAUDE_CODE_STOP_HOOK_BLOCK_CAP`). UserPromptSubmit cannot rewrite the prompt, only add
context. `type:"prompt"` and `type:"agent"` hooks exist for model-evaluated gates.

## Directions, ranked by local frequency times evidence

| # | direction | local signal | evidence | shape |
|---|---|---|---|---|
| 1 | Research-loop structure: hypothesis-space map per repo, mandatory unvisited angle, disconfirming probe, "retrieved but unasked" step, cross-session query log, pre-declared sufficiency criteria | 59 "nothing passes" turns, 66 "keep going" replies, 70% no counter-evidence search, 12% re-search | STORM, Co-STORM, Failing to Falsify, RAAC | skill + per-repo state file + PreToolUse(WebSearch) dedupe against the repo's query log |
| 2 | Request-reading guard: on short or deictic prompts, inject "restate your reading in one line, then act; ask only if readings diverge" | 23/68 corrections are misreads | ClarifyCodeBench, Clarity Is Not Assumed | UserPromptSubmit additionalContext or one contract line |
| 3 | Skills to hooks: the quality skills are dead listing weight; move the two that matter into hooks (fresh-context verifier at Stop when the session edited code; assumption check injected when a prompt has 2+ unknowns) and prune the rest | 0 invocations in 30 days; 99/100 implementation sessions unguarded | RETRACE, Anthropic review practice | Stop `type:"agent"` hook + UserPromptSubmit; delete or demote unused skills |
| 4 | Lessons v2: broader capture regex, within-session repeat detection, error-text-required provenance, trigger-indexed injection on PostToolUseFailure/PreToolUse instead of SessionStart only | miner misses 25/68, 0 within-session repeats detected, 4 real repeats | ReasoningBank, ACE, Honest Lying | extend `hooks/lessons.py`, `evals/corrections.py` |
| 5 | Coverage-aware verify: after tests pass, check that the changed symbols' callers and the user-named path were exercised | 2 false "done" claims, both coverage misses | Anthropic "give Claude a check" | extend `hooks/verify.py` with `better-callers` |
| skip | Command-loop fingerprint hook | 0 real loops in 151 sessions | strong in general, unmeasurable here | revisit if data changes |
| skip | Generic self-reflection, free-form premortems, multi-agent debate | | negative or null results | |

## How each would be measured (ledger convention)

- Direction 1, offline: per research-day, count distinct hypothesis families tested, share
  of sessions with a counter-evidence query, cross-session re-search rate, and "nothing
  passes" -> "keep going" pairs. Live: run the swing-trader loop N cycles with and without
  the skill; count new families and kills per cycle, not just "passes".
- Direction 2: misread corrections per 100 typed prompts (now 1.2%) over the next 30 days,
  plus AskUserQuestion rate to make sure it does not trade misreads for questions.
- Direction 3: bench cell with the verifier subagent on the hard tasks; pass^3 not pass@1
  (SWE Atlas shows pass^3 drops 30-50% from pass@1, https://arxiv.org/html/2605.08366v1).
  Cost of the extra agent is a real line; needs the CI to exclude zero.
- Direction 4: miner recall on a hand-labelled set (the 68 above), within-session repeat
  count, lessons fired per session that match a later failure.

Mining scripts for reproduction: `scratchpad/mine/{extract,t1_corrections,t2_loops,
t3_search,t3b_cross,t4_skills,t5_claims}.py` in this session's scratchpad (not committed).
