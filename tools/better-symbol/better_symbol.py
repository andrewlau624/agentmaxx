#!/usr/bin/env python3
"""Better-symbol: Find symbol definitions, usages, and implementations.

Locates where a symbol (class, function, variable) is defined and where it's used,
with minimal output and context.

Usage:
    python3 better_symbol.py "UserService" --kind definition
    python3 better_symbol.py "authenticate" --kind usage --max-results 10
    python3 better_symbol.py "handleClick" --kind implementation
"""

import argparse
import json
import re
import sys
from collections import defaultdict
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


def find_symbol_definitions(
    symbol: str,
    path: str = ".",
    max_results: int = 20,
) -> list[dict[str, Any]]:
    """Find where a symbol is defined (class, function, interface, type).
    
    Returns locations with context lines showing the definition.
    """
    better_grep = _load_tool("better-grep")
    
    # Language-specific patterns for definitions
    patterns = [
        rf"^\s*(?:def|function|async\s+function)\s+{re.escape(symbol)}\s*\(",
        rf"^\s*(?:class|interface|type|struct)\s+{re.escape(symbol)}\s*(?:\{{|:|<|=)",
        rf"^\s*(?:const|let|var|export\s+(?:const|let|var))\s+{re.escape(symbol)}\s*[=:]",
        rf"^\s*{re.escape(symbol)}\s*:\s*(?:class|interface|type)",
    ]
    
    results = []
    for pattern in patterns:
        try:
            found = better_grep.search(
                query=[pattern],
                path=path,
                max_results=max_results,
            )
            if found and "results" in found:
                results.extend(found["results"])
        except Exception:
            pass
    
    # Deduplicate and return
    seen = set()
    unique = []
    for r in results:
        key = (r.get("file"), r.get("line"))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    return unique[:max_results]


def find_symbol_usages(
    symbol: str,
    path: str = ".",
    max_results: int = 30,
) -> list[dict[str, Any]]:
    """Find where a symbol is used/called.
    
    Filters out definitions to return only usages.
    """
    better_grep = _load_tool("better-grep")
    
    try:
        found = better_grep.search(
            query=[re.escape(symbol)],
            path=path,
            max_results=max_results * 2,  # Get extra to filter
        )
        if found and "results" in found:
            results = found["results"]
        else:
            results = []
    except Exception:
        return []
    
    # Filter to likely usages (not definitions)
    usages = []
    for result in results:
        line = result.get("text", "")
        file = result.get("file", "")
        
        # Skip definition patterns
        is_def = any([
            re.match(rf"^\s*(?:def|function|async\s+function|class|interface)\s", line),
            re.match(rf"^\s*(?:const|let|var|export)\s+{re.escape(symbol)}\s*[=:]", line),
            re.match(rf"^\s*{re.escape(symbol)}\s*:\s*(?:class|interface|type)", line),
        ])
        
        if not is_def:
            usages.append(result)
    
    return usages[:max_results]


def find_implementations(
    symbol: str,
    path: str = ".",
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Find interface/protocol implementations of a symbol."""
    better_grep = _load_tool("better-grep")
    
    patterns = [
        rf"(?:class|struct)\s+\w+\s+(?:implements|extends|:)\s+{re.escape(symbol)}",
        rf"(?:impl|impl<.*>)\s+{re.escape(symbol)}\s+for\s+\w+",
    ]
    
    results = []
    for pattern in patterns:
        try:
            found = better_grep.search(
                query=[pattern],
                path=path,
                max_results=max_results,
            )
            if found and "results" in found:
                results.extend(found["results"])
        except Exception:
            pass
    
    seen = set()
    unique = []
    for r in results:
        key = (r.get("file"), r.get("line"))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    
    return unique[:max_results]


def symbol(
    symbol: str,
    kind: str = "definition",
    path: str = ".",
    max_results: int = 10,
    max_output_chars: int = 5000,
) -> dict[str, Any]:
    """Find symbol locations by kind: definition, usage, or implementation.
    
    Args:
        symbol: Name of symbol to find
        kind: 'definition', 'usage', or 'implementation'
        path: Repository root
        max_results: Maximum results to return
        max_output_chars: Bounded output size
    
    Returns:
        Dict with results, scores, and reasoning
    """
    if kind == "definition":
        results = find_symbol_definitions(symbol, path, max_results)
    elif kind == "usage":
        results = find_symbol_usages(symbol, path, max_results)
    elif kind == "implementation":
        results = find_implementations(symbol, path, max_results)
    else:
        results = []
    
    # Format output
    output = {
        "symbol": symbol,
        "kind": kind,
        "results": results[:max_results],
        "total_found": len(results),
    }
    
    return output


def main():
    parser = argparse.ArgumentParser(
        description="Find symbol definitions, usages, or implementations"
    )
    parser.add_argument("symbol", help="Symbol name to find")
    parser.add_argument(
        "--kind",
        choices=["definition", "usage", "implementation"],
        default="definition",
        help="Type of symbol location to find",
    )
    parser.add_argument("--path", default=".", help="Repository root path")
    parser.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum results to return",
    )
    parser.add_argument(
        "--max-output-chars",
        type=int,
        default=5000,
        help="Bounded output size",
    )
    
    args = parser.parse_args()
    
    result = symbol(
        symbol=args.symbol,
        kind=args.kind,
        path=args.path,
        max_results=args.max_results,
        max_output_chars=args.max_output_chars,
    )
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
