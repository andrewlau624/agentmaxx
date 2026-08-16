# Better Grep

Agent-optimized repository search built on `rg`.

Replaces raw `rg`/`grep` output with ranked, structured, bounded results to reduce context usage.

Target: **30–80% less search-result context**, depending on repository and query.

```bash
python3 tools/better-grep/better_grep.py "authenticate"
python3 tools/better-grep/better_grep.py "authenticate" --path src --type py
python3 tools/better-grep/better_grep.py "authenticate" "authorize" "login"
```

Multiple patterns run in a single `rg` pass and a single round trip. Prefer that over one call per pattern — each extra call re-sends the whole accumulated context.

Uses rg internally; specialized raw searches remain supported.
