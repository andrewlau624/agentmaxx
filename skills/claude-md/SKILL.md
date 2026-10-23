---
name: claude-md
description: Put a CLAUDE.md on a diet and structure repo docs so an agent reads what the task needs and nothing else. Use when a CLAUDE.md is over ~8k tokens, when doctor flags one, when asked to write or reorganize CLAUDE.md or agent docs, or when session notes keep landing in CLAUDE.md.
---

# CLAUDE.md diet

Every token in CLAUDE.md rides on every request and every subagent in the repo, and is rewritten in full whenever the cache misses. On this machine a 192k-char file cost 43k tokens a request. Rules the agent needs on every turn stay; everything else moves to docs behind a one-line index.

## What belongs where

| Goes in CLAUDE.md (target ≤2k tokens, hard stop 5k) | Goes in `docs/memory/` (read on demand) | Goes nowhere |
|---|---|---|
| Objective, priorities, user permissions ("ssh X is always allowed") | Session logs, findings, results, audits | Prose that restates the code |
| Hard facts and traps that change what the agent does next | Specs, schemas, API surfaces, protocols | Status that will be stale in a week |
| "Do not redo" lists, kept to one line each | Rankings and candidate lists with reasoning | Praise, history of who decided what |
| Methodology rules, checklists, where memory lives | Philosophy and long-form "how to think" | Duplicates of anything above |

A line stays only if the agent would act differently on a random turn without it.

## Process

1. **Measure.** `python3 ~/.claude/skills/claude-md/measure.py CLAUDE.md`. It prints tokens per `##` section with a keep/move verdict and the reason, the proposed sizes, and which `###` subsections inside moved sections read like user-stated rules. Don't read the file; read the report.
2. **Correct the verdicts.** `--keep N` / `--move N` for sections the heuristic got wrong. Keep anything that says "(user ...)", "permanent", "non-negotiable", "do not". Move anything with a date in the heading unless it is a rule.
3. **Apply.** Add `--apply`. It writes a byte-exact backup to `docs/memory/CLAUDE.md.<stamp>.before-diet`, one file per moved section, `docs/memory/INDEX.md` with one line per file, copies user-stated `###` rules from moved sections into a "Standing rules recorded during sessions" section, and rewrites CLAUDE.md as the kept sections plus a pointer to the index. Nothing is deleted.
4. **Verify.** Re-run the measure. Check every original line is in CLAUDE.md or a moved file (the apply step prints the counts). Read the new CLAUDE.md once, in full, and tighten: merge duplicate rules, cut dates and attributions from rule lines, turn paragraphs into one-line rules. Report before and after tokens.
5. **Set the habit.** The pointer tells future sessions: new findings go into a new `docs/memory/` file plus one index line, never into CLAUDE.md. If the repo has a research prompt or loop that says "append to CLAUDE.md", change it.

## Writing docs an agent can use

- `docs/memory/INDEX.md`: one line per file, `name (tokens): subject. First sentence.` An agent reads the index, then one or two files. Never a file that says "see all of the above".
- Stable headings: a file's `#` is its subject, `##` are the questions it answers. Agents grep headings.
- Lead with the verdict: the number and the decision in the first line, method after.
- Dates in filenames for logs (`2026-10-08-nx-result.md`), subjects for everything else.
- Each fact lives in one place. A rule derived from a session goes in CLAUDE.md; the session that produced it goes in docs with a line pointing back.
- No file over ~3k tokens; split by subject when it grows.
