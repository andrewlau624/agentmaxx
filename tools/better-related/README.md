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

**Token savings:** ~150-200 tokens per file analysis.
