# Skills and plugins research: what could cut spend or raise quality

Researched 2026-10-03. Every candidate below links a URL fetched in this session (raw files via `curl`/`gh api`, two blog posts via WebFetch) and quotes it verbatim. Savings figures from authors are labelled as claims. Usage numbers are from this machine's transcripts (`~/.claude/projects/*/*.jsonl` plus subagent files; 1,964 files, about 30 days retained).

## The constraints that decide this

| Bill line | Share of bill | What moves it |
|---|---|---|
| Cache reads: tool results and prompts | 58% x 34.5% = 20.0% | smaller tool output, fewer reads |
| Cache reads: fixed prefix | 58% x 29.9% = 17.3% | shorter CLAUDE.md, tools, skill listing |
| Cache reads: prior thinking | 58% x 21.1% = 12.2% | effort level (already benchmarked) |
| Cache reads: visible assistant text | 58% x 14.5% = 8.4% | terser prose |
| Cache writes | 32% | fewer cache breaks, idle rewrites (7%), compaction |
| Output | 10% | terser prose, less thinking |
| Subagents (cross-cutting) | 13.5% | subagent model (already benchmarked: `v2_deleg_*` arms) |
| Skill listing (inside fixed prefix) | 2.3% | `skillOverrides` |

Invocation data, re-measured here:

- Model-invoked Skill calls in the whole retained history: loop 3, browse 3, claude-api 2, dataviz 2, office-hours 1, deep-research 1, workflow-authoring 1, artifact-design 1, artifact-capabilities 1.
- User-typed commands: /loop 50, /goal 12, /context 9, /login 6, /resume 2. No custom skill was ever typed.
- `evals/LEDGER.md` iteration 5: in 72 bench runs "The model invoked no skill in any run".

So a skill only earns its keep here if (a) the user types it, or (b) it works through a hook, plugin, or file change that does not depend on the model choosing to invoke it. Average listing cost per skill is about 2.3% / 109 = 0.02% of the bill; a 700-character description is about 0.04%. Small per skill, but it is paid by every skill that is never used.

## Built-in features first (these make several skills redundant)

All from https://code.claude.com/docs/en/costs.md, https://code.claude.com/docs/en/skills.md and https://code.claude.com/docs/en/plugins/code-intelligence.md (fetched as raw markdown).

1. `/skill-doctor`. Quote: "Run `/skill-doctor` to see what each of your skills costs and how often it gets used, so you can decide which ones to turn off. ... It flags skills in the listing that have never been invoked and says where to turn them off." Requires v2.1.252+; this machine has 2.1.289 per `evals/savings-research.md`. Makes any third-party "skill auditor" redundant.
2. `skillOverrides` states. Quote: `"name-only"` = "Name only" listed, still in `/` menu; `"user-invocable-only"` = "Hidden" from Claude, still in `/` menu; `"off"` = hidden in both. Also "The `/skills` menu writes it for you: highlight a skill and press `Space` to cycle states".
3. Listing truncation already happens. Quote: "The budget scales at 1% of the model's context window. When the listing overflows, Claude Code drops descriptions starting with the skills you invoke least". So many unused skills are already near name-only; the realistic gain from overrides is below the 2.3% ceiling in the ledger.
4. `/compact` with instructions. Quote: "`/compact Focus on code samples and API usage` tells Claude what to preserve during summarization." A `# Compact instructions` section in CLAUDE.md does the same persistently. No skill needed.
5. Idle rewrites (7% of bill). Quote: "your first message after a break longer than the cache lifetime misses the cache and reprocesses your full context. ... On Pro and Max plans, when you resume a large session after a long break, Claude Code offers to resume from a summary so later requests don't carry the full history". Accepting that offer, or `/clear` plus a handoff note, is the lever; no skill touches the cache TTL.
6. `/insights`, `/usage`. Quote: "Run `/insights` for a report on how you work rather than how many tokens you've used." With agentmaxx's own `evals/token_telemetry.py` and `doctor.py`, usage-report skills (session-report, receipts, usage-limit-reducer, cco) are duplicates.
7. `/simplify` and `/loop` are bundled, which makes Anthropic's `code-simplifier` agent and `ralph-loop` plugin duplicates for this user.
8. Skill frontmatter `context: fork` + `model`. Quote: "With `context: fork`, the value sets the forked subagent's model". Useful for authoring agentmaxx skills that do bulk reading on a cheaper model; not a thing to install.

