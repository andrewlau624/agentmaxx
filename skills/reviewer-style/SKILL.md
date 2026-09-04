---
name: reviewer-style
description: Scrape a GitHub reviewer's historical review comments and distill their recurring conventions into the review-style standard. Use when asked to learn a reviewer's style, audit against a specific reviewer (e.g. "Jonathan's concerns"), or bootstrap the code-review memory for a new reviewer.
---

# Reviewer style scraping

Turn a reviewer's past comments into the style file `code-review` enforces. One scrape, one distilled standard — the reviewer's opinions become `must-fix`/`nit`/`never-flag` rules instead of a pile of one-off threads.

## Workflow

1. **Scrape** the reviewer's inline review comments on merged PRs, newest first:

   ```sh
   gh api "search/issues?q=repo:OWNER/REPO+commenter:USER+type:pr&per_page=100" \
     --jq '.items[].number' | sort -n > /tmp/rev-prs.txt
   while read n; do
     gh api "repos/OWNER/REPO/pulls/$n/comments" \
       --jq '.[] | select(.user.login=="USER") | "[\(.path):\(.line // .original_line // "?")] \(.body)"'
   done < /tmp/rev-prs.txt > /tmp/rev-comments.txt
   ```

   Also pull issue-level comments if the reviewer reviews at that level:

   ```sh
   gh api "search/issues?q=repo:OWNER/REPO+commenter:USER" \
     --jq '.items[] | select(.pull_request) | .number' | sort -u \
     | head -50 | while read n; do
       gh api "repos/OWNER/REPO/issues/$n/comments" \
         --jq '.[] | select(.user.login=="USER") | .body'
     done >> /tmp/rev-comments.txt
   ```

   Scope to feature PRs (`select(.pull_request)`) — release/CI/version PRs carry noise, not style.

2. **Cluster** the comments by the concern they name. Read the full set, then group recurring themes:

   - `no silent fallbacks` → a must-fix rule
   - `use base settings for config` → a nit or must-fix
   - `paths in constants` / `enums not strings` / `stronger types` → nits
   - `uuid not string ids` → must-fix
   - `how does this scale` / `cache this` → must-fix when the answer is "it doesn't"
   - `should have a protocol` → nit (shared abstraction)

   A comment that names a *different* rule than the thread it's on is a real concern, not a mis-click. A comment that is only a question ("is this correct?") with no stated preference is not a rule — skip it.

3. **Write** the distilled standard to `~/.config/agentmaxx/review-style.md` (create if missing), in the format `code-review` reads:

   ```markdown
   ## Must-fix (treat as bugs)
   - no silent fallbacks; every except logs and re-raises or returns a logged fallback
   - ids are UUID, never strings, across the Temporal wire too

   ## Style nits
   - tunables live in BaseSettings, not module constants
   - URL paths and header names live in the module config, not inlined at call sites
   - enums over strings for categorical fields
   - prefer shared protocols for cross-connector behavior

   ## Never flag
   - raw SQL in Alembic revisions

   ## Probation (entered YYYY-MM-DD)
   - one generalized rule per recurring comment theme
   ```

   Rules go under `## Probation` first, same as `code-review`'s own growth brake — they promote only after firing again. Keep it under 40 lines; merge duplicates.

4. **Confirm** with one line: `scraped <n> comments from <user> → saved <k> rules to review-style.md`.

## Notes

- The target file is the same one `code-review` reads, so after this skill runs, every review enforces the scraped style automatically — no second hop.
- Prefer the reviewer's *stated rule* over the incident. "we should have a protocol for crawl as well?" becomes "prefer shared protocols for cross-connector behavior", not "Jonathan wanted a crawl protocol in 5437".
- If the reviewer's threads already have "Fixed in …" replies, the fix is the rule, not the complaint — the concern that *needed* fixing is the one to record.
- `gh` is the only external dependency; if it is not authenticated, fail explicitly with the command to run, never fabricate a style.