# better-error

Exception parser: extract actionable error context from stack traces.

## Usage

```bash
python3 better_error.py < stacktrace.txt
python3 better_error.py --file error.log
```

## Output

Returns structured error: type, message, failing line with context, probable cause.

## Why

**Problem:** Stack traces are verbose; agents need to parse them manually to extract the actual failing line and context.

**Solution:** `better-error` parses the trace and returns just the actionable info.

Not benchmarked on its own. In the live A/B bench the model never called any `better-*` tool when native Grep, Read and Edit were available ([evals/RESULTS.md](../../evals/RESULTS.md)), so Claude Code no longer registers these as MCP tools; the saving is the bounded, structured output you get when you call it explicitly.