## Candidates

### 1. caveman (JuliusBrussee/caveman), terse-prose skill

- URL: https://raw.githubusercontent.com/JuliusBrussee/caveman/main/skills/caveman/SKILL.md
- Quote: "Terse caveman voice: answer first, fluff gone, every technical fact kept. Use for /caveman, "caveman mode", "talk like caveman", "be brief", "less tokens". Stays on until "stop caveman" or "normal mode"."
- Independent measurement, https://blog.jetbrains.com/ai/2026/07/speak-to-ai-agents-like-cavemen-tosave-tokens/ (WebFetch): "Advertised saving: 65%. Measured saving: 8.5%." over "86 of 87 tasks", Claude Code 2.1.200, Sonnet 5 at low effort; quality "8 tasks better, 10 worse, 64 tied ... p = 0.82". The raw cost totals went the other way ("USD 40.60 vs. USD 36.39") because of one outlier task.
- The repo's own README (https://raw.githubusercontent.com/JuliusBrussee/caveman/main/README.md) is unusually honest: "Default caveman: 3% fewer output tokens at the median on top of the terse control, inside the noise ... ultracave: 35%".
- Targets: output (10%) and visible-text cache reads (8.4%).
- Mechanism: style rules that shorten prose. Code and tool calls are untouched.
- Honest guess: 0 to 1% of the bill. Your global CLAUDE.md already says "No openers, preambles, recaps ... or postambles", which is roughly the "terse control" in caveman's own eval, where default mode added 3% (noise). Upside only from `ultracave`, at unmeasured quality cost in agentic work.
- Listing risk: low if user-typed (`/caveman`), and the trigger is unambiguous. As always-on rules it adds input every turn; HONEST-NUMBERS.md: "Input cost the skill *adds* | Not measured here".
- Bench: add arm `v2_cave` = `v2` + `files: {"<caveman>/skills/caveman/SKILL.md": ".claude/skills/caveman/SKILL.md"}` plus a prompt prefix "/caveman" (or paste the rules into the arm CLAUDE.md, since bench runs never auto-invoke skills). Compare output tokens and cost vs `v2` on t1-t6 with `analyze.py` CIs; expect within noise at n=3.

### 2. caveman-compress (same repo), one-shot CLAUDE.md compressor

- URL: https://raw.githubusercontent.com/JuliusBrussee/caveman/main/skills/caveman-compress/SKILL.md
- Quote: "Compress a memory file such as CLAUDE.md or a todo list into caveman format to save input tokens, keeping a readable backup. Trigger: /caveman-compress."
- Claim (README): "46% smaller on average, headings, code, paths, and URLs verified intact" on five fixtures. Size only, no behavior check.
- Targets: fixed prefix (17.3%), main and subagents.
- Mechanism: rewrites the memory file once; the saving persists with no skill installed.
- Honest guess: about 0.3 to 0.6%. Your global + project CLAUDE.md are 1,890 + 2,779 chars (~1.2k tokens) of a ~17k-token prefix; halving them is ~3% of the prefix. Risk: terse rules may be followed less faithfully, and the agentmaxx `templates/CLAUDE.md` is already lean.
- Listing risk: none if installed, run once, removed.
- Bench: arm `v2_cmpr` with `files: {"arms/v2_CLAUDE.caveman.md": "CLAUDE.md"}` (compressed template) vs `v2`; check pass rate, tell count (`v2t`-style judge), and cost.

