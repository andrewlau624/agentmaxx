# better-symbol

Universal symbol finder: locate definitions, usages, and implementations.

## Usage

```bash
python3 better_symbol.py "UserService" --kind definition
python3 better_symbol.py "authenticate" --kind usage --max-results 20
python3 better_symbol.py "Handler" --kind implementation
```

## Output

Returns structured JSON with symbol locations, including file, line number, and context.

## Why

**Problem:** Understanding a codebase means finding where things are defined and used. Agents grep for a symbol, get 50+ results, read 10 files to find the actual definition.

**Solution:** `better-symbol` returns definitions first, then usages/implementations separately. One call replaces 3-5 grep searches + manual filtering.

Not benchmarked on its own. In the live A/B bench the model never called any `better-*` tool when native Grep, Read and Edit were available ([evals/RESULTS.md](../../evals/RESULTS.md)), so Claude Code no longer registers these as MCP tools; the saving is the bounded, structured output you get when you call it explicitly.

## Kinds

- `definition` - Where the symbol is declared (class, function, interface, variable)
- `usage` - Where the symbol is referenced or called
- `implementation` - Classes/types implementing an interface/protocol
