# Tools

Twenty-one `better-*` CLI tools: ranked search (`better-grep`, `better-explore`), bounded reads
(`better-cat`, `better-context`), batched edits (`better-edit`), code structure (`better-symbol`,
`better-trace`, `better-related`, `better-structure`, `better-types`, `better-contract`), git
(`better-git`, `better-diff`, `better-blame`), checks (`better-test`, `better-lint`,
`better-check`, `better-error`), listings (`better-find`, `better-tree`) and output compression
(`better-compress`). Each bounds its output and takes several inputs in one call.

## What the measurements say

- In the live A/B bench ([evals/RESULTS.md](../evals/RESULTS.md)), the model never called a
  single `better-*` tool when it had native Grep, Read and Edit, and the MCP server connecting
  after the first request changed the tool list and forced full cache rewrites. The arm that
  shipped them as MCP tools cost +89% per task. Claude Code therefore no longer registers them;
  they are listed in the on-demand `better-tools` skill and remain native tools in opencode and
  Codex.
- Over 30 days of real sessions, discovery before the first edit took a median of 1 tool call
  (p90 7; 6% of 819 task episodes needed 10 or more), so a better search tool has little to
  save on the typical task.
- No tool is benchmarked on its own. The per-tool READMEs describe what each returns, not a
  measured saving.

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
