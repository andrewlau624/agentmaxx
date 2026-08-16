#!/usr/bin/env python3

import argparse
import json
import subprocess


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip() or "git command failed"
        )

    return result.stdout.strip()


def parse_commits(output: str) -> list[dict]:
    commits = []

    for line in output.splitlines():
        if not line.strip():
            continue

        parts = line.split("\t", 3)

        if len(parts) == 4:
            commit, author, date, subject = parts
            commits.append(
                {
                    "commit": commit,
                    "author": author,
                    "date": date,
                    "subject": subject,
                }
            )

        elif len(parts) == 3:
            commit, date, subject = parts
            commits.append(
                {
                    "commit": commit,
                    "date": date,
                    "subject": subject,
                }
            )

    return commits


def parse_numstat(output: str) -> list[dict]:
    files = []

    for line in output.splitlines():
        if not line.strip():
            continue

        parts = line.split("\t", 2)

        if len(parts) != 3:
            continue

        additions, deletions, path = parts

        try:
            additions_value = int(additions)
        except ValueError:
            additions_value = additions

        try:
            deletions_value = int(deletions)
        except ValueError:
            deletions_value = deletions

        files.append(
            {
                "additions": additions_value,
                "deletions": deletions_value,
                "file": path,
            }
        )

    return files


def status() -> dict:
    branch_name = run_git("branch", "--show-current")
    porcelain = run_git("status", "--short")

    staged = []
    unstaged = []
    untracked = []

    for line in porcelain.splitlines():
        if len(line) < 3:
            continue

        index = line[0]
        worktree = line[1]
        path = line[3:]

        if index == "?" and worktree == "?":
            untracked.append(path)
            continue

        if index != " ":
            staged.append(path)

        if worktree != " ":
            unstaged.append(path)

    return {
        "branch": branch_name,
        "staged": staged,
        "unstaged": unstaged,
        "untracked": untracked,
    }


def branch() -> dict:
    current = run_git("branch", "--show-current")

    try:
        upstream = run_git(
            "rev-parse",
            "--abbrev-ref",
            "--symbolic-full-name",
            "@{upstream}",
        )
    except RuntimeError:
        upstream = ""

    ahead = 0
    behind = 0

    if upstream:
        counts = run_git(
            "rev-list",
            "--left-right",
            "--count",
            f"HEAD...{upstream}",
        ).split()

        if len(counts) == 2:
            try:
                ahead = int(counts[0])
                behind = int(counts[1])
            except ValueError:
                pass

    return {
        "branch": current,
        "upstream": upstream,
        "ahead": ahead,
        "behind": behind,
    }


def diff(path: str | None = None) -> dict:
    args = ("--", path) if path else ()

    return {
        "unstaged": run_git("diff", *args),
        "staged": run_git("diff", "--cached", *args),
    }


def diff_summary(path: str | None = None) -> dict:
    args = ("--", path) if path else ()

    return {
        "unstaged": run_git(
            "diff",
            "--stat",
            *args,
        ).splitlines(),
        "staged": run_git(
            "diff",
            "--cached",
            "--stat",
            *args,
        ).splitlines(),
    }


def changed() -> dict:
    files = []

    for state, args in (
        ("staged", ("diff", "--cached", "--numstat")),
        ("unstaged", ("diff", "--numstat")),
    ):
        output = run_git(*args)

        for entry in parse_numstat(output):
            files.append(
                {
                    "path": entry["file"],
                    "additions": entry["additions"],
                    "deletions": entry["deletions"],
                    "state": state,
                }
            )

    return {"files": files}


def recent(limit: int = 10) -> list[dict]:
    if limit < 1:
        raise ValueError("limit must be greater than 0")

    output = run_git(
        "log",
        f"-{limit}",
        "--format=%H%x09%an%x09%ad%x09%s",
        "--date=short",
    )

    return parse_commits(output)


def log_path(path: str, limit: int = 10) -> list[dict]:
    if limit < 1:
        raise ValueError("limit must be greater than 0")

    output = run_git(
        "log",
        f"-{limit}",
        "--format=%H%x09%ad%x09%s",
        "--date=short",
        "--",
        path,
    )

    return parse_commits(output)