### 3. pyright-lsp (anthropics/claude-plugins-official), code intelligence plugin

- URL: https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/plugins/pyright-lsp/README.md
- Quote: "Python language server (Pyright) for Claude Code, providing static type checking and code intelligence."
- Mechanism quote, https://code.claude.com/docs/en/costs.md: "A single "go to definition" call replaces what might otherwise be a grep followed by reading multiple candidate files. Installed language servers also report type errors automatically after edits, so Claude catches mistakes without running a compiler."
- Targets: tool results (20%) and quality (catches type errors before tests).
- Honest guess: 0 to 3% on Python work, unmeasured anywhere I found. Gains scale with repo size; the bench fixture (shopkit) is small, so the bench will understate it. Diagnostics after each edit add tokens, so it can go negative.
- Listing risk: none. It is a plugin, not a skill, and the LSP tool is deferred. Requires `npm i -g pyright` (not on PATH here). You already run `rust-analyzer-lsp`.
- Bench: plugin loading needs user settings, but `run.py` uses `--setting-sources project,local`. Put `"enabledPlugins": {"pyright-lsp@claude-plugins-official": true}` in an arm's `.claude/settings.json` and confirm in one run's transcript that LSP diagnostics appear before trusting the numbers.

### 4. context-mode (mksglu/context-mode), sandboxed tool-output plugin

- URL: https://raw.githubusercontent.com/mksglu/context-mode/main/README.md and the skill at https://raw.githubusercontent.com/mksglu/context-mode/main/configs/copilot-cli/skills/context-mode/SKILL.md
- Quote: "Sandbox tools keep raw data out of the context window. 315 KB becomes 5.4 KB. 98% reduction." and "The plugin registers all hooks (PreToolUse, PostToolUse, UserPromptSubmit, PreCompact, SessionStart, Stop) and 11 MCP tools".
- Targets: tool results (20%).
- Mechanism: routes data-heavy reads and commands into a sandbox and returns only the computed answer.
- Honest guess: unknown, likely small here. It overlaps the agentmaxx Bash squeeze hook and `better-tools` (squeeze already caught most of the large Bash output; Read/Web squeezing measured 1.7% of the bill in `savings-research.md`). It also adds a SessionStart routing block and 11 MCP tool definitions to the prefix.
- Listing risk: medium (hooks + MCP + skill + prefix injection).
- Unsupported claim: "98% reduction" is a byte count on chosen examples. Caveman's comparison table says: "Own size numbers only. No quality check published".
- Bench: arm with the plugin enabled via project settings vs `v2`; watch `t4_question` correctness and the cache-write line (SessionStart injection).

### 5. claude-md-management `/revise-claude-md` (anthropics/claude-plugins-official), quality

- URL: https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/plugins/claude-md-management/commands/revise-claude-md.md
- Quote: "Review this session for learnings about working with Claude Code in this codebase. Update CLAUDE.md with context that would help future Claude sessions be more effective."
- Targets: quality, by recording repeated mistakes. It pushes the fixed prefix up, which is the opposite of candidates 1-2.
- Honest guess: no saving. It overlaps the agentmaxx lessons hook and GrayMatter. Mostly a duplicate here.
- Listing risk: none as a user-typed command (`allowed-tools: Read, Edit, Glob`). The bundled `claude-md-improver` skill is model-invoked and would add listing cost.
- Bench: not meaningful on fresh-fixture runs.

### Checked and rejected

