# Codex and opencode parity research

Researched 2026-10-03. The goal: find the Codex CLI and opencode config keys that match the Claude Code settings agentmaxx ships in `providers/claude.py`. Those settings are `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000`, `ENABLE_TOOL_SEARCH=true`, the `squeeze.py` PostToolUse hook on Bash (8000-char threshold, full output spilled to a file), the guard/verify/lessons hooks, and effort.

## What was checked, and against which build

Neither CLI is on PATH (`which codex opencode` finds nothing), but both are installed:

- Codex: `/Applications/Codex.app/Contents/Resources/codex`, which reports `codex-cli 0.142.5`.
- opencode: the desktop app `/Applications/OpenCode.app` is 1.18.31, and `~/.config/opencode` pins `@opencode-ai/plugin` 1.18.31. To get a matching CLI, I installed `opencode-ai@1.18.31` from npm into the scratchpad. npm latest is 1.18.34.
- `~/.opencode/bin/opencode2` is an OpenCode 2.0 preview (`v0.0.0-beta-19425`) with a different config layer (`v2-compat.ts`). I did not test against it.

Source was read from shallow clones of main:

- openai/codex at `3e23877` (2026-10-03)
- sst/opencode at `907b3bc` (2026-10-02)

Link bases used in the tables:

- CX = `https://github.com/openai/codex/blob/3e23877/codex-rs`
- OC = `https://github.com/sst/opencode/blob/907b3bc/packages`

How each key was verified:

- "ran it" for Codex means a scratch `CODEX_HOME` with a deliberately wrong-typed value, run through `codex features list`. A typed error naming the key proves the installed binary knows it. Codex silently ignores unknown top-level keys, so "accepted" alone proves nothing. Three keys took bad values without error on 0.142.5: `model_post_turn_compact_threshold_percent`, `mcp_servers.<id>.tools.<tool>.output_token_limit` and `made_up_key_xyz`. That means the first two are on main only.
- "ran it" for opencode means `opencode debug config --pure` with `OPENCODE_CONFIG` pointing at a test file. Invalid values fail with "Configuration is invalid". Unknown keys inside a known object are silently stripped: `compaction.threshold` came back as `{}`.

Docs were read at learn.chatgpt.com/docs/config-file/config-reference (developers.openai.com/codex/config-reference now 308-redirects there), learn.chatgpt.com/docs/hooks, opencode.ai/docs/config and opencode.ai/docs/plugins.

## What agentmaxx installs today (read only)

For Codex, `providers/codex.py` does four things:

- Writes the contract into `~/.codex/AGENTS.md` (global) and `AGENTS.override.md` (per repo, git-excluded).
- Copies skills to `~/.codex/skills`.
- Copies tools to `~/.codex/agentmaxx/tools`.
- Appends `[mcp_servers.agentmaxx]` (python3 `mcp/better_mcp.py`) to `~/.codex/config.toml`.

It sets no compaction, output, effort or hook keys.

For opencode, `providers/opencode.py` writes the contract into `~/.config/opencode/AGENTS.md`, copies tools, and copies only the skills that `~/.claude/skills` does not already provide. It also installs `integrations/opencode/better-tools.js` into `~/.config/opencode/plugins/`. That plugin:

- Registers 19 `better_*` tools.
- Has a `tool.execute.before` hook that throws on whole-file `read` calls over 12 KB, which blocks the read.
- Has an `experimental.session.compacting` hook that pushes a "Working state" block into the compaction context.

It writes no `opencode.json` keys (`compaction`, `tool_output`, effort). `templates/` holds only `CLAUDE.md` (the contract). The repo-root `opencode.jsonc` only wires the graymatter MCP server for this repo's own development and is not installed anywhere.

## 1. Auto-compaction threshold

