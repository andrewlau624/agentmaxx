# agentmaxx

Hooks, settings and skills for Claude Code, Codex and OpenCode, each one measured on this machine's transcripts or a hidden-test bench before it shipped. Numbers, including the losers, live in [evals/RESULTS.md](evals/RESULTS.md) and [evals/LEDGER.md](evals/LEDGER.md).

Two facts drive it. Cost: every turn re-sends the whole conversation, so the bill is resident context × turns (cache reads 48%, writes 38%, output 14%; ~87k-token fixed prefix per session, 28k of it my own CLAUDE.md). Quality: in 151 real sessions there were zero command loops. The agent gets stuck by misreading short prompts (23 of 68 corrections) and by re-testing killed research ideas in new costumes ("nothing passes" 59 turns vs "keep going" 66 replies).

## What runs

| When | Piece | What it does | Measured |
|---|---|---|---|
| install | `ENABLE_TOOL_SEARCH=true` | Tool schemas load on demand. Claude Code disables this behind any proxy `ANTHROPIC_BASE_URL` | bench prefix 63k → 17k tokens |
| install | contract | ~2k-char rules in each host's global file: verdict first, batch calls, run independent work at once, delegate exploration, verify before "done" | with tool search + hooks: −18%/task, 18/18 pass, CI −31% to −11% |
| session start | `lessons` | Injects rules from your past corrections, per repo + global, ≤5k chars | rule followed 5/5 with, 0/5 without |
| prompt | `prompt_guard` | Short/deictic/typo'd prompt → "restate your reading first". Implementation prompt with 2+ unknowns → "list every assumption and how you'll check it" | fires 18% / 2% of 1,886 prompts; 3 of 4 real misreads caught |
| tool call | `guard` | Denies `rm -rf ~`, `curl \| sh`, force-push, `reset --hard`, `.env`/key reads, writing creds or git hooks. Parses the command, so `sh -c` doesn't slip | 0.45% of 14,846 calls; 61 of those printed live secrets |
| tool call | `squeeze` | Big Bash output → errors, verdicts, head, tail; filler and secrets stripped; full text saved to a grep-able file | touches 0.3% of 6,541 outputs, keeps 91% of verdict lines; 138KB → 1.6KB; 0 re-runs |
| tool call | `research_log` | Per-repo web-search log; near-duplicate query denied once with the prior query + date | 10 of 530 denied, 8 real repeats |
| tool failure | `lessons` | Injects ≤3 past lessons whose words match the error, once | live FP fixed day one; unmeasured |
| web/MCP result | `inject_scan` | Names prompt-injection markers so the text is read as data | sourced catalog, see RESULTS |
| stop | `verify` | Runs your tests; blocks once, only on failures new since session start. Names changed functions with callers but no test | bench gate; coverage note unmeasured |
| stop | `review` | Fresh-context `claude -p` (Sonnet) gets task + diff only, reports correctness gaps, blocks once | ~6 s, 2¢; 1 real bug caught, 1 FP seen; rate unmeasured |
| always | statusline | Context vs compact window, cache hit rate, cost | |

Also: `agentmaxx doctor` (where your tokens go, what the prefix is made of, which CLAUDE.md is fat, what compaction and TTLs would save; `--apply` writes env recommendations without overwriting yours). Skills: `research` (sufficiency criteria, per-repo hypothesis map, one disconfirming query + one source pivot, stop rule), `claude-md` (57k → 4.1k and 31k → 5.1k tokens, nothing deleted), `fast-commit`, `human-voice`, `spec-first`, `verify-pr`, `better-tools` (21 bounded CLI tools; the model never called them as MCP tools, so Claude Code no longer registers them). opencode plugin squeezes `bash`/`grep` results and redirects whole-file reads over 12KB. GrayMatter for cross-session memory.

## Tested, not shipped

| Knob | Result |
|---|---|
| MCP `better-*` server + 110-line contract | +89%/task, model never called a tool, late connect forced cache rewrites |
| Effort `low` / `medium` (Opus) | −32% but loses a pass / −1%, wash. Sonnet: no effect |
| Sonnet subagents | −22%, equal pass; off by default, weaker than the parent for ~3% of the bill |
| Compaction 400k | −12.6% over 30 days; forced early compaction cost Haiku 4 of 21 passes. `doctor` recommends, install doesn't set |
| 8 quality skills (assumption-check, explore, test-first, code-review, …) | 0 invocations in 30 days → `skills-optional/` |
| Better search tools | discovery before first edit: median 1 call, p90 7 → nothing to save |
| Read dedupe, test-cheating gate | no effect / bench couldn't tempt |

Unmeasured: `review` FP rate, whether `research` moves the loop numbers (needs 30 days), coverage note, CLAUDE.md diet effect on behavior.

## Install

```bash
make install && agentmaxx doctor
```

Restart agents after. Off switches: `AGENTMAXX_{VERIFY,REVIEW,PROMPT_GUARD,RESEARCH_LOG,VERIFY_COVERAGE}=0`. Squeeze: `AGENTMAXX_SQUEEZE_THRESHOLD/_BUDGET` (8000/6000), `_NOISY_THRESHOLD/_NOISY_BUDGET` (3000/2000). `AGENTMAXX_REVIEW_MODEL`, `AGENTMAXX_OPTIONAL_SKILLS=1`. Lessons: `python3 ~/.claude/agentmaxx/hooks/lessons.py list|vote ID up|down|rm ID`. Per-repo instead of global: `agentmaxx init` (writes a git-excluded `CLAUDE.local.md`). Re-measure: `evals/bench/run.py`, `squeeze_replay.py`, `guard_replay.py`, `corrections.py`, `doctor.py`; `make test`.

Vs [lowfat](https://github.com/zdk/lowfat): it rewrites known commands and compresses `Read`. Here, squeeze runs after the result (sees every `cd && sed | grep` chain, can't break a pipeline; `git`/`ls`/`find` were <5% of oversized output) and reads stay exact so `Edit` still matches.

## Layout

`agentmaxx.py` CLI · `providers/` host wiring · `templates/CLAUDE.md` contract · `hooks/` (with tests) · `tools/` 21 `better-*` · `skills/`, `skills-optional/` · `integrations/opencode/` · `mcp/` (Codex) · `external/` third-party manifest · `evals/` doctor, replays, bench, [RESULTS](evals/RESULTS.md), [LEDGER](evals/LEDGER.md), [quality-research](evals/quality-research.md)
