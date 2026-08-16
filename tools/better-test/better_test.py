#!/usr/bin/env python3

import argparse
import json
import re
import subprocess
from pathlib import Path


DEFAULT_MAX_OUTPUT = 12000
DEFAULT_TIMEOUT = 120


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
        output = "\n".join(
            part
            for part in (
                exc.stdout,
                exc.stderr,
            )
            if part
        )

        return 124, output or "test command timed out", True


def truncate_output(
    output: str,
    max_output: int,
) -> tuple[str, bool]:
    if max_output < 1:
        raise ValueError("max-output must be greater than 0")

    if len(output) <= max_output:
        return output, False

    half = max_output // 2

    truncated = (
        output[:half]
        + "\n\n... OUTPUT TRUNCATED ...\n\n"
        + output[-half:]
    )

    return truncated, True


def detect_framework() -> str:
    cwd = Path.cwd()

    if (
        (cwd / "pytest.ini").exists()
        or (cwd / "pyproject.toml").exists()
        or (cwd / "tox.ini").exists()
    ):
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--version"],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                return "pytest"
        except OSError:
            pass

    if (
        (cwd / "package.json").exists()
        or (cwd / "vitest.config.ts").exists()
        or (cwd / "vitest.config.js").exists()
    ):
        return "npm"

    if list(cwd.glob("test*.py")) or list(cwd.glob("tests/test*.py")):
        return "unittest"

    return "unknown"


def default_command(framework: str) -> list[str]:
    if framework == "pytest":
        return ["python", "-m", "pytest"]

    if framework == "npm":
        return ["npm", "test", "--", "--runInBand"]

    if framework == "unittest":
        return [
            "python",
            "-m",
            "unittest",
            "discover",
        ]

    raise RuntimeError(
        "could not detect a test framework; "
        "use --command"
    )


def parse_pytest(output: str) -> dict:
    result = {
        "framework": "pytest",
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
        "failures": [],
    }

    summary = output.splitlines()

    for line in summary:
        lower = line.lower()

        match = re.search(
            r"(\d+)\s+passed",
            lower,
        )
        if match:
            result["passed"] = int(match.group(1))

        match = re.search(
            r"(\d+)\s+failed",
            lower,
        )
        if match:
            result["failed"] = int(match.group(1))

        match = re.search(
            r"(\d+)\s+error",
            lower,
        )
        if match:
            result["errors"] = int(match.group(1))

        match = re.search(
            r"(\d+)\s+skipped",
            lower,
        )
        if match:
            result["skipped"] = int(match.group(1))

        match = re.search(
            r"(\d+)\s+xfailed",
            lower,
        )
        if match:
            result["xfailed"] = int(match.group(1))

        match = re.search(
            r"(\d+)\s+xpassed",
            lower,
        )
        if match:
            result["xpassed"] = int(match.group(1))

    failures = []

    for line in summary:
        stripped = line.strip()

        if stripped.startswith("FAILED"):
            failures.append(stripped)

        elif " - " in stripped and (
            "failed" in stripped.lower()
            or "error" in stripped.lower()
        ):
            failures.append(stripped)

    result["failures"] = failures[:50]

    return result


def parse_unittest(output: str) -> dict:
    result = {
        "framework": "unittest",
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "failures": [],
    }

    match = re.search(
        r"Ran\s+(\d+)\s+tests?",
        output,
    )

    total = int(match.group(1)) if match else 0

    failed_match = re.search(
        r"failures=(\d+)",
        output,
    )

    error_match = re.search(
        r"errors=(\d+)",
        output,
    )

    skipped_match = re.search(
        r"skipped=(\d+)",
        output,
    )

    result["failed"] = (
        int(failed_match.group(1))
        if failed_match
        else 0
    )

    result["errors"] = (
        int(error_match.group(1))
        if error_match
        else 0
    )

    result["skipped"] = (
        int(skipped_match.group(1))
        if skipped_match
        else 0
    )

    result["passed"] = max(
        0,
        total
        - result["failed"]
        - result["errors"]
        - result["skipped"],
    )

    failures = []

    for line in output.splitlines():
        if line.startswith("FAIL:"):
            failures.append(line)

        elif line.startswith("ERROR:"):
            failures.append(line)

    result["failures"] = failures[:50]

    return result


