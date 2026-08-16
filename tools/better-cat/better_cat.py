#!/usr/bin/env python3

import argparse
import json
import re
from pathlib import Path


RANGE_PATTERN = re.compile(r"^(\d+)(?:-(\d+)?)?$")


def parse_spec(spec: str) -> tuple[str, int, int | None]:
    """Parse `path`, `path:12-40`, `path:12-`, or `path:12`.

    A trailing `:range` is only treated as a range when it actually looks
    like one, so paths containing colons still resolve.
    """
    if ":" not in spec:
        return spec, 1, None

    path, _, candidate = spec.rpartition(":")
    match = RANGE_PATTERN.match(candidate)

    if not path or not match:
        return spec, 1, None

    start = int(match.group(1))
    end = int(match.group(2)) if match.group(2) else None

    return path, start, end


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


def inspect_many(
    specs: list[str],
    max_output_chars: int = 8000,
) -> dict:
    """Inspect several file ranges in one call.

    The output budget is shared across specs so that a batch costs the same
    as a single read. Unused budget rolls forward to later specs.
    """
    if not specs:
        raise ValueError("at least one file spec is required")

    if max_output_chars < 1:
        raise ValueError("max-output-chars must be greater than 0")

    files = []
    remaining = max_output_chars

    for index, spec in enumerate(specs):
        path, start, end = parse_spec(spec)
        budget = max(1, remaining // (len(specs) - index))

        entry = inspect(
            path=path,
            start=start,
            end=end,
            max_output_chars=budget,
        )

        files.append(entry)
        remaining = max(1, remaining - len(entry["content"]))

    return {
        "files": files,
        "truncated": any(entry["truncated"] for entry in files),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Inspect bounded file ranges. Accepts multiple specs in one "
            "call: path, path:12-40, path:12- or path:12."
        )
    )
    parser.add_argument("specs", nargs="+")
    parser.add_argument("--max-output-chars", type=int, default=8000)

    args = parser.parse_args()

    try:
        output = inspect_many(
            specs=args.specs,
            max_output_chars=args.max_output_chars,
        )
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))

    print(json.dumps(output, separators=(",", ":")))


if __name__ == "__main__":
    main()