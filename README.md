# agentmaxx

Hooks, settings and skills for Claude Code, Codex and OpenCode. Less context per turn, fewer loops.

| Piece | Does | Number |
|---|---|---|
| tool search + contract | Schemas on demand; verdict first, batch calls, verify before "done" | prefix 63k → 17k tokens, −18%/task, 18/18 pass |
| `lessons` | Your corrections become rules every later session starts with | followed 5/5 vs 0/5 |
| `prompt_guard` | Short prompt → restate reading first; unknowns → list assumptions | 23 of 68 corrections were misreads; 3 of 4 caught |
| `guard` | Denies `rm -rf ~`, `curl \| sh`, force-push, `reset --hard`, secret reads | 0.45% of 14,846 calls denied, 61 were live secrets |
| `squeeze` | Big Bash output → errors, verdicts, head, tail; full text saved to grep | 138KB → 1.6KB, 91% of verdict lines kept |
| `research_log` | Near-duplicate web search denied once | 70% of research sessions never searched counter-evidence |
| `verify` | Runs tests, blocks "done" once on new failures | |
| `review` | Fresh-context `claude -p` reviews task + diff, blocks once | 6 s, 2¢ |
| `doctor` | Reads transcripts: where tokens go, which CLAUDE.md is fat, `--apply` | cache 86% of bill, 87k-token prefix, CLAUDE.md 28k of it |
| `claude-md` skill | Diets a fat CLAUDE.md, nothing deleted | 57k → 4.1k tokens |
| `research` skill | Stop criteria first, hypothesis map, disconfirming query | "nothing passes" ×59 vs "keep going" ×66 |
| `better-*` | 21 bounded CLI tools | |

```bash
make install && agentmaxx doctor
```

Off: `AGENTMAXX_{VERIFY,REVIEW,PROMPT_GUARD,RESEARCH_LOG}=0`. Per-repo: `agentmaxx init`. Method: [evals/RESULTS.md](evals/RESULTS.md).
