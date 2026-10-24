# agentmaxx

A set of hooks, settings, skills and a measurement loop for Claude Code, Codex and OpenCode. Every change in here was first measured on this machine's own transcripts or on a live bench with hidden tests, and the numbers (good and bad) are kept in [evals/RESULTS.md](evals/RESULTS.md) and [evals/LEDGER.md](evals/LEDGER.md). Things that measured as a wash or a loss are not shipped, and the README says so.

It started as a cost project and became a quality project. The cost fact: an agent re-sends its whole conversation on every turn, so **the bill is resident context times turns**. On this machine, sessions start from an ~87k-token fixed prefix (28k of it my own CLAUDE.md files, 8k the skill listing), cache reads are 48% of spend, cache writes 38%, and output only 14%. The quality fact, from 151 real sessions over 30 days: there were zero command-level loops. The agent gets stuck in two other ways. It misreads short prompts (the top correction type, 23 of 68), and in research it concludes "nothing passes the bar" and re-tests the same idea in a new costume (59 such turns against 66 "keep going" replies).

## What it does, in the order a session meets it

**At install** (`make install`). Stages everything into `~/.agentmaxx`, then wires each detected host:

- Sets `ENABLE_TOOL_SEARCH=true` so tool schemas load on demand. Claude Code silently turns this off behind any proxy `ANTHROPIC_BASE_URL`; forcing it back on took the bench prefix from 63k to 17k tokens. Values you already set win, and the 1M context window is left alone.
- Writes a ~2k-char output contract (down from 11k) between `agentmaxx:start/end` markers in each host's global rules file: verdict first, no narration between tool calls, batch independent calls, run independent work at once, delegate broad exploration, verify before claiming done.
- Installs the hooks below into Claude Code's `settings.json`, replacing only its own entries (a backup is written the first time). Lessons and verify baselines live in `~/.local/share/agentmaxx`, so reinstalls never wipe them.

**At session start.** `lessons` injects the rules you have corrected the agent on before, for this repo and globally, up to 5k chars. Rules come from your corrections: when you say "no, use pnpm", the agent is nudged to record one imperative line, with a snippet of what it was correcting kept as evidence (never injected).

**On each prompt.** `prompt_guard` adds one line on short, deictic or typo'd prompts asking the agent to restate its reading before acting, and one line on implementation prompts with two or more unknowns asking it to list every assumption and how it will check each. Replayed on 1,886 real prompts it fires the first line on 18%, the second on 2%, and would have fired on 3 of the 4 misreads that cost real corrections.

**On each tool call.**

- `guard` denies `rm -rf ~`, `curl | sh`, force-push, `git reset --hard`, reading `.env` and key files, writing live credentials into files, and writing into git hooks. It parses the command, so `/bin/rm` and `sh -c '...'` do not slip past. Replayed on 14,846 real calls it denies 0.45%, and 61 of those were `cat .env`-style reads that printed live secrets into the transcript.
- `squeeze` trims large Bash output after it returns: keeps errors, failures, summary lines, head and tail, folds repeated log blocks, drops filler (pytest dots, download lines, git hints, ANSI), redacts secret-looking values, and saves the full text to a file the agent can grep. Test runners, builds and listings squeeze above 3k chars; file dumps only above 8k, because cutting a file the agent asked for costs a re-read. 138KB of test noise becomes 1.6KB. Of 693 squeezed outputs, 0 were re-run verbatim.
- `research_log` keeps a per-repo log of every web search. A query that near-duplicates one already run, in this session or an earlier one, is denied once with the prior query and date so the agent changes angle. Replayed on 530 real queries it would have denied 10, of which 8 were genuine repeats.
- `lessons` (on a failed Bash or edit) injects up to three past lessons whose words match the error, once per session.
- `inject_scan` flags prompt-injection shapes in fetched content.

**When the agent says it is done.**

- `verify` runs your tests (autodetected, or pinned in `.agentmaxx/verify`). It blocks only on failures that were not already failing when the session started, and at most once. It also names changed functions that have callers but no test mentioning them, so "done" has to say what was and was not exercised.
- `review` hands the task and the diff, and nothing else, to a fresh-context reviewer (`claude -p`, Sonnet by default) that reports correctness and requirement gaps only. It blocks at most once per session and never blocks on a reviewer failure. About 6 s and 2 cents a run; it caught a real empty-input bug on its first smoke run.
- A statusline shows context used against the compact window, cache hit rate and cost.

