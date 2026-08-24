# better-diff

Ranked diff generator: see what changed with minimal context.

## Usage

```bash
python3 better_diff.py "src/auth" --since "2 days ago"
python3 better_diff.py "service.py" --commits 3
```

## Output

Returns structured diffs, ranked by relevance and impact.

## Why

**Problem:** Understanding changes means reading massive diffs; agents need only the relevant parts.

**Solution:** `better-diff` generates ranked diffs with bounded output.

**Token savings:** ~100-200 tokens per diff request.
