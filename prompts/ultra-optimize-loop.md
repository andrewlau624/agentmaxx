# agentmaxx: optimization loop

You own the optimization of agentmaxx (this repo), a harness for Claude Code, Codex, and opencode. It installs settings, a short output contract, hooks, skills, and CLI tools. Your job is to find every real way to cut token spend and raise output quality, prove each one with a benchmark, ship the ones that win, and remove what doesn't earn its place. Run as a loop. Don't stop after one pass, don't ask me whether to continue, and don't end a turn with a summary and a question. Stop only when I say I'm satisfied or a stop rule below fires.

## Read first (every fresh context)

1. `evals/RESULTS.md`: what has been measured, the method, and the caveats.
2. `evals/LEDGER.md`: your own running log (create it on iteration 1). It holds hypotheses tried, results, decisions, and the open queue.
3. `README.md`, `templates/CLAUDE.md`, `hooks/`, `providers/claude.py`, `evals/bench/`.

Known state, so you don't rediscover it:

- **The bill is resident context × turns.** On the author's machine, cache reads are 65% of weighted cost, cache writes 24%, and output 11%. The median request is ~240k tokens; the fixed prefix at session start was ~86k before tool search.
- **Shipped and measured:**
  - Tool search forced on: −16% per task. Claude Code silently disables it behind a proxy `ANTHROPIC_BASE_URL`.
  - Auto-compact window 300k: −25% in replay.
  - Lean contract.
  - Hooks:
    - Bash squeeze: −28% resident Bash output.
    - Guard: 0.47% false positives.
    - Baseline-aware verify gate.
    - Lessons: 5/5 vs 0/5 cross-session.
  - Statusline and `agentmaxx doctor`.
  - Overall: v2 is −18% on Sonnet 5.5 and −11% on Haiku 4.5, with no pass-rate loss.
- **Known gaps:**
  - The bench is easy; Sonnet passes everything, so quality deltas are invisible.
  - The verify gate never fired, so its quality value is unproven.
  - The compact-window number is a simulation.
  - GrayMatter, claude-mem, Haiku subagents, and cache TTL are untested.
  - Codex and opencode only get the contract.
  - The 20 better-* tools were never called by the model on the bench.

## The loop

Each iteration:

1. **Pick.** Take the highest expected-value item from the queue: (expected % of bill or quality gain) × confidence ÷ cost to test. Log why you picked it.
2. **Research.** Read primary sources: official docs (code.claude.com, platform.claude.com, Codex and opencode docs), papers, source code of the tools you're evaluating, and issue trackers. Use parallel subagents for breadth and ask them for conclusions with URLs, not transcripts. Verify every config key, env var, and hook field against current docs or by running it; a claim nobody checked doesn't go in the ledger as fact.
3. **Hypothesize.** Write one falsifiable line: "X reduces weighted cost per task by ≥N% at equal pass rate" or "X raises pass rate on hard tasks by ≥N points".
4. **Build** the smallest version that tests it. Match the repo's style: stdlib Python, no new dependencies without a written reason, tests next to the code.
5. **Measure.**
   - **Offline replay** of real transcripts (`evals/doctor.py` patterns) when the effect is mechanical.
   - **Live bench** (`evals/bench/run.py`) when behavior changes. Live runs need ≥5 reps per cell, paired by task, medians per task, then the mean across tasks, plus a bootstrap 90% CI on the cost delta.
   - Run pass rate on the hard tasks with the cheapest model that fails sometimes.
6. **Decide.**
   - **Ship** if the CI excludes zero in your favor and quality is not worse.
   - **Revert** if quality drops, even when it's cheaper.
   - **Park** with the numbers if the result is inconclusive.
   - Record the decision in `LEDGER.md` and, if shipped, in `RESULTS.md`, including what didn't work.
7. **Regress.** Run `make test` and the full bench on the shipped config every 3 iterations. If total savings regress by more than 3 points, bisect before doing anything new.
8. **Report** to me in ≤8 lines: what you tried, the number, the decision, the next pick. Then continue immediately.

If you're running under `/loop` or have ScheduleWakeup, use it to keep going across long benchmark waits. Otherwise, keep working in the same session and let compaction happen; `LEDGER.md` is your memory.

## Stop rules

- I say stop or say I'm satisfied.
- Three consecutive iterations where nothing ships and the queue's best expected value is under 2% of the bill. When that happens, say so plainly and list what would need to change (a bigger bench, a new model, a new Claude Code feature) to reopen it.
- Spend: before each live bench batch, estimate cost and log it. Pause and tell me if cumulative bench spend passes $40.

