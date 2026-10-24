#!/usr/bin/env python3
"""Collect everything one reviewer said on a repo's PRs, with the code each comment was about.

    python3 scrape.py OWNER/REPO USER [--prs 150] [--out reviews.jsonl]

Finds PRs the user reviewed or commented on (gh search, newest first), then for
each PR pulls, with pagination: inline review comments (with the diff hunk they
point at), review summaries (APPROVED / CHANGES_REQUESTED bodies), and
conversation comments. An inline comment whose line later changed is marked
"addressed": GitHub clears a comment's `line` when the code under it changes,
which is the closest cheap signal that the author acted on it.

Prints counts per kind; writes one JSON object per comment.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor


def gh(*args: str) -> list | dict:
    out = subprocess.run(["gh", *args], capture_output=True, text=True)
    if out.returncode:
        print(f"gh {' '.join(args[:3])}: {out.stderr.strip()[:200]}", file=sys.stderr)
        return []
    # --paginate --slurp wraps pages in an outer list
    data = json.loads(out.stdout or "[]")
    return [x for page in data for x in page] if data and isinstance(data[0], list) else data


def find_prs(repo: str, user: str, limit: int) -> list[int]:
    seen: dict[int, str] = {}
    for flag in ("--reviewed-by", "--commenter"):
        for pr in gh("search", "prs", "--repo", repo, flag, user, "--limit", str(limit),
                     "--sort", "updated", "--json", "number,updatedAt"):
            seen.setdefault(pr["number"], pr["updatedAt"])
    return sorted(seen, key=seen.get, reverse=True)[:limit]


def pr_comments(repo: str, user: str, n: int) -> list[dict]:
    base = f"repos/{repo}"
    out = []
    for c in gh("api", "--paginate", "--slurp", f"{base}/pulls/{n}/comments?per_page=100"):
        if c["user"]["login"].lower() == user.lower():
            out.append({"pr": n, "kind": "inline", "path": c.get("path"), "line": c.get("line") or c.get("original_line"),
                        "body": c["body"], "hunk": (c.get("diff_hunk") or "")[-600:],
                        "addressed": c.get("line") is None and c.get("original_line") is not None,
                        "reply": c.get("in_reply_to_id") is not None, "url": c["html_url"]})
    for r in gh("api", "--paginate", "--slurp", f"{base}/pulls/{n}/reviews?per_page=100"):
        if (r.get("user") or {}).get("login", "").lower() == user.lower() and (r.get("body") or "").strip():
            out.append({"pr": n, "kind": "review", "state": r["state"], "body": r["body"], "url": r["html_url"]})
    for c in gh("api", "--paginate", "--slurp", f"{base}/issues/{n}/comments?per_page=100"):
        if c["user"]["login"].lower() == user.lower():
            out.append({"pr": n, "kind": "conversation", "body": c["body"], "url": c["html_url"]})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("repo")
    ap.add_argument("user")
    ap.add_argument("--prs", type=int, default=150, help="most recent PRs to read")
    ap.add_argument("--out", default="reviews.jsonl")
    args = ap.parse_args()
    prs = find_prs(args.repo, args.user, args.prs)
    with ThreadPoolExecutor(8) as ex:
        rows = [c for batch in ex.map(lambda n: pr_comments(args.repo, args.user, n), prs) for c in batch]
    with open(args.out, "w") as fh:
        for r in rows:
            fh.write(json.dumps(r) + "\n")
    kinds = {k: sum(r["kind"] == k for r in rows) for k in ("inline", "review", "conversation")}
    addressed = sum(r.get("addressed", False) for r in rows)
    print(f"{len(prs)} PRs, {len(rows)} comments ({kinds['inline']} inline, {addressed} of them addressed; "
          f"{kinds['review']} review summaries; {kinds['conversation']} conversation) -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
