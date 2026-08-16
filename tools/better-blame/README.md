# Better Blame

Agent-optimized git blame inspection.

Replaces noisy `git blame` output with bounded, structured results.

Target: **30–80% less** blame context.

```bash
python3 tools/better-blame/better_blame.py path/to/file.py
```

Limits output while preserving useful line ownership and history.