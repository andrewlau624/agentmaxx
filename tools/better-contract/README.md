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

**Token savings:** ~150-250 tokens per service analysis.
