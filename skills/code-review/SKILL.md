---
name: code-review
description: Structured diff review with persistent reviewer preferences. Use when asked to review code, review a PR or diff, check changes before commit, or whenever the user states a review nit, style rule, or correction worth remembering.
---

# Code review with memory

Reviews enforce your accumulated standards, not generic taste. Standards live in two markdown files:

- `~/.config/agentmaxx/review-style.md`: personal, applies in every repo
- `.review-style.md` in the repo root: repo-specific conventions (committable for teams)

Both are optional; missing ones get created on first save.

## Workflow

1. **Gather**: a single bash call:

   ```sh
   git diff HEAD && cat ~/.config/agentmaxx/review-style.md .review-style.md 2>/dev/null
   ```

   For PRs substitute the appropriate base ref. If the patch exceeds ~600 lines, truncate; `--stat` carries the shape.

2. **Check, in this order.** Design first, because a well-styled change that shouldn't exist is the expensive miss (Google's review guide: "The most important thing to cover in a review is the overall design of the CL"):

   - Does it do what the user needs, and is it one self-contained change? Unrelated edits are a finding.
   - Is it more complex than the problem needs? Speculative options, layers, and abstractions for one caller are findings.
   - Failure paths: bad input, missing config, a dependency down. Agent-written tests skip these most of the time (try/catch lines went untested 81-86% of the time in arXiv 2607.18057), so a new error path with no test is a must-fix.
   - Could the tests fail? Tests that mock the thing under test, or assert the implementation instead of the outcome, prove nothing.
   - Production differences: new env vars without defaults or deploy config, files missing from the build, schema changes without a migration.
   - Then the stored style rules, then naming and readability.

   The bar is Google's: approve once the change "definitely improves the overall code health of the system", even if it isn't perfect. Don't block on taste. When reviewing your own work, run the review in a subagent with only the diff and the style files, so the reviewer didn't write the code.

3. **Review the diff only.** Pull minimal surrounding context with `better-cat` ranges when a change is ambiguous; never read whole files. Stored style rules apply silently; they surface only when violated.

4. **Report**, ordered `must-fix` → `nit` → `praise`:

   ```
   must-fix  src/api.ts:42: unhandled fetch: no try/catch, no res.ok check → wrap and guard
   nit       src/api.ts:17: else after return → drop the else
   ```

   One line each: `file:line: problem → fix`. No restating code, no summarizing what the diff does, no praise padding. Empty categories are skipped, not announced.

5. **Persist learnings; this is the point of the skill.** When the user corrects a finding ("that pattern is fine", "we always do X") or states a rule ("no default exports", "early return always"):
   - Write the *rule*, never the incident: "prefer early returns", not "in api.ts don't nest else". One generalized principle replaces five logged cases.
   - New entries go under `## Probation` with today's date. They promote to their permanent section only after firing in a later review (you enforced them again). Probation entries older than 30 days that never fired are deleted on next save; a rule nobody trips over isn't a rule.
   - Check for a near-duplicate before writing; refine the existing entry instead of appending a second.
   - Confirm with nothing beyond: `saved: "<entry>" → <file>`.
   - Hard cap: 40 lines per file. Adding beyond it requires merging two overlapping entries or evicting the least-recently-enforced one; state which in one line. The cap is an attention budget first, token budget second: a bloated style file makes every rule weigh less.

## Style file format

```markdown
## Must-fix (treat as bugs)
- no `any` in TypeScript
- every fetch wrapped in try/catch with a non-ok response check

## Style nits
- early returns; no else-after-return
- named exports only

## Never flag
- long lines in generated or vendored files

## Probation (entered 2026-08-24)
- prefer zod validation at API boundaries
```

**Probation is the growth brake.** New rules are guilty until proven useful: they sit dated under `## Probation`, get promoted to a permanent section the first time they fire again, and die silently after 30 days if never enforced. The permanent sections only ever contain rules that repeatedly mattered.

Sections map to severity: **Must-fix** findings outrank compiler-level pedantry, **Style nits** are the recurring opinions this system exists to remember, **Never flag** suppresses false positives so they stop costing attention every review.
