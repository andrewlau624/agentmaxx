# agentmaxx

Token-efficiency tooling for Claude Code, Codex, and OpenCode.

Coding agents burn most of their budget the same way: grepping into dead ends, reading whole files, narrating every step — then re-sending all of it on every turn. agentmaxx attacks the three places that cost compounds:

1. **A strict output contract**, injected into each provider's global rules. Verdict-first answers, capped verbosity, no mid-task narration.
2. **Twenty `better-*` tools** — ranked search, bounded file reads, atomic batched edits, parallel checks — installed per provider *and* registered natively (MCP or plugin) so agents actually reach for them instead of falling back to raw grep.
3. **Measurement** — one command reports real token spend across all three providers, so changes get judged on data instead of vibes.

## Install

```bash
make install
```

Stages everything to `~/.agentmaxx`, then wires every detected provider (by binary or config dir):

| What | Where |
|---|---|
| Output contract | `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md`, `~/.config/opencode/AGENTS.md` |
| Tools | `<provider config>/agentmaxx/tools` |
| Skills | `~/.claude/skills`, `~/.codex/skills` |
| Native tool registration | opencode plugin (`~/.config/opencode/plugins/better-tools.js`); MCP server for Claude Code (`~/.claude.json`) and Codex (`~/.codex/config.toml`) |

Restart your agents afterwards — hosts load plugins and MCP servers only at startup.

Re-run any time. Install overwrites its own blocks (delimited by `agentmaxx:start/end` markers) and leaves your own rules untouched; tools deleted from the repo disappear from the install too.

## Extras

```bash
make telemetry    # token spend per session/provider, cache hit rate, tool volume
make prune        # remove unused gstack skills — their descriptions tax every request
make test         # unit tests, including contract-stability guarantees
```

`make install` also installs third-party tools listed in `external/tools.json` — currently [GrayMatter](https://github.com/angelnicolasc/graymatter) for persistent cross-session memory. Adding another tool is one JSON entry: name, install command, wire command.

## Per-repo scoping

The global install covers every repo automatically. To scope the contract to one repo instead:

```bash
cd your-project && agentmaxx init
```

Writes your personal rules file (`CLAUDE.local.md` / `AGENTS.override.md`), excludes it via `.git/info/exclude`, and never touches anything your teammates would see.

## Why it works

Context cost scales as **turns × context size**: every byte resident in a session is re-sent, and re-billed, on every subsequent turn. The levers:

- **Bounded output** — never dump raw search results or entire files
- **Batching** — one call with many patterns, files, or edits beats one call each
- **Ranked discovery** — read the right file first instead of three wrong ones
- **Stable prefixes** — deterministic generation keeps provider prompt caches warm (86% hit rate measured)

Measured on real usage: fixed prompt overhead cut ~40% by compressing the contract and pruning dead skills; tool-result volume is the dominant remaining line item — exactly what the tools target.

## Layout

| Path | What |
|---|---|
| `agentmaxx.py` | CLI: `install` (global), `init` (per-repo) |
| `providers/` | Per-host config, detection, native tool registration |
| `templates/CLAUDE.md` | The injected contract |
| `tools/` | The `better-*` CLI tools |
| `skills/` | Agent skills shipped everywhere |
| `integrations/opencode/` | Plugin registering tools natively in opencode, plus compaction hook |
| `mcp/` | MCP stdio server registering tools natively in Claude Code / Codex |
| `external/` | Third-party tool manifest + installer, gstack skill pruner |
| `evals/` | Telemetry and stability tests — dev-only, never installed |