def inspect_path(path: str) -> dict:
    return {
        "path": path,
        "history": log_path(path, 5),
        "diff": diff(path),
        "status": status(),
    }


def show(commit: str) -> dict:
    metadata = run_git(
        "show",
        "--no-patch",
        "--format=%H%n%an%n%ad%n%s",
        "--date=short",
        commit,
    ).splitlines()

    files = run_git(
        "show",
        "--stat",
        "--oneline",
        "--format=",
        commit,
    ).splitlines()

    return {
        "commit": metadata[0] if len(metadata) > 0 else "",
        "author": metadata[1] if len(metadata) > 1 else "",
        "date": metadata[2] if len(metadata) > 2 else "",
        "subject": metadata[3] if len(metadata) > 3 else "",
        "files": files,
    }


def conflicts() -> list[str]:
    return run_git(
        "diff",
        "--name-only",
        "--diff-filter=U",
    ).splitlines()


def is_rebasing() -> bool:
    for rebase_path in ("rebase-merge", "rebase-apply"):
        try:
            path = run_git(
                "rev-parse",
                "--git-path",
                rebase_path,
            )

            result = subprocess.run(
                ["test", "-d", path],
                check=False,
            )

            if result.returncode == 0:
                return True

        except RuntimeError:
            pass

    return False


# ---------------------------------------------------------------------------
# Compound workflows
# ---------------------------------------------------------------------------


def check() -> dict:
    return {
        "branch": branch(),
        "status": status(),
        "changed": changed(),
        "diff_summary": diff_summary(),
        "conflicts": conflicts(),
    }


def context(path: str) -> dict:
    return {
        "path": path,
        "status": status(),
        "history": log_path(path, 5),
        "diff": diff(path),
    }


def review() -> dict:
    return {
        "branch": branch(),
        "status": status(),
        "changed": changed(),
        "diff_summary": diff_summary(),
        "diff": diff(),
        "conflicts": conflicts(),
    }


def review_branch(base: str) -> dict:
    merge_base = run_git(
        "merge-base",
        base,
        "HEAD",
    )

    commits = parse_commits(
        run_git(
            "log",
            "--format=%H\t%ad\t%s",
            "--date=short",
            f"{merge_base}..HEAD",
        )
    )

    changed_files = parse_numstat(
        run_git(
            "diff",
            "--numstat",
            f"{merge_base}..HEAD",
        )
    )

    summary = run_git(
        "diff",
        "--stat",
        f"{merge_base}..HEAD",
    )

    full_diff = run_git(
        "diff",
        f"{merge_base}..HEAD",
    )

    return {
        "base": base,
        "merge_base": merge_base,
        "commits": commits,
        "changed": changed_files,
        "diff_summary": summary,
        "diff": full_diff,
        "branch": branch(),
    }


def commit_context() -> dict:
    current_status = status()

    return {
        "branch": branch(),
        "status": current_status,
        "recent_commits": recent(10),
        "changed": changed(),
        "diff_summary": diff_summary(),
        "conflicts": conflicts(),
        "ready_to_commit": bool(current_status["staged"]),
        "unstaged_work": bool(
            current_status["unstaged"]
            or current_status["untracked"]
        ),
    }

def fix_context() -> dict:
    current_status = status()
    current_branch = branch()

    result = {
        "branch": current_branch,
        "status": current_status,
        "changed": changed(),
        "diff_summary": diff_summary(),
        "diff": diff(),
        "conflicts": conflicts(),
    }

    result["has_conflicts"] = bool(result["conflicts"])

    return result


def merge_context() -> dict:
    current_status = status()
    current_branch = branch()
    current_conflicts = conflicts()

    return {
        "branch": current_branch,
        "status": current_status,
        "conflicts": current_conflicts,
        "changed": changed(),
        "diff_summary": diff_summary(),
        "diff": diff(),
        "has_conflicts": bool(current_conflicts),
    }


