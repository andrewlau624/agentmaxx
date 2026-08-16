#!/usr/bin/env python3

import argparse
import json
import subprocess
from pathlib import Path


DEFINITION_PREFIXES = (
    "class ",
    "def ",
    "async def ",
    "function ",
    "func ",
    "interface ",
    "type ",
    "struct ",
    "enum ",
)


def file_score(path: str) -> int:
    name = Path(path).name.lower()
    suffix = Path(path).suffix.lower()

    score = 0

    if suffix in {
        ".py", ".ts", ".tsx", ".js", ".jsx",
        ".go", ".rs", ".java", ".kt", ".swift",
        ".c", ".h", ".cpp", ".hpp",
    }:
        score += 30

    if "/test/" in path.lower() or "/tests/" in path.lower():
        score += 10

    if name in {"readme.md", "changelog.md", "license"}:
        score -= 30

    if suffix in {".md", ".txt", ".rst"}:
        score -= 20

    if name in {"package-lock.json", "yarn.lock", "pnpm-lock.yaml"}:
        score -= 40

    return score


def score_match(query: str, match: dict) -> int:
    query_lower = query.lower()
    file_lower = match["file"].lower()
    text_lower = match["text"].strip().lower()

    score = file_score(match["file"])

    if query_lower == Path(file_lower).stem:
        score += 100

    if query_lower in Path(file_lower).name:
        score += 50

    if query_lower in text_lower:
        score += 20

    if text_lower.startswith(DEFINITION_PREFIXES):
        score += 50

    return score


def search(
    query: str,
    path: str = ".",
    file_type: str | None = None,
    max_results: int = 20,
    max_output_chars: int = 8000,
) -> dict:
    if max_results < 1:
        raise ValueError("max-results must be greater than 0")

    if max_output_chars < 1:
        raise ValueError("max-output-chars must be greater than 0")

    command = [
        "rg",
        "--json",
        "--smart-case",
    ]

    if file_type:
        command.extend(["--type", file_type])

    command.extend([query, path])

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        raise RuntimeError(
            "ripgrep (rg) is required. Run `make install`."
        )

    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip())

    matches = []

    for line in result.stdout.splitlines():
        if not line:
            continue

        entry = json.loads(line)

        if entry["type"] != "match":
            continue

        data = entry["data"]
        submatches = data["submatches"]

        match = {
            "file": data["path"]["text"],
            "line": data["line_number"],
            "column": (
                submatches[0]["start"] + 1
                if submatches
                else None
            ),
            "text": data["lines"]["text"].rstrip("\n"),
        }

        match["_score"] = score_match(query, match)
        matches.append(match)

    matches.sort(
        key=lambda match: (
            -match["_score"],
            match["file"],
            match["line"],
        )
    )

    selected = []
    output_chars = 0

    for match in matches:
        match.pop("_score")

        encoded = json.dumps(
            match,
            separators=(",", ":"),
        )

        if selected and output_chars + len(encoded) > max_output_chars:
            break

        selected.append(match)
        output_chars += len(encoded)

        if len(selected) >= max_results:
            break

    return {
        "query": query,
        "results": selected,
        "truncated": len(selected) < len(matches),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Search a repository and return compact "
            "ranked results."
        )
    )

    parser.add_argument("query")
    parser.add_argument("--path", default=".")
    parser.add_argument("--type", dest="file_type")
    parser.add_argument("--max-results", type=int, default=20)
    parser.add_argument("--max-output-chars", type=int, default=8000)

    args = parser.parse_args()

    try:
        output = search(
            query=args.query,
            path=args.path,
            file_type=args.file_type,
            max_results=args.max_results,
            max_output_chars=args.max_output_chars,
        )
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    print(json.dumps(output, separators=(",", ":")))


if __name__ == "__main__":
    main()