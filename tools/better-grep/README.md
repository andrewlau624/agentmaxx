# Better Grep

Agent-optimized repository search built on `rg`.

Replaces raw `rg`/`grep` output with ranked, structured, bounded results to reduce context usage.

Not benchmarked on its own. In the live A/B bench the model never called any `better-*` tool when native Grep, Read and Edit were available ([evals/RESULTS.md](../../evals/RESULTS.md)), so Claude Code no longer registers these as MCP tools; the saving is the bounded, structured output you get when you call it explicitly.

```bash
python3 tools/better-grep/better_grep.py "authenticate"
python3 tools/better-grep/better_grep.py "authenticate" --path src --type py
python3 tools/better-grep/better_grep.py "authenticate" "authorize" "login"
```

Multiple patterns run in a single `rg` pass and a single round trip. Prefer that over one call per pattern — each extra call re-sends the whole accumulated context.

Uses rg internally; specialized raw searches remain supported.
