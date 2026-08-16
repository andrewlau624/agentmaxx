# Better Find

Agent-optimized file discovery.

Replaces noisy `find` output with bounded, structured results.

Target: **30–80% less** filesystem-search context.

```bash
python3 tools/better-find/better_find.py . --name "*.py"
```

Limits output and skips common generated/dependency directories.