| Candidate | URL fetched | Quote | Why not |
|---|---|---|---|
| superpowers | https://raw.githubusercontent.com/obra/superpowers/main/README.md | "because the skills trigger automatically, you don't need to do anything special" | Depends on auto-invocation, which barely happens here. Its SessionStart hook (`"matcher": "startup\|clear\|compact"`, hooks/hooks.json) re-injects a bootstrap into the prefix. Overlaps test-first, investigate, code-review. |
| RTK | https://raw.githubusercontent.com/rtk-ai/rtk/develop/README.md | "RTK cuts up to 90% of the bash output your agent reads. ... it is not the same as cutting your bill by 90%." | JetBrains measured "+7.6%" (already noted in `RESULTS.md`). Overlaps the squeeze hook. |
| session-report | https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/plugins/session-report/skills/session-report/SKILL.md | "Generate an explorable HTML report of Claude Code session usage (tokens, cache, subagents, skills, expensive prompts)" | Duplicates `token_telemetry.py`/doctor and `/usage`/`/insights`. Measures; saves nothing. |
| receipts | https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/plugins/receipts/skills/receipts/SKILL.md | "Generate a personal Claude Code usage & impact report" | Reporting only. |
| code-simplifier | https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/plugins/code-simplifier/agents/code-simplifier.md | "Simplifies and refines code for clarity, consistency, and maintainability while preserving all functionality." | Bundled `/simplify` does this. Also `model: opus` on a subagent. |
| ralph-loop | https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/plugins/ralph-loop/README.md | "This plugin implements Ralph using a **Stop hook** that intercepts Claude's exit attempts" | Bundled `/loop` (typed 50 times) covers it. |
| commit-commands `/commit` | https://raw.githubusercontent.com/anthropics/claude-plugins-official/main/plugins/commit-commands/commands/commit.md | "Stage and create the commit using a single message." | `fast-commit` already installed with the same pre-injected git context. |
| concise | https://raw.githubusercontent.com/o4f6bgpac3/concise/main/skills/concise/SKILL.md | "Cuts ~60-70% of output tokens while keeping natural, readable English." | Same lever as caveman with no measurement; 17 stars. |
| usage-limit-reducer | https://raw.githubusercontent.com/Dubibubii/usage-limit-reducer/main/SKILL.md | "Apply Dubi's 11 rules for cutting Claude token usage." | Advice plus a JSONL analyzer. agentmaxx's doctor already does this with measured data. |

## Claims that look unsupported

- KINGSTAR-OMEGA/claude-token-optimizer (source of the installed `antigravity` and `ultimate-protocol` skills), https://raw.githubusercontent.com/KINGSTAR-OMEGA/claude-token-optimizer/main/README.md: "Reduce Claude token usage by 60–80%", with a table of "~76%", "~81%", "~93%" "Est. token saving" and "(See `BENCHMARK.md` for the raw logs of our 5-task stress test)". `https://raw.githubusercontent.com/KINGSTAR-OMEGA/claude-token-optimizer/main/BENCHMARK.md` returns "404: Not Found", and the repo contents are only LICENSE, README.md, a screenshot and three skill folders. Five tasks, "Est.", no raw logs. Treat as unmeasured. agentmaxx ships both skills, so they should get a bench arm or lose the claim.
- MindStudio, https://www.mindstudio.ai/blog/5-claude-code-skills-cut-token-costs-70-percent-benchmarked: the headline says "70%", but the body's Graphify figure is "up to 70x cheaper". The only benchmark is "12 automated Claude Code sessions — six with a plugin called Superpowers installed, six without", run by "someone", with no model, tasks or raw data given. The article concedes "The 12-session benchmark is small."
- context-mode "98% reduction" and RTK "up to 90%" are byte reductions on tool output, not bill reductions. RTK says so itself; JetBrains measured RTK at +7.6% cost.
- valorisa/Claude-Skills `rescue-tokens`, https://raw.githubusercontent.com/valorisa/Claude-Skills/main/README.md: "**Verified results:** 90% token reduction in emergency scenarios." The supporting row is "| **Response Length** | 950 words | 525 words | 97 words | **90% reduction** |", which is the word count of one response, not tokens across a session. 15 stars.
- caveman's own "65%" was measured at 8.5% by JetBrains; the caveman README now says this itself.

## Ranked shortlist (at most 6)