def parse_npm(output: str) -> dict:
    result = {
        "framework": "npm",
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "failures": [],
    }

    lower = output.lower()

    passed = re.findall(
        r"(\d+)\s+(?:passing|passed)",
        lower,
    )

    failed = re.findall(
        r"(\d+)\s+failing",
        lower,
    )

    if passed:
        result["passed"] = int(passed[-1])

    if failed:
        result["failed"] = int(failed[-1])

    if result["failed"] == 0:
        if "test failed" in lower or "tests failed" in lower:
            result["failed"] = 1

    failures = []

    for line in output.splitlines():
        stripped = line.strip()

        if (
            stripped.startswith("FAIL")
            or stripped.startswith("✕")
            or stripped.startswith("×")
        ):
            failures.append(stripped)

    result["failures"] = failures[:50]

    return result


def parse_results(
    framework: str,
    output: str,
) -> dict:
    if framework == "pytest":
        return parse_pytest(output)

    if framework == "unittest":
        return parse_unittest(output)

    if framework == "npm":
        return parse_npm(output)

    return {
        "framework": framework,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "failures": [],
    }

def extract_failure_context(
    output: str,
    max_failures: int = 10,
) -> list[str]:
    lines = output.splitlines()

    failures = []
    current = None

    for line in lines:
        stripped = line.strip()

        is_failure_start = (
            stripped.startswith("FAIL:")
            or stripped.startswith("ERROR:")
        )

        if is_failure_start:
            if current is not None:
                failures.append("\n".join(current))

            current = [line]
            continue

        if current is not None:
            if not stripped:
                failures.append("\n".join(current))
                current = None
            else:
                current.append(line)

    if current is not None:
        failures.append("\n".join(current))

    return failures[:max_failures]


def test(
    command: list[str] | None = None,
    framework: str | None = None,
    max_output: int = DEFAULT_MAX_OUTPUT,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict:
    if timeout < 1:
        raise ValueError(
            "timeout must be greater than 0"
        )

    if framework is None:
        framework = detect_framework()

    if command is None:
        command = default_command(framework)

    return_code, raw_output, timed_out = run_command(
        command,
        timeout=timeout,
    )

    bounded_output, truncated = truncate_output(
        raw_output,
        max_output,
    )

    results = parse_results(
        framework,
        raw_output,
    )

    failures = extract_failure_context(
        raw_output,
    )

    passed = (
        return_code == 0
        and not timed_out
    )

    return {
        "command": command,
        "framework": framework,
        "passed": passed,
        "exit_code": return_code,
        "timed_out": timed_out,
        "results": results,
        "failures": failures,
        "output": bounded_output,
        "output_truncated": truncated,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run tests with bounded, "
            "agent-oriented structured output."
        )
    )

    parser.add_argument(
        "--framework",
        choices=[
            "pytest",
            "unittest",
            "npm",
        ],
    )

    parser.add_argument(
        "--command",
        nargs="+",
        help=(
            "Explicit test command. "
            "Example: --command python -m pytest tests/"
        ),
    )

    parser.add_argument(
        "--max-output",
        type=int,
        default=DEFAULT_MAX_OUTPUT,
        help="Maximum output characters.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help="Maximum test runtime in seconds.",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only return structured test results.",
    )

    args = parser.parse_args()

    try:
        result = test(
            command=args.command,
            framework=args.framework,
            max_output=args.max_output,
            timeout=args.timeout,
        )

    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    if args.quiet:
        result.pop("output", None)
        result.pop("failures", None)

    print(
        json.dumps(
            result,
            separators=(",", ":"),
        )
    )

    raise SystemExit(
        0 if result["passed"] else 1
    )


if __name__ == "__main__":
    main()