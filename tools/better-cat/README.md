# Inspect

Agent-optimized bounded file inspection.

Replaces raw `cat`/`sed` reads with exact, line-numbered ranges to reduce context usage.

Target: **50–90% less file-content context** when only part of a file is needed.

```bash
python3 tools/inspect/inspect.py src/auth.py --start 40 --end 80
```

Returns source unchanged; it only limits which lines enter context.