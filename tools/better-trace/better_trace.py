#!/usr/bin/env python3
"""Better-trace: Call graph tracer for understanding call chains.

Shows what calls a function and what it calls, with depth control.

Usage:
    python3 better_trace.py "authenticate" --direction callers --depth 2
    python3 better_trace.py "processData" --direction callees --depth 3
    python3 better_trace.py "handleRequest" --show-entry-points
"""

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def _load_tool(name: str) -> Any:
    """Load a sibling tool dynamically."""
    import importlib.util
    mod_name = name.replace("-", "_")
    path = Path(__file__).parent.parent / name / f"{mod_name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def find_callers(
    function: str,
    path: str = ".",
    max_depth: int = 2,
    max_results: int = 50,
) -> dict[str, Any]:
    """Find functions that call the given function."""
    better_grep = _load_tool("better-grep")
    
    # Search for function calls
    pattern = rf"\b{re.escape(function)}\s*\("
    
    try:
        found = better_grep.search(
            query=[pattern],
            path=path,
            max_results=max_results,
        )
        if found and "results" in found:
            results = found["results"]
        else:
            results = []
    except Exception:
        results = []
    
    # Group by file
    by_file = defaultdict(list)
    for result in results:
        file = result.get("file", "")
        if file:
            by_file[file].append(result)
    
    return {
        "function": function,
        "callers": dict(by_file),
        "depth": 1,
        "total_found": len(found),
    }


def find_callees(
    function: str,
    path: str = ".",
    max_depth: int = 2,
    max_results: int = 50,
) -> dict[str, Any]:
    """Find functions called by the given function."""
    better_grep = _load_tool("better-grep")
    
    # Search for function definitions first
    def_pattern = rf"(?:def|function|async\s+function)\s+{re.escape(function)}\s*\("
    
    try:
        definitions = better_grep.search(
            query=[def_pattern],
            path=path,
            max_results=5,
        )
        if definitions and "results" in definitions:
            definitions = definitions["results"]
        else:
            definitions = []
    except Exception:
        definitions = []
    
    if not definitions:
        return {"function": function, "callees": [], "depth": 0}
    
    # For each definition, find what it calls
    # Simple heuristic: search for function calls within the file
    callees = []
    for defn in definitions:
        file = defn.get("file", "")
        if file:
            # This is simplified; real implementation would parse file
            try:
                found = better_grep.search(
                    query=[r"\w+\s*\("],
                    path=file,
                    max_results=max_results,
                )
                if found and "results" in found:
                    callees.extend(found["results"])
            except Exception:
                pass
    
    return {
        "function": function,
        "callees": callees[:max_results],
        "depth": 1,
        "total_found": len(callees),
    }


def trace(
    function: str,
    direction: str = "callers",
    depth: int = 2,
    path: str = ".",
    show_entry_points: bool = False,
    max_results: int = 50,
) -> dict[str, Any]:
    """Trace call graph for a function.
    
    Args:
        function: Function name to trace
        direction: 'callers', 'callees', or 'both'
        depth: How deep to trace
        path: Repository root
        show_entry_points: Highlight entry points in output
        max_results: Maximum results per level
    
    Returns:
        Call graph structure
    """
    if direction in ("callers", "both"):
        callers = find_callers(function, path, depth, max_results)
    else:
        callers = None
    
    if direction in ("callees", "both"):
        callees = find_callees(function, path, depth, max_results)
    else:
        callees = None
    
    result = {
        "function": function,
        "direction": direction,
        "depth": depth,
    }
    
    if callers:
        result["callers"] = callers
    if callees:
        result["callees"] = callees
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Trace call graph for a function"
    )
    parser.add_argument("function", help="Function name to trace")
    parser.add_argument(
        "--direction",
        choices=["callers", "callees", "both"],
        default="callers",
        help="Direction to trace",
    )
    parser.add_argument(
        "--depth",
        type=int,
        default=2,
        help="Trace depth",
    )
    parser.add_argument("--path", default=".", help="Repository root path")
    parser.add_argument(
        "--show-entry-points",
        action="store_true",
        help="Highlight entry points",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=50,
        help="Maximum results per level",
    )
    
    args = parser.parse_args()
    
    result = trace(
        function=args.function,
        direction=args.direction,
        depth=args.depth,
        path=args.path,
        show_entry_points=args.show_entry_points,
        max_results=args.max_results,
    )
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
