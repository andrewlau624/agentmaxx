# agentmaxx

Hooks, settings and skills that make Claude Code, Codex and OpenCode cheaper and harder to derail. Every turn re-sends the whole conversation, so it cuts what sits in context, and it catches the two ways agents actually get stuck: misreading short prompts and re-testing ideas that already failed.

## What it does

| When | Piece | Does |
|---|---|---|
| install | tool search + 2k-char contract | Tool schemas load on demand (Claude Code disables this behind a proxy; forcing it on cuts the prefix 63k → 17k tokens). Rules: verdict first, batch calls, delegate exploration, verify before "done". −18% per task at equal pass rate |
| session start | `lessons` | Injects rules from your past corrections, per repo and global. A correction made once is followed in every later session |
| prompt | `prompt_guard` | Short or ambiguous prompt → agent restates its reading before acting. Implementation prompt with unknowns → lists its assumptions and how it will check them |
| tool call | `guard` | Denies `rm -rf ~`, `curl \| sh`, force-push, `reset --hard`, reading or writing secrets. Parses the command, so `sh -c` doesn't slip past. 0.45% of real calls |
| tool call | `squeeze` | Big Bash output keeps errors, verdicts, head and tail; filler and secrets stripped; full text saved to a file the agent can grep. 138KB of test noise → 1.6KB |
| tool call | `research_log` | Logs every web search per repo. A near-duplicate query is denied once with the earlier one, so the agent changes angle |
| tool failure | `lessons` | Injects past lessons whose words match the error |
| stop | `verify` | Runs your tests and blocks "done" once on failures new since the session started. Names changed functions with no test |
| stop | `review` | A fresh-context `claude -p` gets only the task and the diff, reports correctness gaps, blocks once. 6 s, 2¢ |
| always | statusline | Context vs compact window, cache hit rate, cost |

Plus `agentmaxx doctor` (reads your transcripts: where tokens go, what the fixed prefix is made of, which CLAUDE.md is fat; `--apply` writes the fixes). Skills: `research` (stop criteria up front, per-repo hypothesis map, one disconfirming query per plan), `claude-md` (57k → 4.1k tokens, nothing deleted), `fast-commit`, `human-voice`, `spec-first`, `verify-pr`, `better-tools` (21 bounded CLI tools). An opencode plugin, and GrayMatter for cross-session memory.

## Install

```bash
make install && agentmaxx doctor
```

Restart agents. Off switches: `AGENTMAXX_{VERIFY,REVIEW,PROMPT_GUARD,RESEARCH_LOG}=0`. Per-repo instead of global: `agentmaxx init`. Method and numbers: [evals/RESULTS.md](evals/RESULTS.md).

Layout: `agentmaxx.py` CLI · `providers/` · `templates/CLAUDE.md` · `hooks/` · `tools/` · `skills/` · `integrations/opencode/` · `mcp/` (Codex) · `evals/`
