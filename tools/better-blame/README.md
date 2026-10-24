# Better Blame

Agent-optimized git blame inspection.

Replaces noisy `git blame` output with bounded, structured results.

Not benchmarked on its own. In the live A/B bench the model never called any `better-*` tool when native Grep, Read and Edit were available ([evals/RESULTS.md](../../evals/RESULTS.md)), so Claude Code no longer registers these as MCP tools; the saving is the bounded, structured output you get when you call it explicitly.

```bash
python3 tools/better-blame/better_blame.py path/to/file.py
```

Limits output while preserving useful line ownership and history.