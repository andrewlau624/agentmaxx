---
name: verify-pr
description: Proves a branch or PR works the way it will run in production, feature by feature, and fixes what fails until every claim has evidence. Use before saying a feature is done, before opening or merging a PR, when asked to "QA this", "test everything", "make sure it works", "will this work in prod", or after a change that passed tests but hasn't been run for real. Passing unit tests is not enough to skip it.
argument-hint: "[base-ref or PR number]"
---

# Verify a PR end to end

Passing tests is weak evidence. In one study, 29.6% of SWE-bench patches that passed the tests behaved differently from the real fix ("Are 'Solved Issues' in SWE-bench Really Solved Correctly?", arXiv 2503.15223). Agent-written tests leave error handling untested most of the time: lines inside try/catch blocks went uncovered 81% (Python) to 86% (Java) of the time (arXiv 2607.18057). So this skill doesn't ask "do the tests pass". It asks "did I watch each feature work, the way a user or caller will hit it, including when things go wrong".

## 1. Build the claim list

Read the diff against the base (`git diff <base>...HEAD`, or `gh pr diff <n>`), the PR description, and any linked issue. Write a numbered list of every behavior the change claims or implies:

- each user-visible feature or fixed bug, stated as an observable outcome ("POST /orders with an expired coupon returns 422 and a message", not "coupon validation")
- each error path the code adds or touches: bad input, missing config, network or DB failure, permission denied, empty and huge inputs
- what must not change: callers of modified functions, existing endpoints, CLI flags, file formats, migrations on existing data

Show the list to the user before testing if the change is large or the intent is unclear. A wrong list wastes the whole run.

## 2. Find how it really runs

Work out the production path before testing anything: the entry point (CLI command, HTTP route, worker, UI page, library API), how it's built (Dockerfile, build script, `pip install .`, `npm run build`), and what it needs (env vars, config files, a database, a queue, feature flags, secrets). Read the deploy config if there is one (Dockerfile, CI workflow, Procfile, k8s or fly/vercel config). The point is to test what ships, not what the dev server happens to tolerate.

Things that pass locally and break in prod, so check each that applies:

- a new env var or config key with no default and no entry in the example env, deploy config, or docs
- code that works from the source tree but not from the built artifact (missing package data, files not included in the build, imports that only resolve from the repo root)
- a dependency used but not declared, or declared only as a dev dependency
- a schema change with no migration, or a migration that fails on existing rows
- dev-only behavior: debug mode, permissive CORS, SQLite locally and Postgres in prod, a mock left wired in
- anything depending on the current directory, local paths, timezone, or locale

## 3. Exercise every claim

For each item, run it through the real entry point and record the evidence: the command, the request and response, the log line, the screenshot. Prefer, in order:

1. the built artifact or a production-like run (container, installed package, production build)
2. the app started normally, hit through its public interface (curl, the CLI, a browser via Playwright or the bundled `/verify` skill)
3. an integration test using real dependencies (a real database in a container, not a mock)
4. a unit test, only for logic with no I/O

Mocks don't count as evidence that an integration works. Where a test double stands in for a service you don't control, say so in the report.

Error paths get the same treatment: actually send the bad input, unset the env var, stop the database, and watch what happens. "It raises" isn't the bar. The bar is that the caller gets a useful error and nothing is left half-written.

When existing tests pass, check that they could have failed. Break the new code on purpose (invert a condition, return early) and rerun. If nothing goes red, the tests don't cover the change, so write one that does.

## 4. Fix and loop

When something fails, find the cause before fixing it, then fix it in the code rather than in the test. Rerun that item and everything that touches the same code. Repeat until every item passes or you hit something you can't verify here.

Stop and ask instead of looping when a failure needs a product decision, credentials you don't have, or a service you can't reach. Don't mark those as passing.

## 5. Report

One table, one row per claim:

```
| # | Claim | How it was run | Result | Evidence |
|---|-------|----------------|--------|----------|
| 1 | expired coupon returns 422 | curl against `docker run` of the built image | pass | response body below |
| 4 | missing STRIPE_KEY fails at startup | unset in .env, started app | fixed | was a 500 on first request; now exits with a message |
| 6 | migration on existing orders | not run | unverified | no prod-like data here |
```

Then list what you changed while fixing, and every item you couldn't verify, with the reason. Never round "unverified" up to "pass". The user needs to know exactly which parts were watched working.
