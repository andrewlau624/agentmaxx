# agentmaxx

Coding agents waste money in predictable ways. They grep into dead ends and read five wrong files before finding the right one. They paste whole files into context. And because every turn re-sends the whole conversation, each of those habits gets billed dozens of times over.

agentmaxx is the guardrail set I install across Claude Code, Codex, and OpenCode to make them stop. It's built around one fact from measuring my own transcripts (see [evals/RESULTS.md](evals/RESULTS.md)): **the bill is resident context times turns.** In the last 14 days my median request carried 153k tokens and started from an 87k-token fixed prefix. Of that prefix, 28k was my own CLAUDE.md files and 8k the skill listing. Cache writes were 45% of the bill, and 47% of those writes were the same prefix being rewritten mid-session.

What it installs:

1. **Settings that shrink resident context.** `ENABLE_TOOL_SEARCH=true` defers tool schemas (Claude Code silently turns this off behind any proxy `ANTHROPIC_BASE_URL`; forcing it back on took the bench prefix from 63k to 17k tokens). Values you've already set win. The full 1M context is left alone.
2. **A short output contract** (~2k chars, down from 11k) in each provider's global rules file: verdict first, no narration between tool calls, batch independent calls, delegate broad exploration, verify before claiming done.
3. **Hooks** (Claude Code):
   - `squeeze`: large Bash output keeps errors, failures, summary lines, head and tail, and folds repeated log blocks. The full text is saved to a file the agent can grep. Test runners, package managers, builds, `git status`/`log` and listings squeeze above 3k chars; file dumps (`sed`, `cat`, `grep`, python heredocs) only above 8k, because cutting the middle of a file the agent asked for costs a re-read. Filler is dropped everywhere (pytest dots, pip and npm download lines, git hints, diff index lines, `ls -l` permission columns, ANSI codes) and secret-looking values (AWS, GitHub, Slack, Anthropic and OpenAI keys, JWTs, private keys, `user:pass@` URLs) are redacted on every Bash output. 138KB of test noise becomes 1.6KB.
   - `guard`: denies `rm -rf ~`, `curl | sh`, force-push, pushes to main, `git reset --hard`, reading `.env`/keys, and writing live credentials into files. It parses commands, so `/bin/rm` and `sh -c '...'` don't slip past.
   - `verify`: before the agent says it's done, runs your tests. It only blocks on failures that weren't already failing when the session started, and it blocks at most once.
   - `lessons`: when you correct the agent, it records the rule as one line. Every later session in that repo starts with it, across clones and worktrees.
   - A statusline: context used against the compact window, cache hit rate, cost.
