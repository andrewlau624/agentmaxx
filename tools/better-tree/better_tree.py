#!/usr/bin/env python3

import argparse
import json
from pathlib import Path


DEFAULT_IGNORES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    ".turbo",
}


def tree(
    root: str = ".",
    max_depth: int = 3,
    max_entries: int = 500,
    show_hidden: bool = False,
    include_ignored: bool = False,
) -> dict:
    """
    Return a compact, bounded directory tree.

    The output is intentionally structured for agents:
      - paths are relative to root
      - files include sizes
      - common generated/dependency directories are ignored
      - traversal is bounded by depth and entry count
    """

    if max_depth < 0:
        raise ValueError("max_depth must be >= 0")

    if max_entries < 1:
        raise ValueError("max_entries must be greater than 0")

    base = Path(root).resolve()

    if not base.exists():
        raise RuntimeError(f"path does not exist: {root}")

    if not base.is_dir():
        raise RuntimeError(f"path is not a directory: {root}")

    entries = []
    truncated = False

    def should_skip(path: Path) -> bool:
        if not show_hidden and path.name.startswith("."):
            return True

        if not include_ignored and path.name in DEFAULT_IGNORES:
            return True

        return False

    def walk(path: Path, depth: int) -> None:
        nonlocal truncated

        if truncated:
            return

        if depth > max_depth:
            return

        try:
            children = list(path.iterdir())
        except OSError:
            return

        children.sort(
            key=lambda item: (
                not item.is_dir(),
                item.name.lower(),
            )
        )

        for child in children:
            if len(entries) >= max_entries:
                truncated = True
                return

            if should_skip(child):
                continue

            try:
                relative_path = child.relative_to(base)
            except ValueError:
                continue

            is_directory = child.is_dir()

            entry = {
                "path": str(relative_path),
                "name": child.name,
                "type": "directory" if is_directory else "file",
            }

            if not is_directory:
                try:
                    entry["size"] = child.stat().st_size
                except OSError:
                    entry["size"] = None

            entries.append(entry)

            if is_directory and depth < max_depth:
                walk(child, depth + 1)

            if truncated:
                return

    walk(base, 0)

    return {
        "root": str(base),
        "max_depth": max_depth,
        "count": len(entries),
        "truncated": truncated,
        "entries": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compact, bounded directory tree."
    )

    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to inspect.",
    )

    parser.add_argument(
        "--depth",
        type=int,
        default=3,
        help="Maximum traversal depth.",
    )

    parser.add_argument(
        "--max-entries",
        type=int,
        default=500,
        help="Maximum number of entries to return.",
    )

    parser.add_argument(
        "--hidden",
        action="store_true",
        help="Include hidden files and directories.",
    )

    parser.add_argument(
        "--include-ignored",
        action="store_true",
        help="Include common generated/dependency directories.",
    )

    args = parser.parse_args()

    try:
        output = tree(
            root=args.path,
            max_depth=args.depth,
            max_entries=args.max_entries,
            show_hidden=args.hidden,
            include_ignored=args.include_ignored,
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