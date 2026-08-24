#!/usr/bin/env python3
"""Better-error: Parse stack traces and extract actionable context.

Locates the actual error, failing line, and probable cause from verbose traces.

Usage:
    python3 better_error.py < stacktrace.txt
    python3 better_error.py --file error.log
    cat error.log | python3 better_error.py
"""

import argparse
import json
import re
import sys
from typing import Any


def parse_traceback(content: str) -> dict[str, Any]:
    """Parse a Python/JS/Go traceback and extract error context."""
    
    result = {
        "error_type": None,
        "message": None,
        "failing_file": None,
        "failing_line_no": None,
        "failing_line": None,
        "context": [],
        "raw_trace": content[:500],  # First 500 chars of trace
    }
    
    lines = content.split("\n")
    
    # Find error type and message (usually at the end)
    for i in range(len(lines) - 1, max(0, len(lines) - 10), -1):
        line = lines[i].strip()
        if "Error" in line or "Exception" in line:
            match = re.search(r"(\w+(?:Error|Exception)): (.+)", line)
            if match:
                result["error_type"] = match.group(1)
                result["message"] = match.group(2)
                break
    
    # Find failing file and line (usually in traceback body)
    file_pattern = r"(?:File|at|in)\s+['\"]?([^\s'\"]+\.(?:py|js|ts|go))['\"]?.*?(?:line|:)\s+(\d+)"
    matches = re.finditer(file_pattern, content)
    failing = list(matches)
    
    if failing:
        last = failing[-1]  # Last occurrence is usually the failing line
        result["failing_file"] = last.group(1)
        result["failing_line_no"] = int(last.group(2))
    
    # Extract context: lines mentioning the error or key parts
    for line in lines:
        if result["error_type"] and result["error_type"] in line:
            result["context"].append(line.strip())
        elif "File" in line or "at " in line:
            result["context"].append(line.strip())
    
    return result


def error(
    content: str = None,
    file: str = None,
) -> dict[str, Any]:
    """Parse error from content or file.
    
    Args:
        content: Error/traceback content as string
        file: File path to read error from
    
    Returns:
        Structured error information
    """
    if file:
        try:
            with open(file, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except Exception as e:
            return {"error": f"Could not read file: {e}"}
    
    if not content:
        return {"error": "No content provided"}
    
    return parse_traceback(content)


def main():
    parser = argparse.ArgumentParser(
        description="Parse error traces and extract actionable context"
    )
    parser.add_argument(
        "--file",
        help="File containing error trace",
    )
    parser.add_argument(
        "--content",
        help="Error content as string",
    )
    
    args = parser.parse_args()
    
    # If no args, read from stdin
    content = args.content
    if not content and not args.file:
        content = sys.stdin.read()
    
    result = error(content=content, file=args.file)
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
