# better-contract

API contract extractor: routes, request/response types, handlers.

## Usage

```bash
python3 better_contract.py "src/routes"
python3 better_contract.py "api.py" --format openapi
```

## Output

Returns structured API: {routes, methods, request_schemas, response_schemas, handlers}.

## Why

**Problem:** Understanding a service's API means reading route files + type definitions spread across files.

**Solution:** `better-contract` extracts all API info in one call.

Not benchmarked on its own. In the live A/B bench the model never called any `better-*` tool when native Grep, Read and Edit were available ([evals/RESULTS.md](../../evals/RESULTS.md)), so Claude Code no longer registers these as MCP tools; the saving is the bounded, structured output you get when you call it explicitly.
