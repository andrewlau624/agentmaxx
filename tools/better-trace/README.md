# better-trace

Call graph tracer: understand what calls a function and what it calls.

## Usage

```bash
python3 better_trace.py "authenticate" --direction callers --depth 2
python3 better_trace.py "handleRequest" --direction callees --depth 3
python3 better_trace.py "processData" --show-entry-points
```

## Output

Returns structured call tree with entry points highlighted.

## Why

**Problem:** Agents need to understand call chains—"what calls this?" or "what does this call?"—requiring manual tracing through imports and definitions.

**Solution:** `better-trace` returns a call tree in one call, with entry points highlighted so agents understand execution flow immediately.

**Token savings:** ~200-400 tokens per trace request.

## Directions

- `callers` - What functions call this one?
- `callees` - What functions does this one call?
- `both` - Bidirectional trace
