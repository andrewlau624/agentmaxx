---
name: fast-commit
description: Batched git commit workflow. Use whenever asked to commit, write a commit message, or save work. One shell call gathers repository state, one silent reasoning step composes the message, one shell call commits — Claude only where needed.
---

# Fast commit

Every Claude round trip re-sends the full conversation. Mechanical git steps cost almost nothing in shell; they cost a full context re-send each time they route through the model. Three steps total, never more:

1. **Gather** — a single bash call, nothing else alongside it:

   ```sh
   git status --short && git diff HEAD --stat && git diff HEAD
   ```

   If the patch exceeds ~600 lines, truncate to the first 600 — `--stat` already carries the shape.

2. **Compose silently** — write the commit message from the gathered diff alone. No file reads. No second git call. No narration. Conventional subject ≤72 chars, imperative mood ("add telemetry target", not "added"); body only for why and tradeoffs, never a file list.

3. **Commit** — a single bash call:

   ```sh
   git add -A && git commit -m "<subject>" -m "<body>"
   ```

Never read files outside the diff to "understand context", never run git commands between gather and commit, never print the message before committing it. Close with the commit hash only.
