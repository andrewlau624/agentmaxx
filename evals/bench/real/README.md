# Real-repo bench tasks

These are SWE-bench-style tasks taken from real bug-fix commits in three pure-Python repos. Each repo has no runtime dependencies, and its test suite runs with only the stdlib and pytest on Python 3.13. The repos are sqlparse (~4.4k lines), mistune (~6.4k lines) and boltons (~17k lines). Candidate commits were mined from history since 2021. Each one had to touch 1-3 non-test source files, change 6-120 lines and come with test changes. The list was then narrowed by hand to bugs where the symptom and the root cause are in different places, or where the fix depends on a subtle invariant: parser state machines, lexer regexes, CommonMark delimiter rules, the dead-slot bookkeeping in `IndexedSet`, and the dict-subclass pickle/copy protocol. Simple typo fixes and refactors were skipped.

For each task, `hidden.patch` holds only the test-file diff (parent..fix) and `fix.patch` holds only the source diff. `fix.patch` is for reference and is never shown to the agent. The agent starts at `sha`, the parent commit, and gets only `prompt`, which is a user-style bug report. `verify.py` (stdlib only) checks every task in both directions on a fresh worktree:

1. With `hidden.patch` applied, each `hidden_tests` node fails and each `hidden_guard_tests` node passes. Guard tests are new tests that already pass at the parent and must keep passing.
2. With `fix.patch` also applied, all of those nodes pass.
3. The full `regress_tests` suite then runs with no failures outside `known_failures`.

None of the parent suites had failures before any patch was applied, so every `known_failures` list is empty.

Run `python3 verify.py [task_id ...] [--no-regress] [--keep]`.

| task_id | repo | fix sha | files touched | verification |
|---|---|---|---|---|
| sqlparse-begin-end-semicolon | sqlparse | 1a3bfbd50b | `sqlparse/engine/statement_splitter.py` | PASS: 1 fail->pass, 1 guard, 480 regress ok |
| sqlparse-tzcast-whitespace | sqlparse | 3d3df9dcfb | `sqlparse/engine/grouping.py` | PASS: 1 fail->pass, 421 regress ok |
| sqlparse-strip-comments-hints | sqlparse | af6df6c662 | `sqlparse/filters/others.py` | PASS: 2 fail->pass, 463 regress ok |
| sqlparse-between-leading-dot-float | sqlparse | a194d3187b | `sqlparse/keywords.py` | PASS: 2 fail->pass, 1 guard, 497 regress ok |
| mistune-emphasis-mod3 | mistune | 2d26bc8fc9 | `src/mistune/inline_parser.py` | PASS: 2 fail->pass, 1113 regress ok |
| mistune-table-delimiter-row | mistune | 86f9fd1d7a | `src/mistune/plugins/table.py` | PASS: 4 fail->pass, 1143 regress ok |
| mistune-list-directive-markers | mistune | 03eacc5cf6 | `src/mistune/list_parser.py` | PASS: 1 fail->pass, 1 guard, 1139 regress ok |
| mistune-footnote-block-backref | mistune | 9b6220486d | `src/mistune/plugins/footnotes.py` | PASS: 2 fail->pass, 959 regress ok |
| boltons-indexedset-slice-after-remove | boltons | 609cabe932 | `boltons/setutils.py` | PASS: 2 fail->pass, 439 regress ok |
| boltons-omd-copy | boltons | ebc7a8f776 | `boltons/dictutils.py` | PASS: 1 fail->pass, 442 regress ok |
