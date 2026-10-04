---
name: safe-change
description: Makes risky changes to existing code without breaking callers or data. Pins current behavior with characterization tests before a refactor, and splits schema, API, config, and dependency changes into expand, migrate, contract steps that can each ship alone. Use for refactors, renames across modules, database migrations, changing a function signature or API response, upgrading a major dependency, or any change where "what else uses this?" matters.
---

# Safe change

Most breakage from a refactor or migration isn't in the code that changed. It's in a caller nobody checked, a row nobody migrated, or a client still sending the old shape. This skill makes the old behavior explicit before touching it, then moves in steps that are each safe to deploy.

## Refactors: pin the behavior first

1. Find every caller: `rg -n "name\b"`, plus dynamic uses (string dispatch, reflection, templates, config keys, serialized names in JSON or the DB). List them.
2. Write characterization tests for the code you're about to change: tests that record what it does now, including odd behavior, not what it should do. Feed it real-looking inputs and edge cases, capture the outputs, and assert them. These are sometimes called golden master tests.
3. Run them and confirm they pass on the unchanged code. If one fails, your picture of the current behavior is wrong, so fix the test.
4. Refactor in small commits, running the characterization tests and the existing suite after each one. A refactor changes structure, not behavior. If a test has to change, you're no longer refactoring: stop and say what behavior is changing and why.
5. Don't mix a refactor with a behavior change in one commit.

## Interface, schema, and data changes: expand, migrate, contract

A backward-incompatible change ships in three phases (Parallel Change, martinfowler.com/bliki/ParallelChange.html):

1. Expand. Add the new form next to the old one. New column (nullable or with a default), new field, new endpoint version, new function. Both work. Writers write both forms where needed.
2. Migrate. Move every reader and writer to the new form. Backfill existing data in batches that can be resumed. Verify: count the rows still in the old form, compare old and new values on a sample.
3. Contract. Only after nothing uses the old form (check logs, metrics, `rg`, and all deployed clients), remove it in a separate change.

Rules that keep each step deployable:

- Old code must keep working against the new schema, because during a deploy both run at once.
- Never rename or drop a column, field, or env var in the same release that stops using it.
- A NOT NULL constraint or a new unique index goes in only after the backfill is verified. On a large table, check whether adding it locks writes.
- Every migration needs a tested way back: a down migration, or a written note on why it's irreversible and what the recovery plan is.
- Run the migration against a copy of production-shaped data (realistic row counts, nulls, duplicates, legacy values) before calling it done. An empty dev database proves nothing.

## Dependency upgrades

Read the changelog between the two versions for breaking changes and deprecations. Search the code for each affected API. Upgrade one major dependency per change. Run the full suite and the app's real entry point, not just the import.

## Done means

- Characterization tests and the full suite pass after every step.
- Every caller from step 1 was either unaffected or updated, and you can say which.
- For data changes, the counts show the migration finished, and the rollback was tested or its absence explained.
- The report says which phase this change is (expand, migrate, or contract) and what the next one is.
