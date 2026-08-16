#!/usr/bin/env python3

"""Locate code and return the surrounding source in a single call.

The dominant agent pattern is search, then read each hit's region. Done
with separate tools that is one round trip per hit, and every round trip
re-sends the whole accumulated context. This collapses the sequence into
one call.
"""

import argparse
import importlib.util
import json
from pathlib import Path


TOOLS_ROOT = Path(__file__).resolve().parent.parent


def _load_tool(directory: str, module: str):
    """Load a sibling tool module by path.

    Tool directories are hyphenated, so they are not importable as
    packages. This mirrors how the test suites load their subjects.
    """
    path = TOOLS_ROOT / directory / f"{module}.py"
    spec = importlib.util.spec_from_file_location(module, path)

    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load tool module: {path}")

    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)

    return loaded


better_grep = _load_tool("better-grep", "better_grep")
better_cat = _load_tool("better-cat", "better_cat")


def collect(
    query: str | list[str],
    path: str = ".",
    file_type: str | None = None,
    max_hits: int = 5,
    context_lines: int = 20,
    max_output_chars: int = 8000,
) -> dict:
    """Search, then return a bounded window around each ranked hit."""
    if max_hits < 1:
        raise ValueError("max-hits must be greater than 0")

    if context_lines < 0:
        raise ValueError("context-lines must be 0 or greater")

    if max_output_chars < 1:
        raise ValueError("max-output-chars must be greater than 0")

    found = better_grep.search(
        query=query,
        path=path,
        file_type=file_type,
        max_results=max_hits,
        max_output_chars=max_output_chars,
    )

    results = found["results"]
    regions = []
    remaining = max_output_chars

    for index, match in enumerate(results):
        budget = max(1, remaining // (len(results) - index))
        start = max(1, match["line"] - context_lines)
        end = match["line"] + context_lines

        window = better_cat.inspect(
            path=match["file"],
            start=start,
            end=end,
            max_output_chars=budget,
        )

        regions.append(
            {
                "file": match["file"],
                "match_line": match["line"],
                "start": window["start"],
                "end": window["end"],
                "total_lines": window["total_lines"],
                "content": window["content"],
            }
        )

        remaining = max(1, remaining - len(window["content"]))

    return {
        "queries": found["queries"],
        "regions": regions,
        "truncated": found["truncated"] or remaining <= 1,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Find code and return its surrounding source in one call. "
            "Accepts multiple patterns."
        )
    )

    parser.add_argument("query", nargs="+")
    parser.add_argument("--path", default=".")
    parser.add_argument("--type", dest="file_type")
    parser.add_argument("--max-hits", type=int, default=5)
    parser.add_argument("--context-lines", type=int, default=20)
    parser.add_argument("--max-output-chars", type=int, default=8000)

    args = parser.parse_args()

    try:
        output = collect(
            query=args.query,
            path=args.path,
            file_type=args.file_type,
            max_hits=args.max_hits,
            context_lines=args.context_lines,
            max_output_chars=args.max_output_chars,
        )
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))

    print(json.dumps(output, separators=(",", ":")))


if __name__ == "__main__":
    main()