4. **`agentmaxx doctor`** reads your transcripts and tells you which of these matter on your machine, with numbers: where the cost goes, what the fixed prefix is made of (your CLAUDE.md files, the skill listing, MCP instructions), which CLAUDE.md is over 8k tokens, what the subagent TTL, the compaction window and the main-thread TTL would cost you. `agentmaxx doctor --dry-run` previews writing the env-var recommendations to settings.json, and `--apply` does it: backup first, and it never overwrites a value you set.
5. Twenty-one `better-*` CLI tools (ranked search, bounded reads, batched edits, call graphs, parallel checks, output compression), described in an on-demand `better-tools` skill instead of the always-loaded contract. opencode and Codex still register them natively; Claude Code doesn't, because the bench showed the model never called them and the late-connecting MCP server forced full cache rewrites. One of them, `better-compress`, routes each output to the best compressor for its shape: JSON to headroom when installed, else a vendored crusher; logs and diffs through the squeeze engine. Its `--run` mode executes a command under lowfat.
6. **opencode plugin**: the same squeeze runs on `bash` and `grep` results after they return (opencode's own `tool_output.max_bytes` keeps only the tail and the built-in `grep` tool ignores it; I saw 65k-char grep results), plus a read guard that redirects whole-file reads over 12KB to ranged ones.

## Install

```bash
make install
agentmaxx doctor
```

Everything stages into `~/.agentmaxx`, then each detected provider gets wired up. Restart your agents after — hosts only load plugins, hooks, and MCP servers at startup. Installs are idempotent: the contract lives between `agentmaxx:start/end` markers, agentmaxx only replaces its own hook entries in `settings.json` (a backup is written the first time), and lessons live in `~/.local/share/agentmaxx` so reinstalls never wipe them.

Turn pieces off per shell with `AGENTMAXX_VERIFY=0`, or pin the test command for a repo in `.agentmaxx/verify`. Squeeze thresholds are `AGENTMAXX_SQUEEZE_THRESHOLD` / `_BUDGET` (content, default 8000/6000) and `AGENTMAXX_SQUEEZE_NOISY_THRESHOLD` / `_NOISY_BUDGET` (default 3000/2000). Set `AGENTMAXX_SQUEEZE_ROUTER=1` to route outputs that parse as JSON through `better-compress`. Manage lessons with `python3 ~/.claude/agentmaxx/hooks/lessons.py list|vote ID up|down|rm ID`.

## Does it work

On a 6-task bench with hidden-test grading (Sonnet 5.5, 3 reps), compared with stock Claude Code behind a proxy:

| Setup | Pass | Cost per task |
|---|---|---|
| old agentmaxx (long contract + MCP tools) | 12/12 | +89% |
| tool search on | 18/18 | −16% |
| agentmaxx v2 | 18/18 | −18% |

Replaying 14 days of my own sessions (61 main, 274 subagents, 15,530 requests):

| Finding | Number |
|---|---|
| Fixed prefix, median first request | 86.9k tokens |
| of which my CLAUDE.md files / skill listing (per session) | 28.0k / 7.8k |
| CLAUDE.md re-attached mid-session | 20.1k tokens per session |
| Largest single CLAUDE.md | 192k chars, 43k tokens, on every request and every subagent |
| Cache-write tokens that were mid-session prefix rewrites | 47% (24% main thread idle >1h, 19% subagents on the 5m TTL, 3% compaction). Moving subagents to 1h would cost +19%, so that one stays |
| Thinking, as a share of billed output | 32% |
| Bash outputs over 2k chars that were file dumps (`sed`, `cat`, `grep`, heredocs) | 2,123 of 3,567, 9.0 of 15.0MB |
| Same, from commands lowfat ships filters for (`git`, `docker`, `ls`, `find`) | under 5% of the volume |

The squeezer, replayed over 6,541 Bash outputs with the shipped defaults, touches 0.3% of them and keeps 91% of error and verdict lines in the ones it touches. Set the content threshold to 3k and it touches 11.7%, cuts resident Bash chars by 22% (35% in subagents), and keeps 71% of verdict lines. Of 693 outputs the earlier version squeezed, 0 were re-run verbatim and 34 were followed by a grep of the spill file. With lessons, a correction made once was followed in 5/5 fresh sessions, against 0/5 without.

Method, caveats, and what didn't work are in [evals/RESULTS.md](evals/RESULTS.md). Re-run any of it: `python3 evals/bench/run.py base v2 --reps 3`, `python3 evals/squeeze_replay.py`, `python3 evals/compress_bench.py`, `python3 evals/doctor.py`.

## Compared with lowfat

[lowfat](https://github.com/zdk/lowfat) is a Rust CLI that rewrites `git status` into `lowfat git status` through a PreToolUse hook and filters known commands with a per-command DSL (git −62%, `ls -la` −75% on its samples). It also compresses file contents after `Read`: strips comments, collapses function bodies, summarizes lock files. Two of its ideas are in here now: command-aware filtering and secret redaction on tool output, plus the opencode after-hook. Two are deliberately not:

- **Rewriting the command** only fires when the first word is a known command. My agent's Bash calls are `cd repo && sed -n 40,120p x.py | grep -n foo; wc -l y` chains, and `git`/`docker`/`ls`/`find` were under 5% of oversized output. Squeezing the result after it returns sees every command, keeps the exit status and stderr, and can't break a pipeline.
- **Lossy Read compression** strips comments the model will then try to match with `Edit`, which needs the exact text. Reads are already small here (Bash is 82% of result bytes, Read 11%); the guard that matters is refusing whole-file reads, which the opencode plugin does and the contract asks for.

Command wrapping exists only as the explicit `better-compress --run` CLI, never in the hook path.

## What else comes with it

- **code-review** skill that remembers your review nits and style preferences in plain markdown, with a probation system so the list never bloats
- **fast-commit** skill: one call gathers git state, one silent step writes the message, one call commits
- **human-voice** skill, distilled from Wikipedia's "Signs of AI writing", for docs and anything else that should read like a person wrote it
- [GrayMatter](https://github.com/angelnicolasc/graymatter) wired in for cross-session memory (add more external tools to `external/tools.json`; `make install` handles them)
- `make prune`, which strips unused gstack skills whose descriptions would otherwise ride along in every request
- `make telemetry` for per-session tokens and API-equivalent cost across Claude Code, Codex, and opencode
- `make compress-deps` for the optional `better-compress` backends: headroom (JSON crush) into `~/.agentmaxx/.venv`, lowfat (command wrap) into `~/.local/bin`

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
| `hooks/` | Claude Code hooks (guard, squeeze, verify, lessons, inject_scan) and statusline |
| `tools/` | The `better-*` tools |
| `skills/` | Skills shipped to every provider |
| `integrations/opencode/` | opencode plugin: better-* tools, read guard, output squeeze |
| `mcp/` | MCP stdio server for Claude Code / Codex |
| `external/` | Third-party tool manifest, installer, gstack pruner |
| `evals/` | `doctor`, telemetry, `squeeze_replay`, `compress_bench`, the A/B bench, and [RESULTS.md](evals/RESULTS.md) |
