#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


def inspect(
    path: str,
    start: int = 1,
    end: int | None = None,
    max_output_chars: int = 8000,
) -> dict:
    if start < 1:
        raise ValueError("start must be greater than 0")

    if end is not None and end < start:
        raise ValueError("end must be greater than or equal to start")

    if max_output_chars < 1:
        raise ValueError("max-output-chars must be greater than 0")

    file_path = Path(path)

    if not file_path.is_file():
        raise FileNotFoundError(path)

    lines = file_path.read_text().splitlines()

    requested_end = end if end is not None else len(lines)
    selected = []

    for line_number in range(start, min(requested_end, len(lines)) + 1):
        text = lines[line_number - 1]
        entry = f"{line_number}: {text}"

        if selected:
            projected = len("\n".join(selected)) + 1 + len(entry)
        else:
            projected = len(entry)

        if projected > max_output_chars:
            break

        selected.append(entry)

    actual_end = (
        start + len(selected) - 1
        if selected
        else start - 1
    )

    return {
        "file": str(file_path),
        "start": start,
        "end": actual_end,
        "total_lines": len(lines),
        "content": "\n".join(selected),
        "truncated": actual_end < requested_end,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect a bounded range of a file."
    )
    parser.add_argument("path")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int)
    parser.add_argument("--max-output-chars", type=int, default=8000)

    args = parser.parse_args()

    try:
        output = inspect(
            path=args.path,
            start=args.start,
            end=args.end,
            max_output_chars=args.max_output_chars,
        )
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))

    print(json.dumps(output, separators=(",", ":")))


if __name__ == "__main__":
    main()