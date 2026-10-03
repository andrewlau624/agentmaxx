# agentmaxx

Coding agents waste money in predictable ways. They grep into dead ends and read five wrong files before finding the right one. They narrate every step. They paste whole files into context. And because every turn re-sends the whole conversation, each of those habits gets billed dozens of times over.

agentmaxx is the guardrail set I install across Claude Code, Codex, and OpenCode to make them stop. After measuring where my own money went (see [evals/RESULTS.md](evals/RESULTS.md)), it's built around one fact: **the bill is resident context times turns.** Cache reads were 65% of my weighted cost, the median request carried 266k tokens, and every session started with an 86k-token prefix of tool schemas before doing anything.

What it installs:

1. **Settings that shrink resident context.** `ENABLE_TOOL_SEARCH=true` defers tool schemas (Claude Code silently turns this off behind any proxy `ANTHROPIC_BASE_URL`; forcing it back on took my prefix from 63k to 17k tokens). `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000` stops 1M-context models from carrying ~1M tokens before compacting. Values you've already set win.
2. **A short output contract** (~1.8k chars, down from 11k) in each provider's global rules file: verdict first, no narration between tool calls, batch independent calls, delegate broad exploration, verify before claiming done.
3. **Hooks** (Claude Code):
   - `squeeze`: large Bash output keeps errors, tracebacks, head and tail, and folds repeated log blocks. The full log is saved to a file the agent can grep. 138KB of test noise becomes 1.6KB.
   - `guard`: denies `rm -rf ~`, `curl | sh`, force-push, pushes to main, `git reset --hard`, reading `.env`/keys, and writing live credentials into files. It parses commands, so `/bin/rm` and `sh -c '...'` don't slip past.
   - `verify`: before the agent says it's done, runs your tests. It only blocks on failures that weren't already failing when the session started, and it blocks at most once.
   - `lessons`: when you correct the agent, it records the rule as one line. Every later session in that repo starts with it, across clones and worktrees.
   - A statusline: context used against the compact window, cache hit rate, cost.
4. **`agentmaxx doctor`** reads your transcripts and tells you which of these matter on your machine, with numbers.
5. Twenty `better-*` CLI tools (ranked search, bounded reads, batched edits, call graphs, parallel checks), described in an on-demand `better-tools` skill instead of the always-loaded contract. opencode and Codex still register them natively; Claude Code doesn't, because the bench showed the model never called them and the late-connecting MCP server forced full cache rewrites.

## Install

```bash
make install
agentmaxx doctor
```

Everything stages into `~/.agentmaxx`, then each detected provider gets wired up. Restart your agents after — hosts only load plugins, hooks, and MCP servers at startup. Installs are idempotent: the contract lives between `agentmaxx:start/end` markers, agentmaxx only replaces its own hook entries in `settings.json` (a backup is written the first time), and lessons live in `~/.local/share/agentmaxx` so reinstalls never wipe them.

Turn pieces off per shell with `AGENTMAXX_VERIFY=0`, or pin the test command for a repo in `.agentmaxx/verify`. Manage lessons with `python3 ~/.claude/agentmaxx/hooks/lessons.py list|vote ID up|down|rm ID`.

## Does it work

On a 6-task bench with hidden-test grading (Sonnet 5.5, 3 reps), compared with stock Claude Code behind a proxy:

| Setup | Pass | Cost per task |
|---|---|---|
| old agentmaxx (long contract + MCP tools) | 12/12 | +89% |
| tool search on | 18/18 | −16% |
| agentmaxx v2 | 18/18 | −18% |

Replaying 14 days of my real sessions, the compact window alone cuts about 25% of the bill. The squeezer cuts resident Bash output by 28%. With lessons, a correction made once was followed in 5/5 fresh sessions, against 0/5 without.

Method, caveats, and what didn't work are in [evals/RESULTS.md](evals/RESULTS.md). Re-run any of it: `python3 evals/bench/run.py base v2 --reps 3`.

## What else comes with it

- **code-review** skill that remembers your review nits and style preferences in plain markdown, with a probation system so the list never bloats
- **fast-commit** skill: one call gathers git state, one silent step writes the message, one call commits
- **human-voice** skill, distilled from Wikipedia's "Signs of AI writing", for docs and anything else that should read like a person wrote it
- [GrayMatter](https://github.com/angelnicolasc/graymatter) wired in for cross-session memory (add more external tools to `external/tools.json`; `make install` handles them)
- `make prune`, which strips unused gstack skills whose descriptions would otherwise ride along in every request
- `make telemetry` for per-session tokens and API-equivalent cost across Claude Code, Codex, and opencode

## Per-repo scoping

The global install covers everything already. To scope the contract to a single repo instead:

```bash
cd your-project && agentmaxx init
```

That writes your personal rules file (`CLAUDE.local.md` or `AGENTS.override.md`) and git-excludes it locally, so teammates see nothing.

## Layout

| Path | What |
|---|---|
| `agentmaxx.py` | CLI: `install`, `init`, `doctor` |
| `providers/` | Per-host detection, wiring, native tool registration |
| `templates/CLAUDE.md` | The injected contract |
| `hooks/` | Claude Code hooks (guard, squeeze, verify, lessons) and statusline |
| `tools/` | The `better-*` tools |
| `skills/` | Skills shipped to every provider |
| `integrations/opencode/` | opencode plugin + compaction hook |
| `mcp/` | MCP stdio server for Claude Code / Codex |
| `external/` | Third-party tool manifest, installer, gstack pruner |
| `evals/` | `doctor`, telemetry, the A/B bench, and [RESULTS.md](evals/RESULTS.md) |
