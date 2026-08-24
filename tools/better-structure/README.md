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

**Token savings:** ~100-200 tokens per codebase analysis (high-level understanding upfront).
