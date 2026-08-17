#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path


def apply_edit(
    content: str,
    old: str,
    new: str,
    replace_all: bool = False,
) -> tuple[str, int]:
    """Apply one exact-string replacement to `content`.

    `old` must be unique in `content` unless replace_all is set — the
    same safety rule a single-file edit tool enforces.
    """
    if old == new:
        raise ValueError("new text must differ from old text")

    count = content.count(old)

    if count == 0:
        raise ValueError(f"text not found: {old!r}")

    if count > 1 and not replace_all:
        raise ValueError(
            f"text is not unique ({count} occurrences): {old!r}"
        )

    occurrences = count if replace_all else 1
    updated = (
        content.replace(old, new)
        if replace_all
        else content.replace(old, new, 1)
    )

    return updated, occurrences


def edit_many(edits: list[dict]) -> dict:
    """Apply a batch of exact-string edits across one or more files.

    Every edit validates against its file's current (or already-staged)
    content before anything is written. If any edit fails, no file in
    the batch is written. Edits to the same path apply in the given
    order, each against the previous edit's result.
    """
    if not edits:
        raise ValueError("at least one edit is required")

    pending: dict[str, str] = {}
    results = []

    for index, edit in enumerate(edits):
        path = edit.get("path")
        old = edit.get("old")
        new = edit.get("new")
        replace_all = bool(edit.get("replace_all", False))

        if not path or old is None or new is None:
            raise ValueError(
                f"edit {index}: 'path', 'old', and 'new' are required"
            )

        if path in pending:
            content = pending[path]
        else:
            file_path = Path(path)

            if not file_path.is_file():
                raise FileNotFoundError(path)

            content = file_path.read_text()

        try:
            updated, occurrences = apply_edit(content, old, new, replace_all)
        except ValueError as exc:
            raise ValueError(f"edit {index} ({path}): {exc}") from exc

        line = content[: content.index(old)].count("\n") + 1
        pending[path] = updated
        results.append({"path": path, "line": line, "occurrences": occurrences})

    for path, content in pending.items():
        Path(path).write_text(content)

    return {"edits": results, "files_changed": len(pending)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Apply a batch of exact-string edits across one or more "
            "files in one call. All edits validate before any file is "
            "written; if any edit fails, nothing is written."
        )
    )
    parser.add_argument(
        "edits",
        nargs="?",
        help=(
            "JSON array of {path, old, new, replace_all?}. Reads from "
            "stdin if omitted."
        ),
    )

    args = parser.parse_args()
    raw = args.edits if args.edits is not None else sys.stdin.read()

    try:
        edits = json.loads(raw)
    except json.JSONDecodeError as exc:
        parser.error(f"invalid JSON: {exc}")

    try:
        output = edit_many(edits)
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))

    print(json.dumps(output, separators=(",", ":")))


if __name__ == "__main__":
    main()
