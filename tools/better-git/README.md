# better-git

Compact, structured Git output for agents. It reduces repeated Git calls and redundant context without changing Git semantics.

| Command | Purpose |
|---|---|
| `status` | Branch and staged, unstaged, and untracked files. |
| `branch` | Branch, upstream, ahead, and behind. |
| `diff` | Staged and unstaged changes, optionally for one file. |
| `diff-summary` | Compact diff statistics. |
| `changed` | Changed files with additions, deletions, and state. |
| `recent` | Recent commits with metadata. |
| `log <path>` | Recent commits affecting a file. |
| `inspect <path>` | File history, current changes, and status. |
| `show <commit>` | Commit metadata and changed-file summary. |
| `conflicts` | Unresolved merge-conflict files. |
| `check` | Branch, status, changes, diff summary, and conflicts. |
| `context <path>` | Status, file history, and file changes in one call. |
| `review` | Complete working-tree review context in one call. |
| `review-branch <base>` | Branch history and complete changes against a base branch. |

Examples:

```bash
python3 tools/better-git/better_git.py check
python3 tools/better-git/better_git.py context src/auth.py
python3 tools/better-git/better_git.py review
python3 tools/better-git/better_git.py review-branch main
```