# Search

Agent-optimized repository search built on `rg`.

Replaces raw `rg`/`grep` output with ranked, structured, bounded results to reduce context usage.

Target: **30–80% less search-result context**, depending on repository and query.

```bash
python3 tools/search/search.py "authenticate"
python3 tools/search/search.py "authenticate" --path src --type py
```

Uses rg internally; specialized raw searches remain supported.