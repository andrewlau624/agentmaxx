# Context Handoff

## Purpose

Preserve the minimum sufficient working state required for another coding agent to continue a task without repeating repository discovery, reconstructing prior decisions, or losing task-specific constraints.

This skill is **ag/ent-agnostic**. It defines the information that must survive a session boundary, not a specific command, model, CLI, or platform.

## When to Use

Create a handoff when:

* the current context is becoming too large;
* the session is ending before the task is complete;
* another agent will continue the task;
* work is being paused;
* a meaningful task boundary has been reached;
* important review, implementation, or architectural state should survive the current session.

Do not create a handoff after every edit or minor action.

## Core Principle

A handoff preserves **continuation-critical working state**, not conversation history.

```text
Repository instructions
→ how the repository works

Handoff
→ what matters about the current task

Repository
→ what is actually true now
```

The handoff should allow a new agent to continue without needing the original conversation.

The repository remains the source of truth for current implementation state.

## What Belongs in a Handoff

Preserve information when losing it could cause the next agent to:

* repeat completed work;
* reconsider an established decision;
* violate a requirement or constraint;
* miss reviewer feedback;
* reintroduce a rejected approach;
* misinterpret why the current implementation exists;
* repeat an investigation;
* miss an unresolved problem;
* perform unnecessary repository exploration.

The handoff should contain:

* objective;
* current state;
* completed work;
* remaining work;
* decisions;
* rejected approaches;
* review feedback;
* review resolution;
* constraints;
* relevant files;
* verification;
* blockers;
* open questions;
* next action.

## What Does Not Belong

Do not preserve:

* the full conversation;
* large source-code excerpts;
* complete command output;
* routine commands;
* temporary thoughts with no effect on the task;
* information already available in repository instructions;
* implementation details that can be recovered directly from the code;
* speculative ideas that were not adopted;
* redundant explanations.

The handoff should be substantially smaller than the conversation it represents.

## Handoff Format

Use the repository's handoff template:

```text
.agent/context/handoff.md
```

The structure is:

```markdown
# Handoff

## Objective

## Current State

## Completed

## Remaining

## Decisions

## Rejected Approaches

## Review Feedback

## Review Resolution

## Constraints

## Relevant Files

## Verification

## Blockers

## Open Questions

## Next Action
```

Sections may contain `None` when there is no relevant information.

Do not remove a section merely because it is currently empty. The structure makes the handoff predictable for every agent.

## Objective

State the desired outcome.

The objective should describe what the task must accomplish, not the sequence of actions used to accomplish it.

## Current State

Describe what is true about the task now.

Include important partial implementation state, known failures, and significant progress.

Do not narrate the investigation process.

Prefer:

```text
The parser is implemented and integrated with the API.
Validation is complete for malformed requests but not for
duplicate identifiers.
```

Over:

```text
We started by looking at the parser and then changed the API
and eventually got most of validation working.
```

## Completed

Record meaningful work that is finished.

Do not list every edit.

The purpose is to prevent another agent from repeating completed work.

## Remaining

Record work that still needs to be completed.

Separate actual remaining work from ideas that were merely considered.

## Decisions

Record decisions that affect implementation or future reasoning.

Include the reason or evidence when it prevents the next agent from incorrectly reconsidering the decision.

Prefer:

```text
Authentication remains at the HTTP boundary.

Reason:
Route-level authentication duplicated authorization logic and
was rejected during review.
```

Do not preserve decisions that have no effect on future work.

## Rejected Approaches

Record approaches that were explicitly considered and rejected when repeating them would waste meaningful effort or violate an established constraint.

Do not turn this section into a list of every idea discussed.

## Review Feedback

Preserve relevant feedback from:

* code review;
* pull-request review;
* maintainers;
* users;
* CI;
* tests;
* other agents.

Review feedback is part of the task state when it imposes a requirement, identifies a defect, questions an implementation decision, or otherwise affects future work.

Do not preserve non-actionable feedback such as generic approval.

Example:

```text
Reviewer requested validation before persistence because the
current ordering allows invalid records to reach the storage layer.
```

## Review Resolution

Record how relevant feedback was addressed.

Explicitly preserve unresolved feedback.

Example:

```text
Validation was moved before persistence and covered by a new test.

Unresolved:
Reviewer requested transaction-level coverage; this remains open.
```

This prevents a later agent from assuming that previously discussed review feedback was either never addressed or fully resolved.

## Constraints

Record requirements that must remain true.

Examples include:

