#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(frozen=True)
class BlameRecord:
    line: int
    commit: str
    author: str
    date: str
    summary: str
    content: str

    def to_dict(self) -> dict[str, object]:
        return {
            "line": self.line,
            "commit": self.commit,
            "author": self.author,
            "date": self.date,
            "summary": self.summary,
            "content": self.content,
        }


def run_git(
    args: Sequence[str],
    cwd: str | os.PathLike[str] | None = None,
) -> str:
    """Run git and return stdout.

    Raises:
        RuntimeError: If git exits unsuccessfully.
    """
    command = ["git", *args]

    result = subprocess.run(
        command,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )

    if result.returncode != 0:
        message = result.stderr.strip()

        if not message:
            message = "git command failed"

        raise RuntimeError(message)

    return result.stdout


def _parse_porcelain_blame(output: str) -> list[BlameRecord]:
    """Parse `git blame --porcelain` output."""
    records: list[BlameRecord] = []

    lines = output.splitlines()
    index = 0
    line_number = 0

    while index < len(lines):
        header = lines[index]

        parts = header.split()

        if len(parts) < 3:
            index += 1
            continue

        commit = parts[0]

        try:
            final_line = int(parts[2])
        except ValueError:
            index += 1
            continue

        author = ""
        date = ""
        summary = ""
        content = ""

        index += 1

        while index < len(lines):
            metadata = lines[index]

            if metadata.startswith("\t"):
                content = metadata[1:]
                index += 1
                break

            if metadata.startswith("author "):
                author = metadata[7:]

            elif metadata.startswith("author-time "):
                try:
                    timestamp = int(metadata[12:])
                    date = str(timestamp)
                except ValueError:
                    date = metadata[12:]

            elif metadata.startswith("summary "):
                summary = metadata[8:]

            index += 1

        line_number += 1

        records.append(
            BlameRecord(
                line=final_line if final_line else line_number,
                commit=commit,
                author=author,
                date=date,
                summary=summary,
                content=content,
            )
        )

    return records


def blame(
    path: str | os.PathLike[str],
    *,
    revision: str | None = None,
    start_line: int | None = None,
    end_line: int | None = None,
    max_lines: int | None = None,
    cwd: str | os.PathLike[str] | None = None,
) -> list[dict[str, object]]:
    """Return compact blame information for a file.

    Args:
        path: File to inspect.
        revision: Optional git revision.
        start_line: First line to include, 1-based.
        end_line: Last line to include, 1-based.
        max_lines: Maximum number of records to return.
        cwd: Repository working directory.

    Returns:
        A list of compact blame dictionaries.
    """
    path = str(path)

    if start_line is not None and start_line < 1:
        raise ValueError("start_line must be >= 1")

    if end_line is not None and end_line < 1:
        raise ValueError("end_line must be >= 1")

    if (
        start_line is not None
        and end_line is not None
        and start_line > end_line
    ):
        raise ValueError("start_line must be <= end_line")

    if max_lines is not None and max_lines < 1:
        raise ValueError("max_lines must be >= 1")

    args: list[str] = [
        "blame",
        "--porcelain",
    ]

    if start_line is not None or end_line is not None:
        first = start_line or 1
        last = end_line or first

        args.extend(
            [
                "-L",
                f"{first},{last}",
            ]
        )

    if revision:
        args.append(revision)

    args.append("--")
    args.append(path)

    output = run_git(args, cwd=cwd)

    records = _parse_porcelain_blame(output)

    if max_lines is not None:
        records = records[:max_lines]

    return [record.to_dict() for record in records]


def blame_context(
    path: str | os.PathLike[str],
    line: int,
    *,
    context: int = 2,
    revision: str | None = None,
    cwd: str | os.PathLike[str] | None = None,
) -> list[dict[str, object]]:
    """Return blame records around a particular line."""
    if line < 1:
        raise ValueError("line must be >= 1")

    if context < 0:
        raise ValueError("context must be >= 0")

    start = max(1, line - context)
    end = line + context

    return blame(
        path,
        revision=revision,
        start_line=start,
        end_line=end,
        cwd=cwd,
    )


def commit_context(
    commit: str,
    *,
    cwd: str | os.PathLike[str] | None = None,
) -> dict[str, object]:
    """Return useful information about a commit."""
    output = run_git(
        [
            "show",
            "--no-renames",
            "--format=%H%n%an%n%ae%n%aI%n%s",
            "--stat",
            commit,
        ],
        cwd=cwd,
    )

    lines = output.splitlines()

    values = lines[:5]

    while len(values) < 5:
        values.append("")

    return {
        "commit": values[0],
        "author": values[1],
        "email": values[2],
        "date": values[3],
        "summary": values[4],
        "stat": "\n".join(lines[5:]),
    }


def format_records(records: list[dict[str, object]]) -> str:
    """Format blame records for terminal output."""
    if not records:
        return ""

    output: list[str] = []

    for record in records:
        line = record.get("line", "")
        commit = str(record.get("commit", ""))
        author = str(record.get("author", ""))
        date = str(record.get("date", ""))
        content = str(record.get("content", ""))

        short_commit = commit[:10]

        output.append(
            f"{line:>6} "
            f"{short_commit:<10} "
            f"{author:<24} "
            f"{date:<12} "
            f"{content}"
        )

    return "\n".join(output)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compact, useful git blame information.",
    )

    parser.add_argument(
        "path",
        help="File to blame.",
    )

    parser.add_argument(
        "-L",
        "--lines",
        dest="line_range",
        help="Line range, for example 10,20.",
    )

    parser.add_argument(
        "-r",
        "--revision",
        help="Git revision.",
    )

    parser.add_argument(
        "--context",
        type=int,
        help="Show context around a line.",
    )

    parser.add_argument(
        "--max-lines",
        type=int,
        help="Limit the number of records.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    start_line: int | None = None
    end_line: int | None = None

    if args.line_range:
        try:
            start_text, end_text = args.line_range.split(",", 1)

            start_line = int(start_text)
            end_line = int(end_text)

        except ValueError:
            parser.error(
                "--lines must be in the form START,END"
            )

    try:
        if args.context is not None:
            if start_line is None:
                parser.error(
                    "--context requires --lines"
                )

            records = blame_context(
                args.path,
                start_line,
                context=args.context,
                revision=args.revision,
            )
        else:
            records = blame(
                args.path,
                revision=args.revision,
                start_line=start_line,
                end_line=end_line,
                max_lines=args.max_lines,
            )

    except (RuntimeError, ValueError) as exc:
        print(f"better-blame: {exc}", file=sys.stderr)
        return 1

    formatted = format_records(records)

    if formatted:
        print(formatted)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())