| Tool | Key | Type / accepted values | Default | Source | Verified | Recommendation |
|---|---|---|---|---|---|---|
| Codex | `model_auto_compact_token_limit` | integer (i64), tokens | Unset: 90% of the resolved context window. A set value is clamped to `min(value, 0.9 * context_window)`. | CX/protocol/src/openai_models.rs#L526-L537; CX/models-manager/src/model_info.rs#L29-L31; CX/core/config.schema.json#L7577; docs config-reference, "config.toml" table | docs, source, ran it (0.142.5: `expected i64`) | Do not set 300000. Every model in the 0.142.5 catalog has `context_window` 272000, so the default trigger is already about 244800 and 300000 would be clamped to a no-op. Only set it alongside `model_context_window`. |
| Codex | `model_context_window` | integer (i64) | Model catalog value (272000 for gpt-5.5, gpt-5.4 and the others in 0.142.5). It is capped at the model's `max_context_window` (1,000,000 for gpt-5.4). | CX/models-manager/src/model_info.rs#L20-L28 | source, ran it | Leave unset. Raising it is the only way past 272k, and the measured goal is to stay small. |
| Codex | `model_auto_compact_token_limit_scope` | `"total"` or `"body_after_prefix"` | `"total"` | CX/protocol/src/config_types.rs#L49-L55; CX/core/src/session/context_window.rs#L62-L80 | docs, source, ran it (0.142.5 rejects `bogus` with "expected `total` or `body_after_prefix`") | Leave at default. `total` matches Claude's semantics. |
| Codex | `model_post_turn_compact_threshold_percent` | integer 0-100 | 0 (disabled) | CX/core/config.schema.json (property description); CX/core/src/config/mod.rs#L646-L648 | source only. 0.142.5 accepted `"x"` without error, so it is not in the installed release. | Skip for now. It is main-only. |
| opencode | `compaction.auto` | boolean | true | OC/core/src/v1/config/config.ts#L149-L153; OC/opencode/src/session/overflow.ts#L22-L34; opencode.ai/docs/config "Compaction" | docs, source, ran it (1.18.31) | Leave default. |
| opencode | `compaction.reserved` | non-negative integer, tokens | `min(20000, model max output)` | OC/opencode/src/session/overflow.ts#L8-L20; config.ts#L164-L166 | docs, source, ran it (`-1` rejected) | Not a threshold. It only applies when the model defines `limit.input`. Otherwise the trigger is `context - maxOutputTokens`. |
| opencode | (no threshold key) | not applicable | not applicable | config.ts#L149-L168 has only auto, prune, tail_turns, preserve_recent_tokens, reserved | ran it (`compaction.threshold` silently stripped to `{}`) | There is no direct equivalent of `CLAUDE_CODE_AUTO_COMPACT_WINDOW`. |
| opencode | `provider.<id>.models.<model>.limit.{context,input,output}` | integers | From models.dev | OC/core/src/v1/config/provider.ts#L47; overflow.ts#L10-L20 | ran it (accepted and echoed back) | This is the only way to get a 300k trigger: `limit.input = 300000` compacts at about `300000 - reserved`. It also changes what opencode believes the model accepts, and it is per model id, so do not ship it by default. If wanted, offer it as an opt-in per model. |
| opencode | `compaction.tail_turns`, `compaction.preserve_recent_tokens` | non-negative integers | tail_turns: unbounded. preserve_recent_tokens: `clamp(0.25 * usable, 2000, 15000)`. | OC/opencode/src/session/compaction.ts#L32-L33, #L115-L120 | source, ran it. Not on opencode.ai/docs/config. | Leave default. |

## 2. Capping tool output that enters context

