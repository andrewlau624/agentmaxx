---
name: reviewer-style
description: Learns how a specific GitHub reviewer reviews, from everything they've written on a repo's PRs (inline comments with the code they point at, review summaries, conversation), and saves their rules with real examples so code-review can review like them. Use when asked to learn a reviewer's style, review "like <person>", audit against someone's concerns (e.g. "Jonathan's concerns"), or set up review rules for a new reviewer.
argument-hint: "OWNER/REPO USER"
---

# Learn a reviewer's style

The goal is a file that lets `code-review` say what this reviewer would say, on code they haven't seen. That takes their recurring concerns, how strongly they hold each one, and real examples of the code that set them off. A list of their opinions isn't enough. Google's review-comment model learned from "the reviewer comments, and the edits the author performed to address those comments" (Google Research blog, "Resolving code review comments with ML"), so the comments the author acted on count most.

## 1. Scrape

Run the bundled script (needs an authenticated `gh`; if `gh auth status` fails, stop and give the user that command):

```sh
python3 ~/.claude/skills/reviewer-style/scrape.py OWNER/REPO USER --prs 150 --out /tmp/reviews-USER.jsonl
```

It finds PRs the user reviewed or commented on and collects, with pagination, three kinds of text: inline comments with the diff hunk they point at, review summaries (approve or request-changes text), and PR conversation. It marks an inline comment `addressed` when the code under it changed afterwards. On astral-sh/ruff it pulled 413 comments from 100 PRs, where the old inline commands got 283 with no code and no review summaries.

If it finds fewer than about 40 comments, raise `--prs`, or add a second repo the reviewer works on, before drawing conclusions. Tell the user how much you got.

## 2. Read all of it

Read the JSONL in chunks of about 100 lines. If it runs past about 400 comments, hand chunks to subagents that each return themes with counts and example ids. Skip bot-like text (CI links, "LGTM", "thanks!", merge notices) and pure questions with no stated preference.

For each comment, ask what it's really objecting to. Say it in general terms that would apply to code the reviewer hasn't seen ("errors from the parser must carry the source span"), not as the incident ("line 40 should pass span"). Then group comments by concern.

## 3. Keep what holds up

For each concern, count the distinct PRs it appears on, and how many of those comments were `addressed`. Keep a rule when it appears on 2 or more PRs, or on one PR with the author changing the code in response. Drop the rest. Google calibrated its model to 50% precision because "incorrect suggested edits take the developers time". A rule the reviewer doesn't really hold makes every future review worse.

Rank severity by what the reviewer did, not by your own taste. Request-changes reviews and comments that were addressed point to must-fix. Comments phrased as "nit:", "optional", or "consider" are nits. Things the reviewer explicitly let go ("fine here", "not blocking") go under "Never flag".

## 4. Write the reviewer file

Write `~/.config/agentmaxx/reviewers/USER.md`, or `.reviewers/USER.md` in the repo if the user wants it shared with the team:

```markdown
# USER on OWNER/REPO (scraped YYYY-MM-DD: 413 comments, 100 PRs)

## Must-fix
- Errors from the parser carry the source span. (7 PRs, 6 addressed)
  e.g. crates/parser/src/lexer.rs: "This loses the range. Can we return a `ParseError` with the token's span so the diagnostic points somewhere useful?"

## Nits
- Prefer `&str` over `String` for read-only parameters. (4 PRs, 3 addressed)
  e.g. ...

## Never flag
- Long match arms in generated code. (said "fine, it's generated" twice)

## How they write comments
- Short, ends in a question, offers the fix ("Can we ...?"). Explains the why when blocking.
```

Give each rule one real example: a short quote plus the path. Keep it to the top 25 rules or so. These rules are backed by evidence, so they don't go through `code-review`'s probation step.

## 5. Confirm

One line: `USER: 413 comments from 100 PRs, 18 rules (7 must-fix, 9 nits, 2 never-flag) -> ~/.config/agentmaxx/reviewers/USER.md`. Then name the 3 strongest rules so the user can sanity-check them.

## Notes

- `code-review` reads reviewer files when asked to review like that person, or when the repo has `.reviewers/`.
- When the user corrects a rule ("he doesn't care about that anymore"), edit the reviewer file directly.
- Never fill gaps with generic best practice. If the scrape is thin, the file is short and says so.