## Research queue (seed; add to it, reorder by evidence)

### Context residency (the biggest line)

- **Tool-result decay.** Can a PostToolUse hook (`updatedToolOutput`, object-shaped like `tool_response`) or anything else shrink results that are already old? Claude Code has internal tool-result clearing; find out whether it's tunable. Compare with the API's `clear_tool_uses_20250919` and `compact_20260112`.
- **Compaction quality.** PreCompact hooks and custom compaction instructions. A SessionStart `compact` hook that re-injects task state, failing tests, and decisions. Measure task success after a forced compaction mid-task, not only cost.
- **Live context guard.** Turn the compact-window simulation into a live measurement: run long multi-step bench tasks with a 200k vs 300k vs 1M window.
- **Read dedupe.** A hook that answers a re-Read of an unchanged file with "unchanged since turn N, lines X–Y were shown". Measure how often re-reads happen in real transcripts first.
- **Huge Reads and web content.** Large Read results, WebFetch, and WebSearch were ~20% of tool-result residency. Look at summarizing or squeezing them, with a spill file.
- **Subagents.**
  - Delegation policy.
  - `CLAUDE_CODE_SUBAGENT_MODEL=haiku` for exploration.
  - Subagent prefix size: each one paid ~87k at start.
  - Return-size caps.
  - Measure end to end, including the cost of a wrong answer from a cheap subagent.
- **Cache behavior.**
  - TTL 5m vs 1h for human-paced sessions.
  - Mid-session model switches.
  - MCP reconnects.
  - Anything else that busts the prefix. Detect these from transcripts (`cache_creation` spikes) and add them to `doctor`.
- **Thinking and effort.** Measure effort levels and adaptive thinking against quality. Don't constrain thinking just because output tokens cost 5x; measure.

### Fixed prefix

