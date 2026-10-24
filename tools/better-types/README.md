# better-types

Type/interface extractor: get signatures without implementation.

## Usage

```bash
python3 better_types.py "User"
python3 better_types.py "Handler" --kind interface
python3 better_types.py "Config" --kind struct
```

## Output

Returns type signature, fields, methods, without implementation details.

## Why

**Problem:** Understanding a type means reading entire files; agents need only the interface.

**Solution:** `better-types` extracts just the signature and fields.

Not benchmarked on its own. In the live A/B bench the model never called any `better-*` tool when native Grep, Read and Edit were available ([evals/RESULTS.md](../../evals/RESULTS.md)), so Claude Code no longer registers these as MCP tools; the saving is the bounded, structured output you get when you call it explicitly.
