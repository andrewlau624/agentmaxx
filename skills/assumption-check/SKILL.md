---
name: assumption-check
description: Extract and verify implicit assumptions before implementing. Use before any non-trivial implementation, bug fix, integration, or refactor - especially when the task relies on undocumented behavior, says "should" or "probably", or touches code you haven't read yet.
---

# Assumption check

Most wrong implementations are confident answers to unverified premises. The bug isn't in the code you're about to write; it's in what you believe about the code you haven't read.

## Workflow

Before writing any implementation code:

1. **List the assumptions.** Everything the plan silently depends on: "this function returns null on miss", "the migration already ran on staging", "this endpoint is rate-limited", "tests run with TZ=UTC", "the config value is always set".

2. **Verify each against ground truth** — the repository, not your memory of it:
   ```sh
   better-context "functionName null return" --max-hits 3
   better-cat src/service.py:40-80
   ```
   One search per assumption. Cheap; each is one call.

3. **Mark every row**: `Verified` (with file:line), `False`, or `Unverifiable`.

4. **Act on the result:**
   - A `False` assumption usually rewrites the plan — stop and replan, don't patch around it.
   - `Unverifiable` assumptions get surfaced to the user explicitly, plus the defensive choice you'll make (e.g., "config may be unset; defaulting to 3 retries").
   - Only when every row is resolved do you implement.

## Rules

- Cap verification at ~2 minutes per assumption; a wrong premise costs hours, a slow check costs seconds.
- Assumptions about *runtime state* (migrations, env vars, deployed versions) are verified by asking or running a command, never by reading code alone.
- For trivial changes skip this entirely — verifying a typo fix's assumptions is its own failure mode.