- **Remaining overhead:** built-in tool schemas (~27k when not deferred), skill listings (~10k, mostly gstack), MCP server instructions, CLAUDE.md layers, and SessionStart injections from plugins (claude-mem's injected block).
- **For each item:** measure its tokens with `claude -p "/context"`, decide whether it pays its way, then prune, defer, or gate it by project.

### Search and retrieval

- **Approaches to compare:**
  - Native Grep/Glob/Read
  - LSP plugins (go-to-definition, references)
  - ast-grep
  - An aider-style repo map
  - ctags
  - A local embedding index
  - Serena
- **What to measure:** turns to first correct file and tokens read before the first edit, on a larger, unfamiliar repo. The current fixture is too small, so add 2–3 real open-source repos pinned at a commit, with hidden-test tasks.
- **better-* tools:**
  - Get usage counts from opencode and Codex logs plus the bench.
  - Keep a tool only if it's used and beats the native equivalent on tokens or turns.
  - Fix, merge, or delete the rest, and update `registry.yaml`, the skill, the opencode plugin, and the MCP server together.

### Memory and learning

- **Lessons.** Add a curator pass (ACE-style: dedupe, merge, retire on harmful votes), auto-voting from outcomes (did the session following a lesson pass verify?), and repo vs global scoping. Test for poisoning: a lesson recorded from a wrong correction must be retirable.
- **Existing memory tools.** GrayMatter and claude-mem: measure their per-session token cost (tool round trips plus injected context) against measured benefit on the learning bench. Keep, gate, or remove.
- **Verify gate.** Build hard tasks where agents often leave a regression (cross-module changes, subtle invariants), so the gate's quality effect becomes measurable.

### Harness

- **Agent SDK runner.** Evaluate an agentmaxx runner on the Claude Agent SDK / API that uses context editing, server-side compaction, and per-phase model routing (plan/explore on a cheap model, edit/verify on a strong one). Compare against plain Claude Code on the same bench, and only ship it if the win is large.
- **Codex parity.** Apply the measured settings to Codex (`tool_output_token_limit`, `model_auto_compact_token_limit`, sandbox) after verifying the keys.
- **opencode parity.** Apply them to opencode as well (`compaction.prune`, plugin hooks), after verifying the keys.

### Security

- Guard coverage gaps:
  - interpreter one-liners reading secrets
  - redirections (`< .env`)
  - exfiltration via `curl -d @file`
  - git hooks
  - the `.mcp.json` / `.claude/` supply chain in freshly cloned repos
- Prompt injection: scanning tool output from WebFetch and MCP.
- A recommended sandbox config.
- Measure everything against real transcripts for false positives. Keep the false-positive rate under 0.5% and never block the author's normal workflow (solo pushes to main are fine).

## No AI tells, anywhere

Any output an agent produces through agentmaxx must not read as AI-made. That covers prose, UI, code, architecture docs, commit messages, and security reports. It is a hard requirement, not taste: every recognizable signal counts. Skills exist (`human-voice`, `design-system-ui`, `reviewer-style`, `code-review`). Audit them, merge the overlap, and make each one enforceable.

### 1. Catalog

Build `skills/no-ai-tells/` (or extend the existing skills) with a catalog of signals per medium, sourced from:
- Wikipedia's "Signs of AI writing"
- published detector features
- design critiques of AI-generated UI
- your own diffing of AI output against human output

The catalog must cover at least the following.

**Prose:**
- em dashes as a crutch
- "delve", "tapestry", "testament", "crucial", "robust", "seamless", "leverage", "elevate"
- "It's not X, it's Y"
- reflexive triplets
- "Great question", "Certainly!"
- "In summary", "Overall"
- hedge stacks
- bolded-label bullet lists everywhere
- headers on short answers
- emoji section markers
- uniform sentence rhythm
- "Let me…" narration
- closing offers
- fake specificity
- sycophancy
- title case in headings

**UI:**
- purple/blue/indigo gradients and gradient text
- glassmorphism, neon on dark
- default Inter or system font everywhere, with no type scale
- centered hero with a badge pill above an H1, two buttons, and a fake logo strip
- the three-card feature grid with icons in rounded squares
- sparkle/✨ and robot iconography
- emoji as icons
- `rounded-2xl shadow-lg` on everything
- uniform spacing with no rhythm
- lorem-like copy ("Unlock the power of…", "Seamlessly…")
- stat blocks with made-up numbers
- testimonial carousels
- dark mode with low contrast
- identical hover lift on every card
- generic gradient blobs in the background

**Code:**
- comments restating code
- docstrings on trivial functions
- try/except swallowing everything
- defensive checks for impossible states
- needless abstractions, factories, and "utils" dumping grounds
- over-parameterized config
- placeholder TODOs
- verbose logging
- names like `handleData` / `processItem`
- unrequested type gymnastics
- a mix of styles within one file
- tests that assert mocks
- README sections nobody asked for

**Architecture and design docs:**
- microservices or queues for a CRUD app
- layer diagrams with no decision in them
- "scalable, maintainable, extensible" boilerplate
- option tables where every option is "it depends"
- missing trade-off and rejected-alternative sections

**Security reports:**
- severity inflation
- generic OWASP recitals with no repo-specific finding
- "consider implementing" without a concrete diff

**Commits and PRs:**
- "This commit…"
- bullet recaps of the diff
- emoji prefixes, unless the repo uses them

### 2. Detector

Build `evals/tells.py`: a deterministic linter that scores text, HTML/CSS/JSX, and code diffs for catalog hits per 1k words / per component / per 100 changed lines. Pair it with an LLM-judge pass for what regex can't catch, with a fixed rubric and blind comparison against human-written references.

### 3. Benchmark

Add generation tasks to the bench:
- write a README section
- build a landing page
- design a settings screen
- write an architecture decision record
- write a security finding
- write a commit message

For each, compare stock vs skill-loaded on tell density and on a blind judge's "which one did a person write" rate. The target is tell density near the human-reference baseline and a judge pick rate of ≈50% (indistinguishable).

### 4. Enforcement

- Hooks that lint agent-written files and commit messages, and block once with the specific hits, the same pattern as verify.
- Keep skill bodies short with the rules up front, loaded on demand, never resident in the contract.
- Measure the token cost of enforcement and keep it under 3% of task cost.

### 5. Writing about this work

Everything you write about this work (`LEDGER.md`, `RESULTS.md`, README, your reports to me) follows the same catalog.

## Rules of evidence

- Every number has a method next to it. No "~X% savings" without the command that reproduces it.
- Negative results go in `RESULTS.md` too.
- Don't trust tool vendors' token-savings claims; re-measure. Published A/Bs (JetBrains on RTK and caveman, Anthropic on tool search and context editing) are priors, not results.
- Cost is the weighted index (input 1, cache write 1.25, 1h write 2, cache read 0.1, output 5) or `total_cost_usd`, never raw token totals.
- Bench runs isolate with `--setting-sources project,local`, so they don't pollute the user's memory plugins or pick up their hooks.
- Don't change `~/.claude` on the author's machine without asking. Ship through `make install`, test installs with a throwaway `HOME`.
- Commit to a feature branch after each shipped iteration, with a plain message and no AI tells. Never push or merge without asking.