| Tool | Key | Type / accepted values | Default | Source | Verified | Recommendation |
|---|---|---|---|---|---|---|
| Codex | `tool_output_token_limit` | unsigned integer, tokens | Model `truncation_policy`, which is 10000 tokens for every model in 0.142.5. gpt-5.2 is in bytes mode with limit 10000. The key overrides the limit and keeps the mode. | CX/models-manager/src/model_info.rs#L32-L43; CX/core/config.schema.json#L7839; docs config-reference | docs, source, ran it (0.142.5: `expected usize`) | This applies to every tool's stored output, file reads included, so a squeeze-sized value (about 2000 tokens) would also cut reads. A moderate cap of 4000 is a reasonable start, but it needs a bench run before shipping. |
| Codex | truncation shape | Middle truncation. The budget is split evenly: head gets `budget/2`, tail gets the rest. A marker plus "Warning: truncated output (original token count: N) / Total output lines: M" is prepended. A 20% serialization allowance is added (`policy * 1.2`). | not applicable | CX/utils/string/src/truncate.rs#L39-L60, #L156-L159; CX/utils/output-truncation/src/lib.rs#L17-L41 | source | Tool output is not spilled to a file; the dropped middle is gone. Spill-to-disk exists only for hook `additionalContext` (`hook_outputs/`, 2500 tokens, CX/hooks/src/output_spill.rs#L11-L12). |
| Codex | `mcp_servers.<id>.tools.<tool>.output_token_limit` | integer >= 1 | unset | CX/core/config.schema.json, `McpServerToolConfig`; docs config-reference | docs, source. 0.142.5 accepted `"x"`, so it is main-only. | Later, cap `better_*` MCP outputs per tool. Not usable on 0.142.5. |
| Codex | PostToolUse hook as squeeze | see item 4 | not applicable | CX/core/src/tools/registry.rs#L747-L777 | source, docs | This is the closest match to squeeze.py: match `Bash`, and the hook's reason text replaces the model-visible result. The hook must write the spill file itself. |
| opencode | `tool_output.max_lines` | positive integer | 2000 | OC/core/src/v1/config/config.ts#L136-L148; OC/opencode/src/tool/truncate.ts#L14-L15, #L76-L84 | source, ran it (1.18.31; `max_bytes: 0` rejected). Not on opencode.ai/docs/config. | See max_bytes. |
| opencode | `tool_output.max_bytes` | positive integer | 51200 | same | same | Ship `"tool_output": {"max_bytes": 8000}`. When output exceeds the cap, opencode already writes the full text to its truncation dir and tells the model the path, which is the same contract as squeeze.py. The shell tool keeps the tail (`...output truncated...\n\nFull output saved to: <file>`, OC/opencode/src/tool/shell.ts#L569-L579). Other tools keep the head (truncate.ts#L95-L104). The limit applies to all tools, including `read`. |
| opencode | `compaction.prune` | boolean | false | config.ts#L154-L156; OC/opencode/src/session/compaction.ts#L28-L31, #L273-L318; docs "Compaction" | docs, source, ran it (`"yes"` rejected) | Leave false until measured. It clears completed tool outputs older than the last 40k tokens of tool output (2 user turns are protected, as are `skill` outputs). It only fires if more than 20k tokens would be freed, and it runs after each loop (prompt.ts#L1338). Editing old history breaks the cached prefix, so the net effect on cost is unknown. |

## 3. Lazy tool loading / tool search

| Tool | Key | Type / accepted values | Default | Source | Verified | Recommendation |
|---|---|---|---|---|---|---|
| Codex | none (built in) | The feature flags `tool_search` and `tool_search_always_defer_mcp_tools` have `Stage::Removed`. Per the docs, setting either to `false` is rejected in cloud mode. | On whenever the model has `supports_search_tool`, which is true for every model in the 0.142.5 catalog. MCP tools are then deferred, not sent directly. | CX/features/src/lib.rs#L248-L251, #L1475-L1485; CX/core/src/tools/spec_plan.rs#L267-L274, #L393-L400; docs config-reference compatibility table | source, ran it (`codex features list` shows `tool_search removed false`; `codex debug models` shows `supports_search_tool: true`) | Nothing to set. Codex already behaves like `ENABLE_TOOL_SEARCH=true` for MCP tools, including the agentmaxx MCP server. Expect the `better_*` tools to be discovered through search rather than listed up front. |
| opencode | none | not applicable | All enabled MCP tools are sent every request | No defer/tool-search code in OC/opencode/src or OC/core/src. `deferLoading` strings in the 1.18.31 binary come from the bundled AI SDK providers, not opencode config. | source, binary strings | Not available. The only lever is disabling tools: `tools: {"<server>_*": false}` globally, or the per-agent `permission`. |

## 4. Hooks

| Tool | Key / event | Type / accepted values | Default | Source | Verified | Recommendation |
|---|---|---|---|---|---|---|
| Codex | `features.hooks` (deprecated alias `features.codex_hooks`) | boolean | true (`Stage::Stable`) | CX/features/src/lib.rs#L1267-L1271; CX/features/src/legacy.rs#L49 | docs, source, ran it (`codex features list`: `hooks stable true`) | No need to set. |
| Codex | `[hooks]` in `~/.codex/config.toml`, or `~/.codex/hooks.json` | `hooks.<Event> = [{matcher, hooks=[{type="command", command, timeout, async, statusMessage}]}]`. The JSON shape is the same as Claude's settings.json hooks. | none | CX/core/config.schema.json#L7479 (`HooksToml`, `MatcherGroup`, `HookHandlerConfig`); CX/hooks/src/engine/discovery.rs#L339-L387 | docs, source, ran it (`hooks = 5` gives "expected struct HooksToml"; a full PostToolUse table parsed) | Install the hooks into `~/.codex/hooks.json` with the same scripts. Use one form per layer: Codex warns when both exist. |
| Codex | Events | 0.142.5 binary: PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact, SessionStart, UserPromptSubmit, SubagentStart, SubagentStop, Stop. Main and the docs add SessionEnd and Interrupt. | not applicable | CX/hooks/schema/generated/; binary strings (`HookEventsToml`) | source, docs, binary strings | Every event agentmaxx uses (PreToolUse, PostToolUse, SessionStart, Stop, UserPromptSubmit) exists in 0.142.5. |
| Codex | Matchers | Regex. Shell and `exec_command` match as `Bash`. `apply_patch` matches as `apply_patch`, `Edit` or `Write`. MCP tools match as `mcp__server__tool`. Stop and UserPromptSubmit ignore matchers. | not applicable | CX/core/src/tools/hook_names.rs#L37-L55; docs hooks "Matcher patterns" | source, docs | Claude's matchers mostly carry over. `Read` and `MultiEdit` have no Codex counterpart, so guard.py will only see Bash and apply_patch. |
| Codex | Trust gate | User and project hooks run only after the user trusts the exact hook hash: `[hooks.state."<id>"] trusted_hash`, set via `/hooks` in the TUI. The `--dangerously-bypass-hook-trust` flag skips this. | untrusted, skipped | CX/hooks/src/engine/discovery.rs#L715-L721, #L796-L823; docs hooks "Review and trust hooks"; `codex --help` | source, docs, ran it (flag present in 0.142.5) | Installed hooks are inert until the user approves them in `/hooks`. agentmaxx should print that instruction and not try to forge `trusted_hash`. |
| Codex | PreToolUse output | `hookSpecificOutput.permissionDecision: "deny"` with a reason, legacy `decision:"block"`, or exit 2 with stderr: any of these blocks. `permissionDecision:"allow"` with `updatedInput` rewrites the input. `ask`, `continue:false` and `suppressOutput` are parsed but unsupported. | not applicable | CX/core/src/hook_runtime.rs#L183-L240; CX/hooks/schema/generated/pre-tool-use.command.output.schema.json | source, docs | guard.py works as is if it emits Claude-style deny JSON. |
| Codex | PostToolUse output | `decision:"block"` with `reason`, or exit 2 with stderr: the model sees the reason as a failed tool result. `continue:false` with `reason`: the model-visible result is replaced by the reason, with no error flag and no stop to the turn. `updatedMCPToolOutput` is parsed but unsupported, so the hook is marked failed and the original output passes through. | not applicable | CX/core/src/tools/registry.rs#L747-L777; CX/hooks/src/events/post_tool_use.rs#L200-L268; docs hooks "PostToolUse" | source, docs. Not run end-to-end: that needs a live model session. | Port squeeze.py for Codex by emitting `{"continue": false, "reason": <squeezed text + spill path>}`. Note that Claude's `updatedToolOutput`-style rewrite is not available. Confirm on 0.142.5 with one real session before shipping. |
| Codex | Stop output | `decision:"block"` with `reason`, or exit 2: Codex continues with the reason as a new prompt. `continue:false` overrides that. | not applicable | docs hooks "Stop"; CX/hooks/schema/generated/stop.command.output.schema.json | docs, source | verify.py's Stop behaviour carries over. |
| opencode | `tool.execute.before` | `(input {tool, sessionID, callID}, output {args})`. Mutating `output.args` rewrites the call. Throwing blocks it, and the error message becomes the tool result. | not applicable | OC/plugin/src/index.ts#L266; OC/opencode/src/session/tools.ts#L105-L110; docs plugins ".env protection" | docs, source, plugin 1.18.31 types | Already used by better-tools.js. |
| opencode | `tool.execute.after` | `(input {tool, sessionID, callID, args}, output {title, output, metadata})`. Mutating `output.output` changes what the model sees. It runs after built-in truncation, so it sees the preview plus the saved-file path. | not applicable | OC/plugin/src/index.ts#L274; OC/opencode/src/session/tools.ts#L111-L127; OC/opencode/src/tool/tool.ts#L130-L140 | source, plugin 1.18.31 types. The docs list the event without describing it. | A plugin can rewrite tool output, so a squeeze port is possible. Prefer `tool_output.max_bytes` first, because it already spills to disk. |
| opencode | Session idle / stop | No dedicated hook key. Use the generic `event` hook and check `event.type === "session.idle"` (also `session.status`, `session.compacted`, `session.error`). It is notification-only and cannot block or continue the turn the way Claude's Stop can. | not applicable | OC/plugin/src/index.ts#L224; OC/opencode/src/session/status.ts#L39-L47; docs plugins "Events", "Send notifications" | docs, source, SDK 1.18.31 types | verify.py's Stop gate cannot be ported directly. A workaround would be calling `client.session.prompt` from the idle handler. That is untested and would need care to avoid loops. |
| opencode | Other hook keys in 1.18.31 | `chat.message`, `chat.params`, `chat.headers`, `permission.ask`, `command.execute.before`, `shell.env`, `experimental.chat.messages.transform`, `experimental.chat.system.transform`, `experimental.session.compacting`, `experimental.compaction.autocontinue`, `experimental.text.complete`, `tool.definition` | not applicable | `~/.opencode/node_modules/@opencode-ai/plugin/dist/index.d.ts` L173-L335 | installed types | `chat.message` is the UserPromptSubmit analogue for lessons.py. `tool.definition` can shorten tool descriptions. |

## 5. Reasoning effort

| Tool | Key | Type / accepted values | Default | Source | Verified | Recommendation |
|---|---|---|---|---|---|---|
| Codex | `model_reasoning_effort` | Non-empty string. Valid levels are whatever the model advertises. In the 0.142.5 catalog that is `low`, `medium`, `high`, `xhigh` for gpt-5.5, gpt-5.4, gpt-5.4-mini, gpt-5.3-codex and gpt-5.2. Main's catalog adds `max` and `ultra` for newer models. | The model's `default_reasoning_level`: `medium` for every model in 0.142.5. | CX/core/config.schema.json#L7630 (`ReasoningEffort`: string, minLength 1); docs config-reference; `codex debug models` | docs, source, ran it (`""` gives "reasoning_effort must not be empty") | Set it only from bench results. Write it to the top level of config.toml with setdefault semantics, the same way claude.py does. |
| Codex | `plan_mode_reasoning_effort` | string, same domain | built-in plan preset | config.schema.json#L1308 | docs, ran it (integer rejected) | Optional. |
| Codex | `model_reasoning_summary` | `auto`, `concise`, `detailed`, `none` | model default | protocol/src/config_types.rs#L57-L70 | ran it (bogus rejected with that list) | `none` or `concise` trims output tokens. Unmeasured. |
| Codex | `model_verbosity` | `low`, `medium`, `high` | model default | config.schema.json, `Verbosity` | docs, ran it | Candidate for a bench arm. |
| opencode | `agent.<name>.variant` | String naming a model variant. For OpenAI models the variants are the model's effort list. For Anthropic adaptive models they are `low`, `medium`, `high`, `xhigh`, `max` (`low`, `medium`, `high`, `max` for 4.6). Older Anthropic models get `high` and `max` thinking budgets. | none (provider default) | OC/core/src/v1/config/agent.ts#L15-L17; OC/opencode/src/provider/transform.ts#L229-L290, #L672-L684 | source, ran it (echoed back) | Use `variant` per agent (`build`, `plan`). Variants are defined per model in `provider.<id>.models.<m>.variants`. |
| opencode | `agent.<name>.options.reasoningEffort` (or a top-level unknown agent key, which is folded into `options`) | free-form provider option, passed through to the AI SDK | none | agent.ts#L30, #L43-L65 | ran it (`reasoningEffort` at agent level came back inside `options`) | Works for OpenAI-style providers. For Anthropic, use `variant`. |

## 6. Prompt cache controls

| Tool | Key | Type / accepted values | Default | Source | Verified | Recommendation |
|---|---|---|---|---|---|---|
| Codex | none | not applicable | `prompt_cache_key` is set automatically per conversation | CX/core/src/client.rs#L267, #L355-L391; no cache key in config.schema.json | source, docs (no prompt-cache entry in config-reference) | Nothing to configure. |
| opencode | `provider.<id>.options.setCacheKey` | boolean | Off, except `promptCacheKey = sessionID` is set automatically for @ai-sdk/openai, azure, xai, mistral and venice (deepinfra and cerebras use `prompt_cache_key`). `false` disables it. | OC/core/src/v1/config/provider.ts#L98-L100; OC/opencode/src/provider/transform.ts#L1323-L1336; docs config "Models" | docs, source, ran it (accepted) | Set `true` only for openai-compatible custom providers or proxies (such as the nerfguard router), where the automatic key is skipped. |
| opencode | Anthropic cache breakpoints | No config. `cacheControl: ephemeral` is placed on the first 2 system messages and the last 2 non-system messages. | automatic | OC/opencode/src/provider/transform.ts#L358-L400, #L469-L484 | source | Nothing to configure. Note that `compaction.prune` rewrites earlier tool parts and so invalidates these breakpoints. |

## Recommended changes, in order

1. opencode: have `providers/opencode.py` set `"tool_output": {"max_bytes": 8000}` in the global `opencode.json` with setdefault semantics. This matches squeeze's threshold and spill-to-file behaviour with no plugin code.
2. Codex: install the existing hooks into `~/.codex/hooks.json` (PreToolUse `Bash|apply_patch` to guard.py, PostToolUse `Bash` to a squeeze variant that emits `{"continue": false, "reason": ...}`, SessionStart and Stop to verify.py, UserPromptSubmit to lessons.py). Tell the user to trust them in `/hooks`, because untrusted hooks never run.
3. Codex: do not port `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000`. The default trigger (90% of 272k, about 245k) is already lower.
4. Codex: bench `tool_output_token_limit` (4000 as a first arm) before shipping, because it also cuts file reads.
5. Leave `compaction.prune` (opencode) and the effort keys unset until a bench arm measures them.
6. Tool search needs no work in Codex (always on) and cannot be done in opencode.

## Not verified

- No end-to-end model run in either CLI. Hook rewrite behaviour (Codex PostToolUse `continue:false` replacement, opencode `tool.execute.after` mutation) and the actual compaction trigger points are confirmed from source and docs only.
- The Codex source is main (3e23877), not the 0.142.5 tag (a shallow clone has no tags). Keys were checked against the 0.142.5 binary by type errors. The truncation algorithm, the 90% clamp and the hook trust logic were read from main and may differ slightly in 0.142.5.
- OpenCode 2.0 preview (`~/.opencode/bin/opencode2`) has a different config layer and was not checked.
