# Better Cat

Agent-optimized bounded file inspection.

Replaces raw `cat`/`sed` reads with exact, line-numbered ranges to reduce context usage.

Target: **50–90% less file-content context** when only part of a file is needed.

```bash
python3 tools/better-cat/better_cat.py src/auth.py:40-80
python3 tools/better-cat/better_cat.py src/auth.py:40-80 src/models.py:1-30 README.md
```

Spec syntax: `path`, `path:12-40`, `path:12-` (to end of file), or `path:12`.

Multiple specs share one output budget and cost one round trip, so batching reads is strictly cheaper than issuing them separately.

Returns source unchanged; it only limits which lines enter context.
