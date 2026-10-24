# agentmaxx

Hooks, settings and skills for Claude Code, Codex and OpenCode, each measured on real transcripts or a hidden-test bench before shipping. Numbers, losers included: [evals/RESULTS.md](evals/RESULTS.md), [evals/LEDGER.md](evals/LEDGER.md).

Why: every turn re-sends the whole conversation, so cost is resident context × turns (cache 86% of the bill, ~87k-token prefix per session). And in 151 real sessions there were zero command loops; the agent gets stuck by misreading short prompts (23 of 68 corrections) and by re-testing killed research ideas in new costumes.

## What runs

| When | Piece | Does | Measured |
|---|---|---|---|
| install | tool search + 2k-char contract | Schemas on demand (Claude Code disables this behind a proxy); verdict first, batch calls, delegate, verify | −18%/task, 18/18 pass, CI −31% to −11% |
| session start | `lessons` | Injects rules from your past corrections | followed 5/5 with, 0/5 without |
| prompt | `prompt_guard` | Short/deictic prompt → restate reading first; 2+ unknowns → list assumptions | fires 18% / 2%; 3 of 4 real misreads caught |
| tool call | `guard` | Denies `rm -rf ~`, `curl \| sh`, force-push, `reset --hard`, secret reads/writes; parses `sh -c` | 0.45% of 14,846 calls, 61 were live secrets |
| tool call | `squeeze` | Big Bash output → errors, verdicts, head, tail; full text saved to grep | 0.3% of outputs touched, 91% of verdict lines kept, 138KB → 1.6KB |
| tool call | `research_log` | Near-duplicate web search denied once, with the prior query | 10 of 530 denied, 8 real repeats |
| tool failure | `lessons` | Injects past lessons matching the error | unmeasured |
| stop | `verify` | Runs tests, blocks once on new failures; names changed functions with no test | bench gate |
| stop | `review` | Fresh-context `claude -p` reviews task + diff for correctness gaps, blocks once | 6 s, 2¢; FP rate unmeasured |

Plus `agentmaxx doctor` (where tokens go, what to change, `--apply`), skills `research` (stop criteria, hypothesis map, disconfirming query), `claude-md` (57k → 4.1k tokens, nothing deleted), `fast-commit`, `human-voice`, `spec-first`, `verify-pr`; an opencode plugin; GrayMatter memory; 21 `better-*` CLI tools.

## Tested, not shipped

| Knob | Result |
|---|---|
| `better-*` as MCP tools | +89%/task; model never called one |
| Effort low / medium (Opus) | −32% but loses a pass / −1% |
| Sonnet subagents | −22%, equal pass, kept off for quality |
| Compaction 400k | −12.6%; early compaction cost Haiku 4 of 21 passes. `doctor` recommends only |
| 8 quality skills | 0 uses in 30 days → `skills-optional/` |
| Better search tools | discovery before first edit: median 1 call |

## Install

```bash
make install && agentmaxx doctor
```

Restart agents. Off: `AGENTMAXX_{VERIFY,REVIEW,PROMPT_GUARD,RESEARCH_LOG}=0`. Squeeze thresholds `AGENTMAXX_SQUEEZE_THRESHOLD/_BUDGET` (8000/6000). Per-repo: `agentmaxx init`. Re-measure: `evals/bench/run.py`, `*_replay.py`, `doctor.py`; `make test`.

Layout: `agentmaxx.py` CLI · `providers/` · `templates/CLAUDE.md` · `hooks/` · `tools/` · `skills/` · `integrations/opencode/` · `mcp/` (Codex) · `evals/`
