#!/usr/bin/env python3

import argparse
import json
import os
from pathlib import Path


def find(
    path: str = ".",
    name: str | None = None,
    file_type: str | None = None,
    max_results: int = 100,
) -> dict:
    if max_results < 1:
        raise ValueError("max-results must be greater than 0")

    root = Path(path)

    if not root.exists():
        raise FileNotFoundError(path)

    results = []

    def add_result(candidate: Path) -> dict | None:
        if name and not candidate.match(name):
            return None

        results.append(str(candidate))

        if len(results) >= max_results:
            return {
                "path": path,
                "results": results,
                "truncated": True,
            }

        return None

    for current_root, dirs, files in os.walk(root):
        dirs[:] = sorted(
            d for d in dirs
            if d not in {
                ".git",
                ".venv",
                "node_modules",
                "__pycache__",
            }
        )

        if file_type == "dir":
            for dirname in dirs:
                result = add_result(Path(current_root) / dirname)

                if result:
                    return result

            continue

        for filename in sorted(files):
            result = add_result(Path(current_root) / filename)

            if result:
                return result

    return {
        "path": path,
        "results": results,
        "truncated": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Find repository files with bounded output."
    )
    parser.add_argument("path", nargs="?", default=".")
    parser.add_argument("--name")
    parser.add_argument("--type", choices=("file", "dir"))
    parser.add_argument("--max-results", type=int, default=100)

    args = parser.parse_args()

    try:
        output = find(
            path=args.path,
            name=args.name,
            file_type=args.type,
            max_results=args.max_results,
        )
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))

    print(json.dumps(output, separators=(",", ":")))


if __name__ == "__main__":
    main()
