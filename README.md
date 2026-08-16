# agentmaxx

Token-efficiency tooling for coding agents (Claude Code, Codex): an output contract that caps
verbosity, and a set of bounded, batchable search/read tools so agents spend fewer round trips
per task.

## Install

```bash
make install
```

This bootstraps the `agentmaxx` CLI to `~/.local/bin` and installs skills + tools into every
detected provider's global config (`~/.claude`, `~/.codex`) — a one-time, machine-wide step.

## Use in a repo

```bash
cd your-project
agentmaxx init
```

`init` is personal and per-repo. It writes the output contract into your own uncommitted rules
file — `CLAUDE.local.md` for Claude, `AGENTS.override.md` for Codex — and excludes it via
`.git/info/exclude` (per-clone, untracked). It never touches the repo's shared `CLAUDE.md` /
`AGENTS.md` or its `.gitignore`, so it can't change what teammates get. Safe to re-run; add
`--force` to pick up template or tool changes.

## Layout

| Path | What |
|---|---|
| `agentmaxx.py` | CLI: `install` (global) and `init` (per-repo) |
| `providers/` | Per-agent-provider config: global root, personal rules filename |
| `templates/CLAUDE.md` | The injected output contract + tool reference |
| `tools/` | The `better-*` CLI tools; `registry.yaml` is their source of truth |
| `skills/` | Claude Code skills installed globally |

## Why a tool matters as much as the prompt

Prose caps cut the visible cost — output tokens. The larger cost is usually context: every tool
round trip re-sends the whole accumulated conversation. The `better-*` tools cut that cost two
ways: bounded output (never dump a whole file or raw `rg` output), and batching (one call takes
multiple files, ranges, or patterns instead of one call each). `better-context` composes search
and read into a single call for the single most common two-step pattern.

See `tools/README.md` for the tool contract and `templates/CLAUDE.md` for the injected rules.
