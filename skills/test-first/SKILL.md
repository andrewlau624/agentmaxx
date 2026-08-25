---
name: test-first
description: Test-driven development loop with enforced verification. Use when implementing new behavior, fixing bugs with reproducible symptoms, or whenever the user asks for tests, TDD, or test coverage.
---

# Test first

Execution is the only ground truth an agent has. Writing the test first turns your change into a conversation with reality instead of a monologue.

## The loop

1. **Red.** Write one test that captures the desired behavior and run it. It must fail, and fail for the reason you expect. A test that passes immediately proves nothing about your change.
2. **Green.** Write the smallest implementation that passes. Nothing speculative — no branches, configs, or abstractions without a failing test demanding them.
3. **Check.** Run the full suite via bounded output so regressions surface:

   ```sh
   python3 {{TOOLS_ROOT}}/better-check/better_check.py --test npm test
   ```

4. **Refactor** with tests green. Then back to 1 for the next behavior.

## Bug fixes

The reproduction test comes first, always: write the test that demonstrates the bug (fails on current code), watch it fail, then fix. This prevents two classic failures — the "fix" that doesn't reproduce, and the regression returning next quarter because nobody pinned it to a test.

## What makes tests worth having

- Test observable behavior, not implementation details. Testing that a private method was called twice breaks on every honest refactor.
- Name tests as claims: `rejects_expired_token_with_401`, not `test_auth_2`.
- One assertion theme per test. If the name has "and", split it.
- No mock theater: mocking the thing under test to verify mocks proves nothing. Mock boundaries (network, clock, fs), not internals.
- When implementation and test disagree, determine which is wrong before editing either — the test may be the outdated artifact.

## With the rest of agentmaxx

Pair with assumption-check for the premises the first failing test depends on. Commit only on green, via fast-commit.
