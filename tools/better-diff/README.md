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

Not benchmarked on its own. In the live A/B bench the model never called any `better-*` tool when native Grep, Read and Edit were available ([evals/RESULTS.md](../../evals/RESULTS.md)), so Claude Code no longer registers these as MCP tools; the saving is the bounded, structured output you get when you call it explicitly.
