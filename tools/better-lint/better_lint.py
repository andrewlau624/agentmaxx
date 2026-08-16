#!/usr/bin/env python3

import argparse
import json
import os
import re
import shutil
import subprocess
from pathlib import Path


DEFAULT_TIMEOUT = 30
DEFAULT_MAX_OUTPUT = 12000


def run_command(
    command: list[str],
    timeout: int = DEFAULT_TIMEOUT,
) -> tuple[int, str, bool]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )

        output = "\n".join(
            part
            for part in (
                result.stdout.strip(),
                result.stderr.strip(),
            )
            if part
        )

        return result.returncode, output, False

    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")

        output = "\n".join(
            part
            for part in (
                stdout.strip(),
                stderr.strip(),
            )
            if part
        )

        if output:
            output += "\n"

        output += "lint command timed out"

        return 124, output, True


def truncate_output(
    output: str,
    max_output: int = DEFAULT_MAX_OUTPUT,
) -> tuple[str, bool]:
    if max_output < 1:
        raise ValueError("max_output must be greater than 0")

    if len(output) <= max_output:
        return output, False

    marker = "\n... OUTPUT TRUNCATED ..."

    if max_output <= len(marker):
        return marker[:max_output], True

    return (
        output[: max_output - len(marker)] + marker,
        True,
    )


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def detect_linter() -> str:
    root = Path.cwd()

    # Python
    if (
        (root / "pyproject.toml").exists()
        or (root / "setup.py").exists()
        or (root / "setup.cfg").exists()
        or (root / "requirements.txt").exists()
    ):
        if command_exists("ruff"):
            return "ruff"

        if command_exists("flake8"):
            return "flake8"

        if command_exists("pylint"):
            return "pylint"

    # JavaScript / TypeScript
    if (root / "package.json").exists():
        if command_exists("eslint"):
            return "eslint"

        if command_exists("biome"):
            return "biome"

    # Rust
    if (root / "Cargo.toml").exists():
        if command_exists("cargo"):
            return "clippy"

    # Go
    if (root / "go.mod").exists():
        if command_exists("golangci-lint"):
            return "golangci-lint"

        if command_exists("go"):
            return "go-vet"

    return ""


def default_command(linter: str) -> list[str]:
    commands = {
        "ruff": [
            "ruff",
            "check",
            ".",
        ],
        "flake8": [
            "flake8",
            ".",
        ],
        "pylint": [
            "pylint",
            ".",
        ],
        "eslint": [
            "eslint",
            ".",
        ],
        "biome": [
            "biome",
            "check",
            ".",
        ],
        "clippy": [
            "cargo",
            "clippy",
            "--all-targets",
            "--all-features",
        ],
        "go-vet": [
            "go",
            "vet",
            "./...",
        ],
    }

    if linter not in commands:
        raise RuntimeError(
            f"unsupported linter: {linter}"
        )

    return commands[linter]


def parse_location(
    line: str,
) -> dict | None:
    patterns = [
        # file.py:10:5: message
        re.compile(
            r"^(?P<file>[^:\n]+):"
            r"(?P<line>\d+):"
            r"(?P<column>\d+):"
            r"\s*(?P<message>.*)$"
        ),
        # file.py:10: message
        re.compile(
            r"^(?P<file>[^:\n]+):"
            r"(?P<line>\d+):"
            r"\s*(?P<message>.*)$"
        ),
        # file.py(10,5): message
        re.compile(
            r"^(?P<file>[^(\n]+)"
            r"\((?P<line>\d+),"
            r"(?P<column>\d+)\):"
            r"\s*(?P<message>.*)$"
        ),
    ]

    for pattern in patterns:
        match = pattern.match(line.strip())

        if not match:
            continue

        result = match.groupdict()

        parsed = {
            "file": result["file"],
            "line": int(result["line"]),
            "message": result["message"],
        }

        if result.get("column"):
            parsed["column"] = int(
                result["column"]
            )

        return parsed

    return None


def parse_ruff(output: str) -> list[dict]:
    errors = []

    for line in output.splitlines():
        parsed = parse_location(line)

        if not parsed:
            continue

        match = re.match(
            r"([A-Z]\d+)\s+(.*)",
            parsed["message"],
        )

        if match:
            parsed["code"] = match.group(1)
            parsed["message"] = match.group(2)

        errors.append(parsed)

    return errors


def parse_flake8(output: str) -> list[dict]:
    errors = []

    for line in output.splitlines():
        parsed = parse_location(line)

        if not parsed:
            continue

        match = re.match(
            r"([A-Z]\d+)\s+(.*)",
            parsed["message"],
        )

        if match:
            parsed["code"] = match.group(1)
            parsed["message"] = match.group(2)

        errors.append(parsed)

    return errors


def parse_eslint(output: str) -> list[dict]:
    errors = []

    for line in output.splitlines():
        parsed = parse_location(line)

        if not parsed:
            continue

        errors.append(parsed)

    return errors


def parse_generic(output: str) -> list[dict]:
    errors = []

    for line in output.splitlines():
        parsed = parse_location(line)

        if parsed:
            errors.append(parsed)

    return errors


def parse_errors(
    linter: str,
    output: str,
) -> list[dict]:
    if linter == "ruff":
        return parse_ruff(output)

    if linter == "flake8":
        return parse_flake8(output)

    if linter == "eslint":
        return parse_eslint(output)

    return parse_generic(output)


def lint(
    command: list[str] | None = None,
    linter: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_output: int = DEFAULT_MAX_OUTPUT,
) -> dict:
    if timeout < 1:
        raise ValueError(
            "timeout must be greater than 0"
        )

    if linter is None:
        linter = detect_linter()

    if not linter:
        raise RuntimeError(
            "could not detect a supported linter"
        )

    if command is None:
        command = default_command(linter)

    exit_code, raw_output, timed_out = run_command(
        command,
        timeout=timeout,
    )

    output, truncated = truncate_output(
        raw_output,
        max_output=max_output,
    )

    errors = parse_errors(
        linter,
        output,
    )

    return {
        "linter": linter,
        "command": command,
        "passed": (
            exit_code == 0
            and not timed_out
        ),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "error_count": len(errors),
        "errors": errors,
        "output": output,
        "output_truncated": truncated,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compact, agent-oriented lint "
            "interface."
        )
    )

    parser.add_argument(
        "--linter",
        choices=[
            "ruff",
            "flake8",
            "pylint",
            "eslint",
            "biome",
            "clippy",
            "go-vet",
        ],
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
    )

    parser.add_argument(
        "--max-output",
        type=int,
        default=DEFAULT_MAX_OUTPUT,
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="omit raw output from the result",
    )

    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="explicit command to execute",
    )

    args = parser.parse_args()

    command = args.command

    if command and command[0] == "--":
        command = command[1:]

    if not command:
        command = None

    try:
        result = lint(
            command=command,
            linter=args.linter,
            timeout=args.timeout,
            max_output=args.max_output,
        )
    except (
        RuntimeError,
        ValueError,
    ) as exc:
        parser.error(str(exc))
        return

    if args.quiet:
        result.pop("output", None)

    print(
        json.dumps(
            result,
            separators=(",", ":"),
        )
    )

    if not result["passed"]:
        raise SystemExit(
            result["exit_code"]
            if result["exit_code"] != 0
            else 1
        )


if __name__ == "__main__":
    main()