def rebase_context() -> dict:
    current_status = status()
    current_branch = branch()
    current_conflicts = conflicts()

    return {
        "branch": current_branch,
        "status": current_status,
        "conflicts": current_conflicts,
        "changed": changed(),
        "diff_summary": diff_summary(),
        "diff": diff(),
        "rebasing": is_rebasing(),
    }

def ship_context() -> dict:
    current_branch = branch()
    current_status = status()
    current_conflicts = conflicts()

    clean = not (
        current_status["staged"]
        or current_status["unstaged"]
        or current_status["untracked"]
    )

    return {
        "branch": current_branch,
        "status": current_status,
        "changed": changed(),
        "diff_summary": diff_summary(),
        "conflicts": current_conflicts,
        "recent_commits": recent(10),
        "clean": clean,
        "ready_to_ship": (
            clean
            and not current_conflicts
            and bool(current_branch["branch"])
        ),
    }


def branch_context() -> dict:
    current_branch = branch()

    return {
        "branch": current_branch,
        "status": status(),
        "recent_commits": recent(10),
        "changed": changed(),
        "conflicts": conflicts(),
    }


def verify_context() -> dict:
    current_status = status()
    current_conflicts = conflicts()

    has_changes = bool(
        current_status["staged"]
        or current_status["unstaged"]
        or current_status["untracked"]
    )

    has_conflicts = bool(current_conflicts)

    return {
        "branch": branch(),
        "status": current_status,
        "changed": changed(),
        "diff_summary": diff_summary(),
        "conflicts": current_conflicts,
        "has_conflicts": has_conflicts,
        "has_changes": has_changes,
        "clean": not has_changes and not has_conflicts,
    }


# ---------------------------------------------------------------------------
# Stash
# ---------------------------------------------------------------------------


def stash_list() -> list[dict]:
    output = run_git(
        "stash",
        "list",
        "--format=%gd\t%H\t%s",
    )

    result = []

    for line in output.splitlines():
        parts = line.split("\t", 2)

        if len(parts) != 3:
            continue

        reference, commit, message = parts

        result.append(
            {
                "stash": reference,
                "commit": commit,
                "message": message,
            }
        )

    return result


def stash_context() -> dict:
    return {
        "branch": branch(),
        "status": status(),
        "changed": changed(),
        "diff_summary": diff_summary(),
        "stashes": stash_list(),
        "conflicts": conflicts(),
    }


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


def tags(limit: int = 20) -> list[dict]:
    if limit < 1:
        raise ValueError("limit must be greater than 0")

    output = run_git(
        "for-each-ref",
        "--sort=-creatordate",
        f"--count={limit}",
        "--format=%(refname:short)\t%(objectname)\t%(creatordate:short)\t%(subject)",
        "refs/tags",
    )

    result = []

    for line in output.splitlines():
        parts = line.split("\t", 3)

        if len(parts) != 4:
            continue

        name, commit, date, subject = parts

        result.append(
            {
                "tag": name,
                "commit": commit,
                "date": date,
                "subject": subject,
            }
        )

    return result


def tag_context() -> dict:
    current_branch = branch()

    try:
        current = run_git(
            "describe",
            "--tags",
            "--always",
            "--dirty",
        )
    except RuntimeError:
        current = ""

    return {
        "branch": current_branch,
        "current": current,
        "tags": tags(20),
        "recent_commits": recent(10),
    }


# ---------------------------------------------------------------------------
# Remotes / PR context
# ---------------------------------------------------------------------------


def remotes() -> list[dict]:
    output = run_git("remote", "-v")

    result = []
    seen = set()

    for line in output.splitlines():
        parts = line.split()

        if len(parts) < 3:
            continue

        name, url, kind = parts[:3]

        key = (name, kind)

        if key in seen:
            continue

        seen.add(key)

        result.append(
            {
                "name": name,
                "url": url,
                "type": kind.rstrip(")"),
            }
        )

    return result


def remote_context() -> dict:
    return {
        "branch": branch(),
        "remotes": remotes(),
        "status": status(),
        "recent_commits": recent(10),
    }


