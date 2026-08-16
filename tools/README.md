# Tools

Tools provide optimized interfaces for common agent operations.

`registry.yaml` is the source of truth for the tool list — every tool directory must have a
matching entry (enforced by `test_registry.py`). It's also where `agentmaxx init` reads the
signatures it injects into a repo's contract, so an agent never has to run `--help` to learn
an interface.

## Requirements

Every tool must:

- Minimize returned context without removing information required for correctness.
- Prefer structured output over raw command output.
- Bound output size.
- Accept multiple inputs (files, ranges, patterns) in one call rather than requiring one call
  per input — a round trip costs more than the bytes it returns.
- Reuse existing repository capabilities.
- Avoid duplicating functionality already available elsewhere.
- Fail explicitly when required dependencies are unavailable.
- Have deterministic behavior where practical.
- Be independently testable.
- Avoid third-party dependencies unless they provide substantial value.
- Have a `README.md`, a `test_<module>.py`, and a `registry.yaml` entry.

## Design principle

A tool should replace multiple lower-level operations or materially reduce the context required for an agent to complete a task.

Do not add features or options without a concrete use case.
