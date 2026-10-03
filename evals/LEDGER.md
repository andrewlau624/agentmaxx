# Optimization ledger

Running log for the loop in `prompts/ultra-optimize-loop.md`. Newest iteration
last. Every number has the command that produced it.

Cost is the weighted index: input 1, cache write 1.25 (5m) or 2 (1h), cache
read 0.1, output 5.

Bench spend so far: $0.

## Iteration 1 (2026-10-03): price what sits in context

Picked because it was free (replay, no bench spend) and it ranks the seed
queue: read dedupe, huge-Read squeezing, cache TTL, and tool-result decay all
depend on numbers nobody had.

Command: `python3 evals/residency.py --days 14` (550 sessions, 11,787 requests).

- **Writes were underpriced.** 79% of cache writes on this machine are 1h
  writes (`cache_creation.ephemeral_1h_input_tokens`), billed at 2x input, not
  1.25x. Re-priced: cache read 58%, cache write 32%, output 10%
  (`python3 evals/doctor.py`). RESULTS.md had 65/24/11.
- **Tool results are 10.2% of the bill as residency** (tokens x requests they
  stay resident, at read price, cut at compaction). Bash 8.1%, WebSearch 0.8%,
  Read 0.8%, WebFetch 0.1%. This machine does not run the squeeze hook.
- **Read dedupe: dropped.** 26 of 618 Reads (4%) repeat an unchanged
  file+range; they are 0.0% of the bill. A dedupe hook can't pay for itself.
- **Huge Reads and web content: deprioritized.** Read + WebSearch + WebFetch
  are 1.7% of the bill together.
- **Cache TTL: keep 1h for human-paced work.** Verified in the 2.1.288
  binary: `CLAUDE_CODE_PROMPT_CACHE_TTL` = `5m` | `1h`; unset means 1h on a
  subscription, 5m on API key/Bedrock/Vertex; subagents default to 5m
  (`CLAUDE_CODE_SUBAGENT_PROMPT_CACHE_TTL`). Replaying real request gaps
  (10,791 under 5m, 369 between 5m and 1h, 75 over 1h): 5m everywhere would
  cost **+19%** (`simulate_ttl` in doctor.py). Shipped: doctor now replays both
  TTLs and recommends a switch when the other one is >3% cheaper.
- **Idle >1h rewrites are 7.0% of the bill** (65 events). No TTL fixes these;
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

- **Prior thinking stays in context.** On 549 turns with >2k hidden output,
  548 grew the next request by billed output, not visible output. The 2.1.288
  binary sends `context_management.edits: [{type: "clear_thinking_20251015",
  keep: "all"}]`, hardcoded. No setting clears old thinking.
- **Composition of cache reads** (`python3 evals/residency.py`, all sessions
  incl. subagents): tool results, prompts and injections 34.5%; prefix
  (system, tools, post-compact summary) 29.9%; thinking 21.1%; visible
  assistant text and tool calls 14.5%.
- **Thinking is ~18% of the bill**: 58% of billed output is hidden (5.8% of
  the bill as output) plus 21% of reads (12% of the bill as residency).
  The levers are `CLAUDE_CODE_EFFORT_LEVEL`, `MAX_THINKING_TOKENS`,
  `CLAUDE_CODE_DISABLE_ADAPTIVE_THINKING` (names verified in the binary,
  semantics not yet). Every one trades quality, so it needs a bench where
  quality can drop.
- **Bash tool inputs are as resident as Bash outputs** (char count: 10.9% vs
  12.4% of reads). Mostly heredocs writing files or scripts. Edit inputs are
  0.1%: whole-file writes dominate. Possible contract line, needs a bench.
- Claude Code has idle-triggered tool-result clearing
  (`clear_tool_uses_20250919`, fires after an idle gap, when the cache is
  cold anyway) behind a server flag. Not user-tunable.

Decision: ship `composition()` in residency.py with a test. No config change.

## Queue (expected % of bill x confidence / cost to test)

1. Hard bench tasks where Haiku/Sonnet fail sometimes. Blocks every quality
   question below (effort, compaction, subagents, verify gate).
2. Effort / thinking budget vs pass rate (thinking ~18% of bill).
3. Compact window live measurement and compaction quality (largest modeled
   lever: doctor says 200k saves 22% here; quality unmeasured).
4. Subagent prefix and model routing (each subagent pays its own prefix).
5. No-AI-tells detector `evals/tells.py` (deterministic part is free to build).
6. Fixed prefix audit with `/context` (prefix now p50 22k; smaller lever than
   the seed assumed).
7. Codex/opencode parity (verify keys first).
8. Guard coverage gaps (security; replay for false positives).

Dropped: read dedupe (0.0%). Deprioritized: Read/Web squeezing (1.7% total).
