# agentmaxx

Token-efficiency tooling for coding agents (Claude Code, Codex, OpenCode).

An **agent navigation layer for codebases**: helps agents discover the minimum necessary code
for a task instead of exploring blindly. Combines a strict output contract with ranked search,
bounded output, and batch operations so agents spend fewer round trips and less context per task.

## Install

```bash
make install
```

This bootstraps the `agentmaxx` CLI to `~/.local/bin`, then installs into every detected
provider's global config (`~/.claude`, `~/.codex`) — machine-wide, so every repo picks it up
with no per-repo step:

| What | Where |
|---|---|
| Output contract | `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.config/opencode/AGENTS.md` (appended between markers) |
| `better-*` tools | `~/.claude/agentmaxx/tools`, `~/.codex/agentmaxx/tools`, `~/.config/opencode/agentmaxx/tools` |
| Skills | `~/.claude/skills`, `~/.codex/skills`; opencode reuses `~/.claude/skills` (which it discovers natively) and copies only missing ones into `~/.config/opencode/skills` |

Re-run it after changing `templates/`, `tools/`, or `skills/`: install always overwrites. Tools
deleted here are removed from the install, and the contract is rewritten in place between its
`agentmaxx:start` / `agentmaxx:end` markers, leaving your own instructions around it untouched.

## Use in a repo

```bash
cd your-project
agentmaxx init
```

`install` already covers every repo on the machine. `init` is only for scoping the contract to
one repo instead: it writes the same block into your own uncommitted rules file —
`CLAUDE.local.md` for Claude, `AGENTS.override.md` for Codex — and excludes it via
`.git/info/exclude` (per-clone, untracked). It never touches the repo's shared `CLAUDE.md` /
`AGENTS.md` or its `.gitignore`, so it can't change what teammates get. Re-running it refreshes
the block in place, same as `install`. `init` skips opencode: its custom instruction
files require entries in a committed `opencode.json`, which init never touches — its
global install already covers every repo.

## Layout

| Path | What |
|---|---|
| `agentmaxx.py` | CLI: `install` (global) and `init` (per-repo) |
| `providers/` | Per-agent-provider config: global root, personal rules filename |
| `templates/CLAUDE.md` | The injected output contract + tool reference + exploration workflow |
| `tools/` | The `better-*` CLI tools; `registry.yaml` is their source of truth |
| `tools/better-explore/` | Discovery agent: ranks candidates to guide exploration (reduces dead-end investigation) |
| `skills/` | Claude Code skills installed globally |
| `skills/explore/` | Documentation for using better-explore in a task workflow |
| `evals/` | Weighted token-cost scorer for A/B testing changes; a dev utility, never installed or agent-facing |

## Why this matters

Every agent round trip re-sends all accumulated context — the cost scales as **turns × context_size**, not just tokens.

Prose caps (`CLAUDE.md`) cut visible output tokens. Mechanical efficiency (bounded tools, batching, exploration ranking) cuts context cost, which is often 3–5× larger than output cost.

Three types of savings:

1. **Bounded output** — never dump raw `rg` output or entire files
2. **Batching** — one call with multiple patterns/files/edits instead of one call each
3. **Ranked discovery** — `better-explore` eliminates dead-end investigation

See `tools/README.md` for the tool contract and `templates/CLAUDE.md` for the injected rules.

## Agent workflow

When an agent (Claude Code, Codex, OpenCode) is installed with agentmaxx:

1. Receives a task
2. If the codebase is unfamiliar, runs `better-explore` to get ranked candidates
3. Reads the top candidate with `better-context`
4. Discovers imports/calls and narrows the scope
5. Makes the change with `better-edit`
6. Verifies with `better-check`

The key shift: **ranked search + bounded output + batch operations** replaces **undifferentiated search + full file reads + one edit per change**.
