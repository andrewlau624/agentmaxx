#!/usr/bin/env python3
"""Better-diff: Ranked diff generator with bounded output.

Shows what changed in a file or directory with minimal context.

Usage:
    python3 better_diff.py "src/auth" --since "2 days ago"
    python3 better_diff.py "service.py" --commits 3
"""

import argparse
import json
import re
import subprocess
from typing import Any


def get_diffs(
    path: str = ".",
    since: str = None,
    commits: int = None,
    max_output: int = 5000,
) -> dict[str, Any]:
    """Get diffs for a file or directory.
    
    Args:
        path: File or directory to diff
        since: Time range (e.g., "2 days ago")
        commits: Number of recent commits
        max_output: Maximum diff size in characters
    
    Returns:
        Structured diff output
    """
    
    cmd = ["git", "log", "--no-merges", "-p"]
    
    if commits:
        cmd.extend([f"-{commits}"])
    elif since:
        cmd.extend([f"--since={since}"])
    else:
        cmd.append("-1")  # Default: last commit
    
    cmd.append("--")
    cmd.append(path)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=".",
        )
        
        if result.returncode != 0:
            return {"error": "git command failed", "path": path}
        
        diffs = result.stdout[:max_output]
        
        # Parse diffs into chunks
        chunks = re.split(r"^diff --git", diffs, flags=re.MULTILINE)
        
        return {
            "path": path,
            "diff_count": len(chunks),
            "diffs": chunks[:5],  # Top 5 diffs
            "total_chars": len(diffs),
            "truncated": len(result.stdout) > max_output,
        }
    except Exception as e:
        return {"error": str(e), "path": path}


def diff(
    path: str = ".",
    since: str = None,
    commits: int = None,
    max_output: int = 5000,
) -> dict[str, Any]:
    """Get diffs for a path.
    
    Args:
        path: File or directory
        since: Time range
        commits: Number of commits
        max_output: Max output size
    
    Returns:
        Diff structure
    """
    return get_diffs(path, since, commits, max_output)


def main():
    parser = argparse.ArgumentParser(
        description="Generate ranked diffs with bounded output"
    )
    parser.add_argument("path", default=".", nargs="?", help="File or directory")
    parser.add_argument(
        "--since",
        help="Time range (e.g., '2 days ago')",
    )
    parser.add_argument(
        "--commits",
        type=int,
        help="Number of recent commits",
    )
    parser.add_argument(
        "--max-output",
        type=int,
        default=5000,
        help="Maximum output size",
    )
    
    args = parser.parse_args()
    
    result = diff(
        path=args.path,
        since=args.since,
        commits=args.commits,
        max_output=args.max_output,
    )
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