def pr_context() -> dict:
    branch_info = branch()

    result = {
        "branch": branch_info,
        "status": status(),
        "recent_commits": recent(10),
        "changed": changed(),
        "diff_summary": diff_summary(),
        "conflicts": conflicts(),
    }

    upstream = branch_info["upstream"]

    if not upstream:
        result["upstream"] = ""
        result["merge_base"] = ""
        result["commits"] = []
        result["branch_diff"] = []
        return result

    result["upstream"] = upstream

    try:
        merge_base = run_git(
            "merge-base",
            "HEAD",
            upstream,
        )

        result["merge_base"] = merge_base

        result["commits"] = parse_commits(
            run_git(
                "log",
                "--format=%H\t%ad\t%s",
                "--date=short",
                f"{merge_base}..HEAD",
            )
        )

        result["branch_diff"] = run_git(
            "diff",
            "--stat",
            f"{merge_base}..HEAD",
        ).splitlines()

    except RuntimeError:
        result["merge_base"] = ""
        result["commits"] = []
        result["branch_diff"] = []

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compact, agent-oriented Git interface."
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    subparsers.add_parser("status")
    subparsers.add_parser("branch")
    subparsers.add_parser("diff-summary")
    subparsers.add_parser("changed")
    subparsers.add_parser("check")
    subparsers.add_parser("review")
    subparsers.add_parser("conflicts")

    diff_parser = subparsers.add_parser("diff")
    diff_parser.add_argument("--path")

    recent_parser = subparsers.add_parser("recent")
    recent_parser.add_argument(
        "--limit",
        type=int,
        default=10,
    )

    log_parser = subparsers.add_parser("log")
    log_parser.add_argument("path")
    log_parser.add_argument(
        "--limit",
        type=int,
        default=10,
    )

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("path")

    context_parser = subparsers.add_parser("context")
    context_parser.add_argument("path")

    show_parser = subparsers.add_parser("show")
    show_parser.add_argument("commit")

    review_branch_parser = subparsers.add_parser("review-branch")
    review_branch_parser.add_argument("base")

    subparsers.add_parser("commit-context")
    subparsers.add_parser("fix-context")
    subparsers.add_parser("merge-context")
    subparsers.add_parser("rebase-context")
    subparsers.add_parser("ship-context")
    subparsers.add_parser("branch-context")
    subparsers.add_parser("verify-context")
    subparsers.add_parser("stash")
    subparsers.add_parser("tag")
    subparsers.add_parser("remote")
    subparsers.add_parser("pr-context")

    args = parser.parse_args()

    try:
        if args.command == "status":
            output = status()

        elif args.command == "branch":
            output = branch()

        elif args.command == "diff":
            output = diff(args.path)

        elif args.command == "diff-summary":
            output = diff_summary()

        elif args.command == "changed":
            output = changed()

        elif args.command == "check":
            output = check()

        elif args.command == "review":
            output = review()

        elif args.command == "review-branch":
            output = review_branch(args.base)

        elif args.command == "recent":
            output = recent(args.limit)

        elif args.command == "log":
            output = log_path(args.path, args.limit)

        elif args.command == "inspect":
            output = inspect_path(args.path)

        elif args.command == "context":
            output = context(args.path)

        elif args.command == "show":
            output = show(args.commit)

        elif args.command == "conflicts":
            output = conflicts()

        elif args.command == "commit-context":
            output = commit_context()

        elif args.command == "fix-context":
            output = fix_context()

        elif args.command == "merge-context":
            output = merge_context()

        elif args.command == "rebase-context":
            output = rebase_context()

        elif args.command == "ship-context":
            output = ship_context()

        elif args.command == "branch-context":
            output = branch_context()

        elif args.command == "verify-context":
            output = verify_context()

        elif args.command == "stash":
            output = stash_context()

        elif args.command == "tag":
            output = tag_context()

        elif args.command == "remote":
            output = remote_context()

        elif args.command == "pr-context":
            output = pr_context()

        else:
            raise RuntimeError(
                f"unknown command: {args.command}"
            )

    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    print(
        json.dumps(
            output,
            separators=(",", ":"),
        )
    )


if __name__ == "__main__":
    main()