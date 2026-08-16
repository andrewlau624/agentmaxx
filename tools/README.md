# Tools

Tools provide optimized interfaces for common agent operations.

## Requirements

Every tool must:

- Minimize returned context without removing information required for correctness.
- Prefer structured output over raw command output.
- Bound output size.
- Reuse existing repository capabilities.
- Avoid duplicating functionality already available elsewhere.
- Fail explicitly when required dependencies are unavailable.
- Have deterministic behavior where practical.
- Be independently testable.
- Avoid third-party dependencies unless they provide substantial value.

## Design principle

A tool should replace multiple lower-level operations or materially reduce the context required for an agent to complete a task.

Do not add features or options without a concrete use case.