1. **`/skill-doctor` + `skillOverrides`** (built-in). Ceiling 2.3% (listing), realistic ~1 to 1.5% because descriptions are already partly truncated. Zero risk to anything you use. Do this before installing anything.
2. **Bench `antigravity`/`ultimate-protocol` against `v2`**, or drop them. They are model-invoked ("ALWAYS" trigger), their upstream savings table has no data behind it, and the bench showed no auto-invocation.
3. **pyright-lsp plugin.** No listing cost; documented mechanism on the biggest bill line (tool results, 20%); also a quality gain. Unmeasured, so bench it, ideally on a larger repo than shopkit.
4. **caveman as a user-typed `/caveman`**, only if it replaces antigravity/ultimate-protocol as the terse-output option. It is the only candidate with an independent 86-task A/B (−8.5% output, quality flat). Expected ≤1% here because your CLAUDE.md is already terse.
5. **caveman-compress, run once then uninstall.** ~0.3 to 0.6% from a smaller prefix, and the prefix is also paid by every subagent. Verify rule adherence with a bench arm.
6. **Built-in resume-from-summary / `/clear` after idle >1h.** Targets the 7% idle rewrite line. This is a habit or a hook nudge, not a skill.

Not shortlisted: context-mode (overlaps squeeze; bench only if squeeze coverage proves thin), superpowers, RTK.

## Installed skills that likely cost more than they save

None of these appears in any retained transcript as a model invocation or a typed command. Characters are description + when_to_use as listed (capped at 1,536), measured from each SKILL.md frontmatter. Suggested state: `"user-invocable-only"` keeps `/name` working at zero listing cost; `"off"` for things you would never type.

| Skill | Desc chars | Suggest |
|---|---|---|
| berkeleytime | 909 | user-invocable-only (domain-specific, type it when needed) |
| plan-tune | 792 | off |
| office-hours | 781 | user-invocable-only (1 model invocation total) |
| design-html | 741 | user-invocable-only |
| plan-devex-review, devex-review | 711, 686 | off |
| framer, framer-code-components | 711, 345 | user-invocable-only (framer requires a setup step anyway) |
| ios-qa, ios-design-review, ios-fix, ios-clean, ios-sync | 710, 707, 629, 611, 561 | off unless you do iOS work (3.2k chars together) |
| qa, qa-only | 686, 485 | user-invocable-only |
| autoplan, plan-ceo-review, plan-eng-review, plan-design-review | 683, 589, 563, 442 | user-invocable-only |
| cso | 632 | user-invocable-only |
| claude-mem: ccs-align, mode-creator, oh-my-issues, weekly-digests, design-is, agent-cost-report, timeline-report, wowerpoint, version-bump, cloud-sync | 619, 475, 470, 404, 374, 354, 238, 219, 335, 240 | off (plugin-level, never used) |
| pair-agent, make-pdf, benchmark-models, document-release, document-generate, design-review, design-consultation, design-shotgun | 609, 597, 587, 572, 446, 572, 538, 415 | user-invocable-only |
| open-gstack-browser + connect-chrome | 480 + 480 | identical descriptions: keep one, turn the other off |
| gstack + _gstack-command | 367 + 367 | identical descriptions: keep one, turn the other off |
| setup-deploy, setup-gbrain, sync-gbrain, setup-browser-cookies, gstack-upgrade, landing-report, canary, land-and-deploy, skillify, retro, scrape, health, benchmark | 311-433 each | user-invocable-only |
| antigravity, ultimate-protocol | 338, 223 | user-invocable-only until benchmarked (see shortlist 2) |
| explore, context-handoff | 0 (no description in frontmatter) | add a description or switch to user-invocable-only. The listing falls back to "the first non-empty line" ("Repository Exploration", "Context Handoff"), which gives the model nothing to match on |

Keep listed: browse (3 model invocations), and the agentmaxx skills you want auto-applied, but only once a bench arm shows they fire.

Caveat: the transcript window is about 30 days (cleanup), so "never invoked" means "not in the last ~30 days". Running `/skill-doctor` gives the authoritative version of this table.