* explicit user requirements;
* compatibility requirements;
* API contracts;
* architectural boundaries;
* security requirements;
* reviewer requirements;
* behavior that must not regress.

Do not duplicate general repository conventions already documented elsewhere.

## Relevant Files

Record only files, directories, symbols, tests, or components that materially narrow the next agent's search.

Include why a file matters when the relationship is not obvious.

Prefer:

```text
src/auth/middleware.ts — authentication boundary.
tests/auth/expired_token.test.ts — currently failing test.
```

Over a long list of every file touched during the session.

## Verification

Record only verification that actually occurred.

Include the check and its result.

Examples:

```text
better-test tests/auth/ — passing
better-lint src/auth/ — passing
better-check — failing: expired-token integration test
```

Never claim that a test, lint check, build, or other verification passed unless it was actually performed.

Distinguish:

* verified facts;
* inferred state;
* unresolved questions.

## Blockers

Record problems that prevent completion or materially affect the next action.

Include the known cause when it is established.

Do not turn hypothetical risks into blockers.

Use `None` when no blocker exists.

## Open Questions

Record unresolved questions that require evidence or a deliberate decision.

Do not include questions that can be answered directly by reading the current code.

An open question should explain why the answer matters when it is not obvious.

## Next Action

State the smallest concrete action another agent should take next.

Prefer:

```text
Run the expired-token integration test and inspect the
middleware expiration path before changing implementation.
```

Over:

```text
Continue authentication work.
```

The next action should be derived from the current state, unresolved issues, and remaining work.

## Writing Rules

Write **state, conclusions, and evidence**, not the conversation that produced them.

Preserve important reasoning when it prevents incorrect future decisions.

Do not preserve reasoning merely because it was lengthy.

A useful rule is:

> If forgetting this information could make the next agent do something incorrect or repeat meaningful work, preserve it.

## Verification on Handoff

Creating a handoff does not require a full repository inspection.

The agent should use its existing context to write the handoff.

Do not reread the repository solely to populate the handoff.

Verification belongs primarily to the receiving agent.

## Restoring a Handoff

When another agent receives a handoff:

1. Read the handoff.
2. Identify the objective and current state.
3. Identify constraints, decisions, review feedback, blockers, and open questions.
4. Inspect the relevant repository state.
5. Compare the repository with the recorded state.
6. Resolve stale or conflicting information.
7. Continue from `Next Action`.

Use targeted inspection.

```text
handoff
  ↓
relevant files
  ↓
git status / diff
  ↓
relevant symbols and tests
  ↓
continue
```

Do not reread the entire repository unless the handoff is missing, stale, contradictory, or insufficient.

If the handoff conflicts with the repository:

* treat the repository as authoritative for current implementation state;
* preserve explicit task constraints and review requirements unless there is evidence they changed;
* update the working state;
* do not blindly repeat previous work.

## Avoiding Hallucinated History

The receiving agent must not infer that an action occurred merely because the current code appears to contain its result.

Use explicit handoff evidence:

```text
Completed:
- Added transaction rollback handling.

Verification:
- Transaction integration test passed.
```

If verification or reasoning is unknown, record it as unknown rather than inventing it.

The same applies to review:

```text
Review Feedback:
- Reviewer requested transaction rollback coverage.

Review Resolution:
- Added rollback test.
- Verification pending.
```

Do not convert `Verification pending` into `passing` without running the test.

## Agent Interoperability

The skill must work across coding agents.

An agent may expose the workflow through:

* a slash command;
* a CLI command;
* an installed skill;
* an automatic lifecycle hook;
* another interface.

The interface may differ, but the handoff format and semantics remain portable.

The original conversation must not be required to understand the handoff.

## Storage

The recommended active handoff location is:

```text
.agent/context/handoff.md
```

Historical handoffs may be stored under:

```text
.agent/context/history/
```

Follow an existing repository convention when one is already established.

## Quality Test

Before creating a handoff, ensure another agent can determine:

* what the task is;
* what is already complete;
* what remains;
* which decisions are established;
* which approaches were rejected;
* what reviewers or other external feedback required;
* how that feedback was resolved;
* which constraints remain;
* which files matter;
* what has actually been verified;
* what is blocked;
* what questions remain;
* what action should happen next.

If missing information would cause meaningful rediscovery, duplicated work, or an incorrect decision, add it.

## Design Principle

> Preserve the minimum sufficient working state required for another agent to continue correctly, including the decisions, evidence, constraints, and feedback that shaped the current implementation.
