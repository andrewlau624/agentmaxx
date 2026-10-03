---
name: better-tools
description: agentmaxx CLI tools for ranked repo search, bounded reads, batched atomic edits, call graphs, and parallel test/lint runs. Use when starting cold in an unfamiliar repo, tracing callers/callees, or batching many edits.
---

# better-* tools

Installed at `{{TOOLS_ROOT}}`. Signatures below; never call `--help`.

| Tool | Purpose | Invocation |
|---|---|---|
| better-explore | Rank search results to start exploration | `python3 {{TOOLS_ROOT}}/better-explore/better_explore.py TASK [--path P] [--num-candidates N] [--max-searches N]` |
| better-context | Search + surrounding source in one call | `python3 {{TOOLS_ROOT}}/better-context/better_context.py QUERY... [--path P] [--type EXT] [--max-hits N] [--context-lines N] [--max-output-chars N]` |
| better-grep | Ranked repo code search | `python3 {{TOOLS_ROOT}}/better-grep/better_grep.py QUERY... [--path P] [--type EXT] [--max-results N]` |
| better-cat | Bounded file ranges (`path`, `path:12-40`, `path:12`) | `python3 {{TOOLS_ROOT}}/better-cat/better_cat.py SPEC... [--max-output-chars N]` |
| better-edit | Batch exact-string edits, atomic | `python3 {{TOOLS_ROOT}}/better-edit/better_edit.py [EDITS_JSON]` — JSON array of `{path, old, new, replace_all?}` or stdin |
| better-find | Find files, bounded results | `python3 {{TOOLS_ROOT}}/better-find/better_find.py [PATH] [--name GLOB] [--type f\|d]` |
| better-tree | Bounded directory tree | `python3 {{TOOLS_ROOT}}/better-tree/better_tree.py [PATH] [--depth N] [--max-entries N] [--hidden]` |
| better-blame | Compact git blame | `python3 {{TOOLS_ROOT}}/better-blame/better_blame.py PATH [-L START,END] [-r REV]` |
| better-git | Repo state, history, diffs, branches, PRs | `python3 {{TOOLS_ROOT}}/better-git/better_git.py COMMAND [ARGS...]` |
| better-check | Test/lint/typecheck/build in parallel | `python3 {{TOOLS_ROOT}}/better-check/better_check.py [--test CMD...] [--lint CMD...] [--typecheck CMD...] [--build CMD...] [--timeout N] [--stop-on-failure]` |
| better-lint | Lint with auto-detection | `python3 {{TOOLS_ROOT}}/better-lint/better_lint.py [--linter NAME] [--quiet] [COMMAND...]` |
| better-test | Tests with bounded structured output | `python3 {{TOOLS_ROOT}}/better-test/better_test.py [--framework pytest\|unittest\|npm] [--command CMD] [--quiet]` |
| better-symbol | Definitions, usages, implementations | `python3 {{TOOLS_ROOT}}/better-symbol/better_symbol.py SYMBOL [--kind definition\|usage\|implementation]` |
| better-trace | Call graph callers/callees | `python3 {{TOOLS_ROOT}}/better-trace/better_trace.py FUNCTION [--direction callers\|callees\|both] [--depth N]` |
| better-related | Imports, imported-by, tests, dependents | `python3 {{TOOLS_ROOT}}/better-related/better_related.py FILE [--kind all\|imports\|imported_by\|tests\|dependents]` |
| better-types | Type/interface signatures | `python3 {{TOOLS_ROOT}}/better-types/better_types.py TYPENAME [--kind all\|class\|interface\|type\|struct]` |
| better-error | Exception → actionable context | `python3 {{TOOLS_ROOT}}/better-error/better_error.py [--file PATH \| --content TEXT]` |
| better-diff | Ranked diffs, bounded output | `python3 {{TOOLS_ROOT}}/better-diff/better_diff.py PATH [--since TIME \| --commits N]` |
| better-contract | Routes, schemas, handlers | `python3 {{TOOLS_ROOT}}/better-contract/better_contract.py PATH [--format json\|openapi]` |
| better-structure | Architecture graph, dependency tree | `python3 {{TOOLS_ROOT}}/better-structure/better_structure.py [--path P] [--max-depth N] [--show-cycles]` |

Workflow: known area → `better-context` keywords, read top results, follow imports/callers, implement. Unknown area → `better-explore "task"`, then switch to `better-context` on the top candidate. Multiple unrelated patterns → one `better-grep` call with several queries. Edits → one batched `better-edit` call (atomic validation). Verification → `better-check`; history → `better-git`/`better-blame`. Once a file is identified, stop using `better-explore`.

These save round trips, not cleverness: one call returning three results beats three calls. Native Grep/Read/Edit are fine for single targeted lookups.
