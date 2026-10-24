# better-related

File relationships: what touches a file (imports, tests, dependents, config).

## Usage

```bash
python3 better_related.py src/auth/service.py
python3 better_related.py config/settings.py --kind imports
```

## Output

Returns structured relationships: imported_by, imports, tested_by, depended_on_by, config_references.

## Why

**Problem:** Understanding what touches a file takes 4-5 separate grepping sessions (imports, tests, callers, configs, dependents).

**Solution:** `better-related` returns all relationships in one structured call.

Not benchmarked on its own. In the live A/B bench the model never called any `better-*` tool when native Grep, Read and Edit were available ([evals/RESULTS.md](../../evals/RESULTS.md)), so Claude Code no longer registers these as MCP tools; the saving is the bounded, structured output you get when you call it explicitly.
