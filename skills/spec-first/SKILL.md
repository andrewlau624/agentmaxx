---
name: spec-first
description: Interviews the user and writes a short spec before building a feature that touches several files or has unclear requirements, so the build matches what they actually need and how it will run in production. Use when asked to build, add, or implement something non-trivial, when the request leaves out users, inputs, failure behavior, or deployment, or when the user says "spec this", "plan this", or "interview me".
argument-hint: "[feature]"
---

# Spec first

Claude Code's own best practices say: "for larger features have Claude interview you and write a spec before you start implementing." A feature that works in the demo and fails in production usually failed at this step. Nobody asked what happens with bad input, at real data sizes, or with the real config.

Skip this for a one-file change with an obvious outcome. Use it when the work spans several files, adds a dependency or a service, changes data, or the request is one sentence long.

## 1. Read before asking

Look at the code first so you ask only what the code can't answer: where this would live, what similar features do, how the app is configured and deployed (Dockerfile, CI, env files), and what tests exist.

## 2. Interview

Ask at most 6 questions, in one message, each with your proposed default so the user can just say "yes":

- Who uses it, and what does success look like for them, as something you could observe?
- What inputs arrive, and what are the bad ones (empty, huge, malformed, duplicate, concurrent)? What should happen for each?
- What does it depend on (DB, API, queue, env vars, secrets), and what happens when one is down or missing?
- How does it ship (where it runs, how it's configured, what data exists already)?
- What's out of scope?
- How will we know it works in production (a log line, a metric, a manual check)?

Drop any question the code already answered.

## 3. Write the spec

Keep it to one screen, in the chat or in `docs/specs/<feature>.md` if the user wants it kept:

```
Goal: one sentence.
Behavior: numbered, observable outcomes, including error cases.
Interfaces: routes, CLI flags, function signatures, schema changes.
Config: new env vars or settings, with defaults, and where each is set in deploy.
Out of scope: ...
Verification: how each behavior will be checked (this becomes the /verify-pr claim list).
Risks: data migrations, breaking changes (see /safe-change), anything irreversible.
```

Get a yes before building. Then build against the spec, and when done run `/verify-pr` with the spec's Behavior list as the claims.

If the build shows the spec was wrong, update the spec and tell the user what changed. Don't let the code and the spec drift apart.
