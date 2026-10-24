# better-structure

Architecture graph: dependency tree and entry points.

## Usage

```bash
python3 better_structure.py
python3 better_structure.py --show-cycles
python3 better_structure.py --max-depth 3
```

## Output

Returns dependency graph, entry points, import cycles, architecture layers.

## Why

**Problem:** Understanding codebase architecture means reading many files; agents need high-level structure.

**Solution:** `better-structure` generates an ASCII architecture overview.

Not benchmarked on its own. In the live A/B bench the model never called any `better-*` tool when native Grep, Read and Edit were available ([evals/RESULTS.md](../../evals/RESULTS.md)), so Claude Code no longer registers these as MCP tools; the saving is the bounded, structured output you get when you call it explicitly.
