# better-compress

Route text to the best compressor for its shape. JSON goes to headroom's
table-izer when installed, else a vendored stdlib JSON crusher; logs, diffs,
and prose use the builtin (which reuses `hooks/squeeze.py` when present);
`--run` executes commands under lowfat when it covers them. Missing backends
and backend failures degrade silently to the builtin. Never empty, never
expands.

```bash
python3 tools/better-compress/better_compress.py --file out.json --budget 2000
python3 tools/better-compress/better_compress.py --command "pytest -q" < test.log
python3 tools/better-compress/better_compress.py --run git log -p -20
python3 tools/better-compress/better_compress.py --file out.json --json  # machine-readable
```

Optional backends: `make compress-deps` installs headroom into
`~/.agentmaxx/.venv` and lowfat into `~/.local/bin`. Without them the tool is
fully functional on the builtin alone. `AGENTMAXX_VENV` overrides the venv
path; `AGENTMAXX_SQUEEZE_ROUTER=1` lets the squeeze hook route JSON outputs
through this tool.