**Also shipped.** `agentmaxx doctor` reads your transcripts and reports, with numbers, where your cost goes, what the fixed prefix is made of, which CLAUDE.md is over 8k tokens, and what the compaction window and cache TTLs would cost you (`--apply` writes the env recommendations, backup first, never overwriting a value you set). Skills: `research` (sufficiency criteria before the first search, a per-repo hypothesis-space map, one disconfirming query and one source-type pivot per plan, a stop rule), `claude-md` (puts a fat CLAUDE.md on a diet without deleting anything), `fast-commit`, `human-voice`, `spec-first`, `verify-pr`, `design-system-ui`, and `better-tools`, which lists 21 `better-*` CLI tools. An opencode plugin squeezes `bash` and `grep` results and redirects whole-file reads over 12KB to ranged ones. [GrayMatter](https://github.com/angelnicolasc/graymatter) is wired in for cross-session memory.

## The numbers

Live A/B bench, hidden-test grading, Sonnet 5.5, 6 tasks, 3 reps, against stock Claude Code behind a proxy:

| Setup | Pass | Cost per task |
|---|---|---|
| old agentmaxx (110-line contract + MCP `better-*` server) | 12/12 | +89% |
| tool search on | 18/18 | −16% |
| tool search + lean contract + guard/squeeze/verify hooks (shipped) | 18/18 | −18% (90% CI −31% to −11%) |

The old version lost because the model never called a single `better-*` MCP tool when native Grep, Read and Edit were available, and the late-connecting MCP server forced two full cache rewrites per session. That is why Claude Code no longer registers them.

Real-repo bench: 10 SWE-bench-style tasks mined from sqlparse, mistune and boltons bug fixes ([evals/bench/real](evals/bench/real/README.md)). Opus 5.5 with the shipped setup passes 26/30 at $0.215 per task. Effort level `low` cuts cost 32% but costs a pass; `medium` is −1%, a wash. Neither ships. Sonnet subagents pass as often and cost −22%, but weaker subagents under a stronger parent were judged not worth 3% of the bill, so that is off by default too.

Replays over this machine's transcripts:

| What | Measured |
|---|---|
| Fixed prefix, median first request | 86.9k tokens, of which CLAUDE.md files 28.0k and skill listing 7.8k |
| Cache-write tokens that were mid-session prefix rewrites | 47% (idle main thread past the 1h TTL 24%, subagents on the 5m TTL 19%, compaction 3%) |
| `guard`, 14,846 real calls | 0.45% denied: 61 printed live secrets, 6 were `reset --hard`, `clean -f` or a force-push |
| `squeeze`, 6,541 Bash outputs, shipped thresholds | touches 0.3%, keeps 91% of error and verdict lines in those |
| `lessons`, fresh session after one correction (bench) | rule followed 5/5 with, 0/5 without; partly inferable rule 4/4 vs 2/4 |
| `lessons` correction detector, 73 labelled prompts (in-sample) | precision 67% → 91%, recall 58% → 96% |
| `prompt_guard`, 1,886 prompts | misread line 17.7%, assumption line 2.2%, 3 of 4 known misreads caught |
| `research_log`, 530 queries | 10 denied, 8 genuine repeats, 2 borderline |
| Research sessions that never searched for counter-evidence | 59 of 85 (70%) |
| Discovery before the first edit, 819 task episodes | median 1 tool call, p90 7, 6% needed 10 or more |
| Quality skills shipped before iteration 23 (assumption-check, explore, test-first, code-review, …) | 0 invocations in 30 days, so moved to `skills-optional/` |
| `claude-md` diet on the two fat files | 57k → 4.1k and 31k → 5.1k tokens, every line kept in `docs/memory/` |
| Auto-compact at 400k instead of ~967k, 30 days, real prices | −12.6% (~$360 of $2,861); 300k −15.5%; an earlier 14-day replay showed −18% |

Compaction is a trade: Haiku 4.5 forced to compact at ~40k passed 13/21 versus 17/20 without, so the window is a recommendation from `doctor`, not something install sets.

## What is not measured yet

- The `review` hook's false-positive rate on sound diffs. It has one smoke run.
- Whether the `research` skill and `research_log` change the research-loop numbers above (families tried per day, counter-evidence share, re-search rate). Needs 30 days of transcripts after install.
- The `verify` coverage note's effect; it has fired on name collisions once.
- Behavioral effect of the CLAUDE.md diet in the repos it was applied to.
- Each `better-*` tool individually. The only measurement is the bench above, where the model did not call them.

Things that were tested and did not help are listed in [evals/RESULTS.md](evals/RESULTS.md#what-didnt-help-or-wasnt-tested): effort level, Read dedupe, a test-cheating gate the bench could not tempt, and terse-output contracts beyond the lean one.

## Install

```bash
make install
agentmaxx doctor
```

Restart your agents after; hosts only load hooks and plugins at startup. Turn pieces off per shell with `AGENTMAXX_VERIFY=0`, `AGENTMAXX_REVIEW=0`, `AGENTMAXX_PROMPT_GUARD=0`, `AGENTMAXX_RESEARCH_LOG=0`, `AGENTMAXX_VERIFY_COVERAGE=0`. Squeeze thresholds are `AGENTMAXX_SQUEEZE_THRESHOLD` / `_BUDGET` (content, default 8000/6000) and `AGENTMAXX_SQUEEZE_NOISY_THRESHOLD` / `_NOISY_BUDGET` (default 3000/2000). `AGENTMAXX_REVIEW_MODEL` picks the reviewer model, `AGENTMAXX_OPTIONAL_SKILLS=1 make install` brings back the skills that never fired. Manage lessons with `python3 ~/.claude/agentmaxx/hooks/lessons.py list|vote ID up|down|rm ID`, and see recent searches with `python3 ~/.claude/agentmaxx/hooks/research_log.py recent`.

To scope the contract to one repo instead of globally, `cd your-project && agentmaxx init` writes `CLAUDE.local.md` or `AGENTS.override.md` and git-excludes it, so teammates see nothing.

Re-run any measurement: `python3 evals/bench/run.py base v2 --reps 3`, `python3 evals/squeeze_replay.py`, `python3 evals/guard_replay.py`, `python3 evals/corrections.py --days 30`, `python3 evals/doctor.py`. `make test` runs the unit tests for hooks, tools, evals and the claude-md skill.

## Compared with lowfat

[lowfat](https://github.com/zdk/lowfat) is a Rust CLI that rewrites `git status` into `lowfat git status` through a PreToolUse hook and filters known commands with a per-command DSL (git −62%, `ls -la` −75% on its samples). It also compresses file contents after `Read`. Two of its ideas are in here: command-aware filtering and secret redaction on tool output, plus the opencode after-hook. Two are deliberately not:

- **Rewriting the command** only fires when the first word is a known command. My agent's Bash calls are `cd repo && sed -n 40,120p x.py | grep -n foo; wc -l y` chains, and `git`/`docker`/`ls`/`find` were under 5% of oversized output here. Squeezing the result after it returns sees every command, keeps the exit status and stderr, and cannot break a pipeline.
- **Lossy Read compression** strips comments the model will then try to match with `Edit`, which needs the exact text. Reads are already small here (Bash is 82% of result bytes, Read 11%).

Command wrapping exists only as the explicit `better-compress --run` CLI, never in the hook path.

## Layout

| Path | What |
|---|---|
| `agentmaxx.py` | CLI: `install`, `init`, `doctor` |
| `providers/` | Per-host detection and wiring for Claude Code, Codex, opencode |
| `templates/CLAUDE.md` | The injected contract |
| `hooks/` | Claude Code hooks (guard, squeeze, verify, lessons, inject_scan, prompt_guard, research_log, review) and the statusline, each with tests |
| `tools/` | The 21 `better-*` CLI tools |
| `skills/` | Skills shipped to every provider; `skills-optional/` holds the ones that never fired |
| `integrations/opencode/` | opencode plugin: better-* tools, read guard, output squeeze |
| `mcp/` | MCP stdio server for Codex (Claude Code no longer uses it) |
| `external/` | Third-party tool manifest, installer, gstack pruner |
| `evals/` | `doctor`, telemetry, replays, the A/B bench, [RESULTS.md](evals/RESULTS.md), [LEDGER.md](evals/LEDGER.md), [quality-research.md](evals/quality-research.md) |
