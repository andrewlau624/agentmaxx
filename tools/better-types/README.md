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

**Token savings:** ~100-300 tokens depending on file size.
