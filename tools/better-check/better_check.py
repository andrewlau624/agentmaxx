#!/usr/bin/env python3

import argparse
import json
import shutil
import subprocess
from pathlib import Path


DEFAULT_TIMEOUT = 60
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

        output += "command timed out"

        return 124, output, True


def truncate_output(
    output: str,
    max_output: int = DEFAULT_MAX_OUTPUT,
) -> tuple[str, bool]:
    if max_output < 1:
        raise ValueError(
            "max_output must be greater than 0"
        )

    if len(output) <= max_output:
        return output, False

    marker = "\n... OUTPUT TRUNCATED ..."

    if max_output <= len(marker):
        return marker[:max_output], True

    return (
        output[:max_output - len(marker)]
        + marker,
        True,
    )


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def detect_project() -> dict:
    root = Path.cwd()

    return {
        "python": (
            (root / "pyproject.toml").exists()
            or (root / "setup.py").exists()
            or (root / "setup.cfg").exists()
        ),
        "javascript": (
            (root / "package.json").exists()
        ),
        "typescript": (
            (root / "tsconfig.json").exists()
        ),
        "rust": (
            (root / "Cargo.toml").exists()
        ),
        "go": (
            (root / "go.mod").exists()
        ),
    }


def detect_test_command() -> list[str] | None:
    project = detect_project()

    if project["python"]:
        if Path("pytest.ini").exists():
            return ["pytest"]

        if Path("pyproject.toml").exists():
            try:
                content = Path(
                    "pyproject.toml"
                ).read_text()

                if (
                    "[tool.pytest" in content
                    or "pytest" in content
                ):
                    if command_exists("pytest"):
                        return ["pytest"]

            except OSError:
                pass

        if command_exists("pytest"):
            return ["pytest"]

        return [
            "python",
            "-m",
            "unittest",
            "discover",
        ]

    if project["javascript"]:
        if command_exists("npm"):
            return [
                "npm",
                "test",
                "--",
                "--runInBand",
            ]

    if project["rust"]:
        if command_exists("cargo"):
            return [
                "cargo",
                "test",
            ]

    if project["go"]:
        if command_exists("go"):
            return [
                "go",
                "test",
                "./...",
            ]

    return None


def detect_lint_command() -> list[str] | None:
    project = detect_project()

    if project["python"]:
        if command_exists("ruff"):
            return [
                "ruff",
                "check",
                ".",
            ]

        if command_exists("flake8"):
            return [
                "flake8",
                ".",
            ]

    if project["javascript"]:
        if command_exists("eslint"):
            return [
                "eslint",
                ".",
            ]

        if command_exists("biome"):
            return [
                "biome",
                "check",
                ".",
            ]

    if project["rust"]:
        if command_exists("cargo"):
            return [
                "cargo",
                "clippy",
                "--all-targets",
                "--all-features",
            ]

    if project["go"]:
        if command_exists("golangci-lint"):
            return [
                "golangci-lint",
                "run",
            ]

        if command_exists("go"):
            return [
                "go",
                "vet",
                "./...",
            ]

    return None


def detect_typecheck_command() -> list[str] | None:
    project = detect_project()

    if project["typescript"]:
        if command_exists("tsc"):
            return [
                "tsc",
                "--noEmit",
            ]

        if command_exists("npx"):
            return [
                "npx",
                "tsc",
                "--noEmit",
            ]

    if project["python"]:
        if command_exists("mypy"):
            return [
                "mypy",
                ".",
            ]

        if command_exists("pyright"):
            return [
                "pyright",
            ]

    if project["go"]:
        if command_exists("go"):
            return [
                "go",
                "vet",
                "./...",
            ]

    if project["rust"]:
        if command_exists("cargo"):
            return [
                "cargo",
                "check",
                "--all-targets",
                "--all-features",
            ]

    return None


def detect_build_command() -> list[str] | None:
    project = detect_project()

    if project["javascript"]:
        package_json = Path(
            "package.json"
        )

        try:
            package = json.loads(
                package_json.read_text()
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            package = {}

        scripts = package.get(
            "scripts",
            {},
        )

        if "build" in scripts:
            if command_exists("npm"):
                return [
                    "npm",
                    "run",
                    "build",
                ]

    if project["rust"]:
        if command_exists("cargo"):
            return [
                "cargo",
                "build",
            ]

    if project["go"]:
        if command_exists("go"):
            return [
                "go",
                "build",
                "./...",
            ]

    return None


def run_check(
    name: str,
    command: list[str] | None,
    timeout: int,
    max_output: int,
) -> dict:
    if command is None:
        return {
            "name": name,
            "available": False,
            "passed": True,
            "skipped": True,
            "exit_code": None,
            "timed_out": False,
            "output": "",
            "output_truncated": False,
        }

    exit_code, raw_output, timed_out = (
        run_command(
            command,
            timeout=timeout,
        )
    )

    output, truncated = truncate_output(
        raw_output,
        max_output=max_output,
    )

    return {
        "name": name,
        "available": True,
        "passed": (
            exit_code == 0
            and not timed_out
        ),
        "skipped": False,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "command": command,
        "output": output,
        "output_truncated": truncated,
    }


def check(
    test_command: list[str] | None = None,
    lint_command: list[str] | None = None,
    typecheck_command: list[str] | None = None,
    build_command: list[str] | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    max_output: int = DEFAULT_MAX_OUTPUT,
    stop_on_failure: bool = False,
) -> dict:
    if timeout < 1:
        raise ValueError(
            "timeout must be greater than 0"
        )

    if max_output < 1:
        raise ValueError(
            "max_output must be greater than 0"
        )

    if test_command is None:
        test_command = detect_test_command()

    if lint_command is None:
        lint_command = detect_lint_command()

    if typecheck_command is None:
        typecheck_command = (
            detect_typecheck_command()
        )

    if build_command is None:
        build_command = detect_build_command()

    commands = [
        ("test", test_command),
        ("lint", lint_command),
        ("typecheck", typecheck_command),
        ("build", build_command),
    ]

    results = []

    for name, command in commands:
        result = run_check(
            name,
            command,
            timeout,
            max_output,
        )

        results.append(result)

        if (
            stop_on_failure
            and not result["passed"]
            and not result["skipped"]
        ):
            break

    failed = [
        result["name"]
        for result in results
        if (
            not result["passed"]
            and not result["skipped"]
        )
    ]

    skipped = [
        result["name"]
        for result in results
        if result["skipped"]
    ]

    return {
        "passed": not failed,
        "failed": failed,
        "skipped": skipped,
        "checks": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Compact, agent-oriented "
            "project verification interface."
        )
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
        "--stop-on-failure",
        action="store_true",
    )

    parser.add_argument(
        "--test",
        nargs="+",
        help="explicit test command",
    )

    parser.add_argument(
        "--lint",
        nargs="+",
        help="explicit lint command",
    )

    parser.add_argument(
        "--typecheck",
        nargs="+",
        help="explicit type-check command",
    )

    parser.add_argument(
        "--build",
        nargs="+",
        help="explicit build command",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="omit command output",
    )

    args = parser.parse_args()

    try:
        result = check(
            test_command=args.test,
            lint_command=args.lint,
            typecheck_command=args.typecheck,
            build_command=args.build,
            timeout=args.timeout,
            max_output=args.max_output,
            stop_on_failure=args.stop_on_failure,
        )
    except ValueError as exc:
        parser.error(str(exc))
        return

    if args.quiet:
        for item in result["checks"]:
            item.pop("output", None)

    print(
        json.dumps(
            result,
            separators=(",", ":"),
        )
    )

    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()