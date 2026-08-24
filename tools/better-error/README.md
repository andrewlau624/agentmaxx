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

**Token savings:** ~50-150 tokens per error (compression + targeting).
