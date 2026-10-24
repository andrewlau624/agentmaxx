# Better Context

Locate code and return the surrounding source in **one** call.

The dominant agent pattern is search, then read each hit's region. With separate tools that is one round trip per hit, and every round trip re-sends the entire accumulated context. This collapses the sequence.

Not benchmarked on its own. In the live A/B bench the model never called any `better-*` tool when native Grep, Read and Edit were available ([evals/RESULTS.md](../../evals/RESULTS.md)), so Claude Code no longer registers these as MCP tools; the saving is the bounded, structured output you get when you call it explicitly.

```bash
python3 tools/better-context/better_context.py "authenticate"
python3 tools/better-context/better_context.py "authenticate" --type py --max-hits 3
python3 tools/better-context/better_context.py "authenticate" "authorize" --context-lines 40
```

Returns a bounded window around each ranked hit, sharing one output budget across regions.

Composes `better-grep` for ranking and `better-cat` for windowing rather than reimplementing either.
