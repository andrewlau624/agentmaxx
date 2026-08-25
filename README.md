# agentmaxx

Coding agents waste money in predictable ways. They grep into dead ends and read five wrong files before finding the right one. They narrate every step. They paste whole files into context. And because every turn re-sends the whole conversation, each of those habits gets billed dozens of times over.

agentmaxx is the guardrail set I install across Claude Code, Codex, and OpenCode to make them stop. It has three parts:

1. An output contract injected into each provider's global rules file: verdict first, capped verbosity, no prose between tool calls.
2. Twenty small `better-*` CLI tools for ranked search, bounded reads, batched edits, and parallel checks. Each host registers them natively (MCP for Claude Code and Codex, a plugin for opencode) because registered tools actually get used; instructions in a rules file mostly don't.
3. Telemetry. One command reads the local databases and shows what each provider really spent. Changes here get judged against those numbers, not vibes.

## Install

```bash
make install
```

Everything stages into `~/.agentmaxx`, then each detected provider gets wired up. Detection checks config directories too, so a binary that's missing from PATH won't silently skip a provider. Restart your agents after — hosts only load plugins and MCP servers at startup.

Installs are idempotent and self-contained. The contract lives between `agentmaxx:start/end` markers, so your own rules survive every reinstall. Delete a tool from this repo and it disappears from all providers next run.

## What comes with it

- **code-review** skill that remembers your review nits and style preferences in plain markdown, with a probation system so the list never bloats
- **fast-commit** skill: one call gathers git state, one silent step writes the message, one call commits
- **human-voice** skill, distilled from Wikipedia's "Signs of AI writing", for docs and anything else that should read like a person wrote it
- [GrayMatter](https://github.com/angelnicolasc/graymatter) wired in for cross-session memory (add more external tools to `external/tools.json`; `make install` handles them)
- `make prune`, which strips unused gstack skills whose descriptions would otherwise ride along in every request

## Does it work

Measured on my own usage: fixed prompt overhead down about 40%, cache hit rate 86%, tool-result volume now the biggest remaining line item, which is exactly what the tools attack. Your numbers will differ. Run `make telemetry` and find out.

## Per-repo scoping

The global install covers everything already. To scope the contract to a single repo instead:

```bash
cd your-project && agentmaxx init
```

That writes your personal rules file (`CLAUDE.local.md` or `AGENTS.override.md`) and git-excludes it locally, so teammates see nothing.

## Layout

| Path | What |
|---|---|
| `agentmaxx.py` | CLI: `install` and `init` |
| `providers/` | Per-host detection, wiring, native tool registration |
| `templates/CLAUDE.md` | The injected contract |
| `tools/` | The `better-*` tools |
| `skills/` | Skills shipped to every provider |
| `integrations/opencode/` | opencode plugin + compaction hook |
| `mcp/` | MCP stdio server for Claude Code / Codex |
| `external/` | Third-party tool manifest, installer, gstack pruner |
| `evals/` | Telemetry and stability tests; dev-only |
