# Token savings research: what agentmaxx does not do yet

Researched 2026-10-03 against the local Claude Code binary, which is now 2.1.289 (`claude --version`; the ledger's checks were on 2.1.288). Every row below is backed by one of three things: a page fetched this session with a verbatim quote, a string found in the local binary (`strings -n 6 $(readlink -f $(which claude))`, dumped once and searched), or a command I ran. Anything else is marked "not verified" and kept out of the shortlist. Vendor savings figures are recorded as claims, not as effects.

Skipped because agentmaxx already did or measured them: `ENABLE_TOOL_SEARCH`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW=300000`, `CLAUDE_CODE_PROMPT_CACHE_TTL`, `CLAUDE_CODE_EFFORT_LEVEL` on Sonnet, `skillOverrides` and `skillListingBudgetFraction`, the Bash squeeze hook, the lean CLAUDE.md, the guard/verify/lessons hooks, opencode `tool_output.max_bytes`, read dedupe (dropped at 0.0%), and Read/Web squeezing (1.7% of the bill in iteration 1).

The "share of bill" column uses the ledger's split: cache reads 58%, cache writes 32%, output 10%. It is the share of the whole bill the method could plausibly move, not a promised saving.

Doc URLs used below, all fetched this session (the `.md` variants were downloaded with curl and searched locally):

- costs: https://code.claude.com/docs/en/costs
- prompt caching (Claude Code): https://code.claude.com/docs/en/prompt-caching
- env vars: https://code.claude.com/docs/en/env-vars
- settings reference: https://code.claude.com/docs/en/settings-reference
- hooks: https://code.claude.com/docs/en/hooks
- subagents: https://code.claude.com/docs/en/sub-agents
- output styles: https://code.claude.com/docs/en/output-styles
- statusline: https://code.claude.com/docs/en/statusline
- pricing: https://platform.claude.com/docs/en/about-claude/pricing
- context editing: https://platform.claude.com/docs/en/build-with-claude/context-editing
- compaction: https://platform.claude.com/docs/en/build-with-claude/compaction
- prompt caching (API): https://platform.claude.com/docs/en/build-with-claude/prompt-caching
- token counting: https://platform.claude.com/docs/en/build-with-claude/token-counting

## Current prices

From the pricing page, model pricing table (base input, 5m cache write, 1h cache write, cache hit, output):

- "Claude Opus 5.5 | $4 / MTok | $5 / MTok | $8 / MTok | $0.20 / MTok<sup>2</sup> | $20 / MTok"
- "Claude Sonnet 5.5 | $2 / MTok | $2.50 / MTok | $4 / MTok | $0.20 / MTok | $10 / MTok"
- "Claude Haiku 4.5 | $1 / MTok | $1.25 / MTok | $2 / MTok | $0.10 / MTok | $5 / MTok"
- Footnote 2: "Cache hits and refreshes on Claude Opus 5.5 are priced at 0.05x the base input price."

The consequence matters for routing. Opus 5.5 and Sonnet 5.5 cost the same per cache-read token ($0.20). Moving work from Opus 5.5 to Sonnet 5.5 halves writes and output only, and leaves the 58% read line unchanged. Haiku 4.5 halves every line against Sonnet 5.5. The same page says long context is not surcharged: "A 900k-token request is billed at the same per-token rate as a 9k-token request."

## 1. Claude Code settings and env vars

| Method | Exact key and accepted values | Verified how | Claimed or measured effect | How agentmaxx could test | Share of bill |
|---|---|---|---|---|---|
| Turn off prompt suggestions | `promptSuggestionEnabled: false` or `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false` | costs page: "When prompt suggestions are on, Claude Code also sends a short request to the model your session is using after Claude responds... That request reuses the conversation's prompt cache, so it is mostly cache reads plus a few output tokens." env-vars: "Set to `false` to turn off prompt suggestions". Binary: both names present. | Ran a replay (60-line script over 1,452 main transcripts, 14 days, list prices): one extra full-context cache read per typed prompt is $51.82 of $1,283, 4.0%. Upper bound: the count includes `-p` bench prompts, where I did not verify that suggestions fire. The user's `~/.claude/settings.json` does not set the key, so it is on. | Replay first (count interactive prompts only), then a two-day A/B on real use with `/usage` | Up to 4% of reads, about 2 to 4% of the bill |
| Built-in Concise output style | `outputStyle: "Concise"` (case-sensitive) or `/output-style concise`, needs v2.1.237+ | output-styles: "In the Concise style, the first sentence of a response states what happened or what the answer is. Claude leaves out the lead-in, the step-by-step narration, and the closing recap". Binary: `Concise:{name:"Concise",source:"built-in",...keepCodingInstructions:!0` | No vendor number for Concise. The closest measurement is JetBrains' caveman A/B (section 4): 8.5% fewer output tokens, about 10% cost. Switching mid-session keeps the cache (prompt-caching page, "Changing output style"). | Bench: arm with `outputStyle: "Concise"` on the 10 real tasks, compare output tokens and pass rate; tells density too | Output is 10%; visible text is a minority of output (58% of billed output is hidden thinking per iteration 2), so about 1 to 3% |
| Native Bash output cap | `bashOutputMaxChars`, integer clamped to 4000..128000, default 30,000 (v2.1.261+). Env `BASH_MAX_OUTPUT_LENGTH` is ignored when the setting is set. | settings-reference: "When output passes the limit, Claude Code saves it to a file and Claude receives a short preview plus the file's path." Binary: present. | None claimed. Overlaps the squeeze hook. Lower maintenance, but it is a blind head/tail cut rather than signal-preserving. | Bench: squeeze hook vs `bashOutputMaxChars: 8000` without the hook, same tasks | Part of Bash's 8.1% residency; the hook already covers it, so the delta is small |
| Cap MCP output | `MAX_MCP_OUTPUT_TOKENS`, default 25000 | env-vars: "Maximum number of tokens allowed in MCP tool responses... (default: 25000)". Binary: present. | None measured. MCP share of residency not yet split out. | Replay: add an MCP bucket to residency.py before deciding | Unknown; probably under 1% |
| Drop git instructions and status snapshot | `CLAUDE_CODE_DISABLE_GIT_INSTRUCTIONS=1` or `includeGitInstructions: false` | env-vars: "remove built-in commit and PR workflow instructions and the git status snapshot". Binary: present. | Ran it: `claude -p /context` went from 17.5k to 17.3k (System tools 3.6k to 3.4k). About 0.2k of prefix. | Already measured: not worth shipping | Under 0.5% |
| Compact earlier as a percent | `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` (1-100, lowers only) | env-vars quote: "Use lower values like `50` to compact earlier; the variable can't raise the threshold". Binary: present. | Redundant with the window setting already tuned in iterations 3 and 9. | none | 0 (covered) |
| Background Haiku model | `ANTHROPIC_DEFAULT_HAIKU_MODEL` ("also used for background functionality"); `ANTHROPIC_SMALL_FAST_MODEL` is "[DEPRECATED]" | env-vars quotes. Binary: both present. | Background calls are small: costs page says "typically under \$0.04 per session". | none | Under 0.5% |
| Session title request | `CLAUDE_CODE_DISABLE_TERMINAL_TITLE=1` "also skips the background small/fast-model request that generates a session title" | env-vars quote. Binary: present. | Negligible. | none | ~0 |
| Goal check-ins while idle | `CLAUDE_CODE_GOAL_CHECKIN_MINUTES=0` | costs page: check-ins start "a new turn that sends your full context". Binary: present. | Only matters when `/goal` is used. | Replay: count check-in turns | Small unless goals are used |

## 2. API context management, and whether Claude Code exposes it

| Method | Exact key and accepted values | Verified how | Claimed or measured effect | How agentmaxx could test | Share of bill |
|---|---|---|---|---|---|
| Tool-result clearing (observation masking) | API: `context_management.edits: [{type: "clear_tool_uses_20250919", trigger, keep, clear_at_least, exclude_tools, clear_tool_inputs}]`, beta header `context-management-2025-06-27`. Defaults: trigger 100,000 input tokens, keep 3 tool uses. | context-editing page: "When activated, the API automatically clears the oldest tool results in chronological order." and on caching: "Invalidates cached prompt prefixes when content is cleared... Use the `clear_at_least` parameter". Binary: Claude Code builds this edit itself only for idle returns, `{minIdleSeconds:3900,keepToolUses:5,clearAtLeastTokens:...}`, gated by server flag `tengu_zany_pike` (off unless the server turns it on). No user setting. | JetBrains (section 4) measured that masking cut cost by more than 50% vs an unmanaged SWE-agent, on a different scaffold and model. Nothing measured for Claude Code. | Replay first: simulate masking (trigger T, keep N, clear_at_least C) in residency.py, charging a write of everything after the first cleared block whenever clearing advances. Then bench with a proxy that appends the edit. This machine already routes through `ANTHROPIC_BASE_URL`, so the proxy hook point exists. | Tool results, prompts and injections are 34.5% of reads (iteration 2), so the ceiling is about 20% of the bill before write penalties |
| Thinking clearing | `clear_thinking_20251015` with `keep` | context-editing page: default keep for "Opus 4.5+ and Sonnet 4.6+: all turns". Binary: Claude Code hardcodes `{type:"clear_thinking_20251015",keep:"all"}`. | Iteration 2 already found thinking is ~18% of the bill. A proxy could change `keep`, but "When thinking blocks are cleared, the cache is invalidated at the point where clearing occurs." | Same proxy as above, after masking | Up to 12% (thinking residency), with a cache-write cost each time |
| Server compaction | Beta `compact-2026-09-04`; Claude Code binary contains `"compact_20260112"` | compaction page table; binary string | Claude Code already compacts. No user lever beyond window and instructions. | none | 0 |
| Token counting | `POST /v1/messages/count_tokens` | token-counting page: "Token counting is **free to use**" and "The token count is an **estimate**." | Useful for agentmaxx's prefix audits without spending; no saving by itself. | Use it in doctor for prefix sizing instead of `-p /context` runs | 0 directly |
| Minimum cacheable size | 512 tokens for Opus 5.5 and Sonnet 5.5, 4,096 for Haiku 4.5 | API prompt-caching page quote: "4,096 tokens for Claude Haiku 4.5" | Haiku subagents with tiny prefixes would not cache; irrelevant at 20k+ prefixes. | none | 0 |

## 3. Hooks that shrink context

| Method | Exact field | Verified how | Effect | How agentmaxx could test | Share of bill |
|---|---|---|---|---|---|
| Replace tool output | PostToolUse `hookSpecificOutput.updatedToolOutput` | hooks page: "Replaces the tool's output with the provided value before it is sent to Claude. The value must match the tool's output shape". Binary: present. squeeze.py already uses it for Bash. | Extending it to MCP tools only pays if MCP output is large (unmeasured). | Replay MCP bucket first | Under 1% |
| Rewrite tool input | PreToolUse `updatedInput` | costs page example rewrites test commands to `| grep -A 5 -E '(FAIL|ERROR|error:)' | head -100` | For Read limits this is the already-deprioritized Read line (0.8%). | none | Under 1% |
| SessionStart context | `additionalContext`; capped: "A hook's `additionalContext`... strings, and its plain stdout, are capped at 10,000 characters" | hooks page quote | Ran a transcript scan: the SessionStart hook on this machine (an nvm-wrapped plugin command, likely claude-mem) injects about 8.5k chars per session, and again on `compact` (12 hits in the last 60 sessions). About 2.4k tokens resident per session. | Replay: residency of `hook_success:SessionStart` attachments | Under 1% |
| Compaction instructions | No hook can supply them: PreCompact only blocks, and "For `auto`, `custom_instructions` is `null`." The supported route is a `# Compact instructions` section in CLAUDE.md, or `/compact <text>`. | costs page: "You can also customize compaction behavior in your CLAUDE.md file". Binary: the summarizer prompt says "There may be additional summarization instructions provided in the included context... ## Compact Instructions". | Iteration 9 found forced compaction dropped Haiku's pass rate (13/21 vs 17/20). Instructions that keep the task state could recover it and allow a lower window, which is the largest modeled lever. | Bench: rerun v2_c40 with a `# Compact instructions` block in the contract | Indirect: enables the window lever (doctor modeled up to 22% at 200k) |

## 4. Community tools and studies

| Tool or study | What it does | Verified how | Claimed vs measured | Relevance to agentmaxx | Share of bill |
|---|---|---|---|---|---|
| JetBrains, "The Complexity Trap" | Compares observation masking with LLM summarization on SWE-agent | blog.jetbrains.com/research/2025/12/efficient-context-management/: "Both approaches (2) and (3) consistently cut costs by over 50% compared to (1)"; "keeping a window of the latest 10 turns gave us the best balance"; hybrid cut costs "7% compared to pure observation masking" | Measured, peer-reviewed workshop paper, SWE-bench Verified, 500 instances. Not Claude Code. | Motivates the masking row in section 2 | see section 2 |
| rtk (Rust Token Killer) | PreToolUse hook that rewrites Bash to `rtk <cmd>` | rtk-ai.app: "On the commands RTK rewrites, output drops by 56% on average" (claim). quesma.com/blog/does-rtk-make-ai-coding-cheaper/: "With RTK, costs fell by 5% for Fable and rose by 5% for DeepSeek" and "We do not recommend RTK as a generic cost-saving tool." | Independent measurement says roughly zero; the same post reports "JetBrains's SkillsBench run found no savings." | Do not adopt. It overlaps squeeze.py, and the measured result agrees with iteration 1 that output shrinking is small. | ~0 |
| caveman | Skill that makes replies terse | github.com/juliusbrussee/caveman README quotes: JetBrains A/B "8.5% fewer output tokens, about 10% cost. No detectable quality change (sign test p = 0.82)"; vs an "Answer concisely." control, "Default caveman: 3% fewer output tokens at the median... inside the noise"; skill costs "about 1,000 estimated" input tokens per call | The 65% headline is a claim; the JetBrains and control numbers are measurements reported by the repo. | Test the built-in Concise style instead (zero install, no extra skill tokens) | 1 to 3% |
| context-mode | MCP server plus PreToolUse routing that runs tools in a sandbox and returns only stdout or search hits | Search results only (github.com/mksglu/context-mode); "98% reduction" is the author's claim | Not verified, no independent measurement found | Skip | not verified |
| Serena / LSP MCP | Symbol-level navigation | Search results only; no controlled benchmark found | Not verified. Claude Code's own docs suggest code intelligence plugins instead: "A single 'go to definition' call replaces what might otherwise be a grep followed by reading multiple candidate files." (costs page) | Skip until a bench shows Read share rising | not verified |
| claude-code-router | Proxy that routes requests to other models | github.com/musistudio/claude-code-router README makes no savings claims; the old `background`/`think`/`longContext` keys are no longer on the page | No claims | Native subagent routing (section 5) covers the safe part | 0 |
| ccusage | Reports usage from local data, Claude Code, Codex and opencode | README: "Tracks and displays cache creation and cache read tokens separately"; `ccusage codex daily`, `ccusage opencode daily` | Measurement only | Could cross-check doctor's totals for Codex/opencode | 0 |
| MCP pruning, `disabledMcpjsonServers` / `enabledMcpjsonServers`, `--disallowedTools` | Remove servers or tools | settings-reference: `disabledMcpjsonServers` "Reject specific servers defined in a project's `.mcp.json`". Binary: both present. | With tool search on, MCP tools are deferred; `/context` here shows MCP tools 0.8k and instructions 0.6k loaded. Denying a whole tool keeps the cache only when tool search is on (prompt-caching page). | Not worth it while tool search is on | Under 1% |

## 5. Model routing

All figures in this table come from a replay I ran over 14 days of local transcripts, repricing each request at list price for its model family (Opus priced at Opus 5.5 rates, so older Opus usage is understated). Main sessions came to $1,284 and subagents to $143, so subagents were 10.0% of the bill (the ledger's iteration 7 said 13.5% with its own pricing).

| Method | Exact key and values | Verified how | Measured or modeled effect | How to test | Share of bill |
|---|---|---|---|---|---|
| Cheaper Explore | A user or project agent file named `Explore` with `model: haiku` | sub-agents page: "A user or project subagent named `Explore` overrides the built-in and keeps its own `model` field, so define one with `model: haiku` to run exploration on a lower-cost model." Binary: built-in Explore is `model:"inherit"` with an Opus cap, `omitClaudeMd:!0`. | Modeled below together with other subagents | Bench tasks that spawn Explore (current tasks spawn none, per iteration 7) | part of the next row |
| All subagents on one model | `CLAUDE_CODE_SUBAGENT_MODEL=haiku` (or `sonnet`) plus `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1` (v2.1.257+) | sub-agents page: "To apply one model to every subagent, teammate, and workflow agent, also set `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` to `1`." Without FORCE, "Setting `CLAUDE_CODE_SUBAGENT_MODEL` by itself doesn't change the model the built-in Explore and Plan subagents run on." Binary: both present. | Replay: subagent Opus to Haiku saves $76.1 = 5.3% of the bill; Opus to Sonnet saves $28.5 = 2.0% | Bench: tasks that need exploration, pass rate and cost | 2 to 5% |
| Main model Opus to Sonnet | `model: "sonnet"` (the user's settings say `opus[1m]`) | Pricing quotes above; cache hits are $0.20 on both | Replay: $301.7 = 21.1% of the bill. It all comes from writes and output, because reads cost the same. | Bench exists (Sonnet already passes 8 of 10 real tasks); needs an Opus arm on the same tasks for the quality side | ~21%, quality trade |
| `opusplan` | `model: "opusplan"` | prompt-caching page: "each plan-mode toggle is a model switch and starts a fresh cache." | Every toggle rewrites the full context at the new model's write price. Not measured. | Replay: count plan-mode toggles and price the rewrites | Not verified as a saving |
| Per-skill `model` | skill frontmatter `model` | prompt-caching page: "that turn is also a model switch: the next request reads the entire conversation history with no cache hits." | A cost trap, not a saving, unless the skill uses `context: fork` | Audit installed skills for a `model:` field | Avoid |
| Fork vs fresh subagent | `CLAUDE_CODE_FORK_SUBAGENT=0` disables forks | env-vars quote: "or `0` to turn it off in every kind of session". Binary: present. Iteration 7: fork first request p50 256k vs general-purpose 65k. | Not measured. A fork reads the parent cache cheaply on its first request, then re-reads 256k every turn; a fresh agent writes 65k once. Rough break-even is about 4 turns. | Replay: price each fork as if it were fresh, from its turn count | Part of the 10% subagent share |

## 6. What busts the cache in Claude Code

From https://code.claude.com/docs/en/prompt-caching unless marked otherwise. The list: "Switching models", "Changing effort level", "Turning on fast mode", "Connecting or removing an MCP server", "Enabling or disabling a plugin", "Denying an entire tool", "Compacting the conversation", "Accumulating many images", "Upgrading Claude Code".

| Event | Busts? | Source |
|---|---|---|
| `/model` switch, opusplan toggle, automatic model fallback, a skill with a different `model` | Yes, full rewrite | "Each model has its own cache." |
| Effort change | No on Opus 5.5, Sonnet 5.5 and Fable 5.1 with an API key or subscription; yes elsewhere | "changing effort keeps the cache, and Claude Code applies the new level without asking" |
| Fast mode on | Yes, once per conversation | "adds a request header that is part of the cache key" |
| MCP server connects or reconnects | No when tool search defers tools; yes when tools load upfront (this machine's proxy disables tool search unless `ENABLE_TOOL_SEARCH` is set) | "Claude Code keeps the tool list from the conversation's first request for the whole conversation" |
| Plugin skills, commands, agents, hooks | No | "Claude Code never invalidates the cache for a plugin's skills, commands, agents, hooks, monitors, or themes." |
| Background plugin refresh in `-p` | Yes, off by default | env-vars: `CLAUDE_CODE_ENABLE_BACKGROUND_PLUGIN_REFRESH` "invalidates prompt caching for that turn" |
| CLAUDE.md edit mid-session | No, and the edit does not apply until `/clear`, `/compact` or restart | "Editing them mid-session does not invalidate the cache, but the edit also doesn't apply." |
| Output style change, permission mode change, `/recap`, `/rewind` | No | "Actions that keep the cache" list |
| Date rollover | No: appended as a message | Binary: `date_change:(e)=>...Re({content:\`The date has changed. Today's date is now ${e.newDate}...\`,isMeta:!0})` |
| Upgrade | Yes for new sessions | "the first conversation you start after an upgrade builds its cache from the top" |
| Different directory or git snapshot | Separate cache | "Sequential sessions share the prefix only when the git status snapshot taken at startup matches" |
| Idle past TTL | Full rewrite | Iteration 1 already measured 7.0% of the bill |

The `/usage` Prompt cache line, and the statusline `prompt_cache` object with `misses` and `expected_rebuilds` (statusline page), now name the likely cause of a miss (v2.1.260+). Doctor could read the same fields to report misses per session instead of inferring them.

## 7. Codex and opencode

The parity research (evals/parity-research.md) already found the keys. Two map onto ideas above and remain untested: opencode `compaction.prune` (boolean, default false), which "clears completed tool outputs older than the last 40k tokens of tool output" and is the built-in form of observation masking, and Codex `tool_output_token_limit` (default 10000 tokens). Neither CLI is on PATH here, so I did not re-run them. Prices for Codex models were not checked.

## Ranked shortlist of untested ideas

Ranked by expected share of the bill times confidence, divided by the cost to test.

1. Observation masking through the existing local proxy. Append a `clear_tool_uses_20250919` edit (keep about 5 to 10 tool uses, a large `clear_at_least` so cache rewrites are rare) to requests Claude Code already sends with `context_management`. The mechanism is verified in the API docs, and the binary shows Claude Code builds the same edit itself behind a server flag. The ceiling is about 20% of the bill; JetBrains measured over 50% on another scaffold. Test it by replay simulation first (free), then a bench arm.
2. Turn off prompt suggestions. One verified setting, no quality risk. The replay upper bound is 4.0% of the bill. Test by counting interactive prompts only, then confirm with `/usage` over two days.
3. Route subagents to Haiku: a project `Explore` agent with `model: haiku`, or `CLAUDE_CODE_SUBAGENT_MODEL=haiku` with `CLAUDE_CODE_SUBAGENT_MODEL_FORCE=1`. The replay reprice is 5.3% (Sonnet: 2.0%). This needs bench tasks that actually spawn subagents.
4. Main model Opus 5.5 to Sonnet 5.5 for routine work. The replay reprice is 21.1%, all from writes and output, because cache hits cost $0.20 on both. It is the largest single number here, but it is a quality decision, so the bench needs an Opus arm on the same real tasks.
5. A `# Compact instructions` block in the contract that tells the summarizer to keep the task state, failing tests and file paths. It is verified in the docs and in the binary's summarizer prompt. The bench is a rerun of v2_c40. If it recovers the iteration 9 pass-rate loss, the lower compact window (doctor modeled up to 22%) comes back into play.
6. The Concise output style. Built in and verified, and switching keeps the cache. Expect 1 to 3% of the bill (output is 10%, and most of it is thinking). Bench it with output tokens, pass rate and tells.
7. Fork vs fresh subagents (`CLAUDE_CODE_FORK_SUBAGENT=0`). Forks start at 256k and re-read it every turn. This is a free replay that prices forks as fresh agents. Any saving sits inside the 10% subagent share.
8. opencode `compaction.prune`, the observation-masking analog for opencode. One key, measured nowhere yet. Bench it next to idea 1 so both tools get the same answer.

## Not verified, kept out of the shortlist

context-mode's "98% reduction", Serena or LSP savings figures, the rtk site's 56% average (contradicted by Quesma's measurement), caveman's 65% headline, and whether prompt suggestions fire in `-p` mode.
