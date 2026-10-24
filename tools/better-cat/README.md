# Better Cat

Agent-optimized bounded file inspection.

Replaces raw `cat`/`sed` reads with exact, line-numbered ranges to reduce context usage.

Not benchmarked on its own. In the live A/B bench the model never called any `better-*` tool when native Grep, Read and Edit were available ([evals/RESULTS.md](../../evals/RESULTS.md)), so Claude Code no longer registers these as MCP tools; the saving is the bounded, structured output you get when you call it explicitly.

```bash
python3 tools/better-cat/better_cat.py src/auth.py:40-80
python3 tools/better-cat/better_cat.py src/auth.py:40-80 src/models.py:1-30 README.md
```

Spec syntax: `path`, `path:12-40`, `path:12-` (to end of file), or `path:12`.

Multiple specs share one output budget and cost one round trip, so batching reads is strictly cheaper than issuing them separately.

Returns source unchanged; it only limits which lines enter context.
