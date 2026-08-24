#!/usr/bin/env python3
"""Better-types: Extract type signatures without implementation.

Returns type definitions, fields, and method signatures without code.

Usage:
    python3 better_types.py "User"
    python3 better_types.py "Handler" --kind interface
"""

import argparse
import json
import re
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


def extract_type_signature(
    typename: str,
    path: str = ".",
) -> dict[str, Any]:
    """Extract type/class signature from codebase."""
    better_grep = _load_tool("better-grep")
    
    # Find definition
    patterns = [
        rf"(?:class|interface|type|struct)\s+{re.escape(typename)}\s*(?:\{{|:|<|=|extends|implements)",
    ]
    
    results = []
    for pattern in patterns:
        try:
            found = better_grep.search(
                query=[pattern],
                path=path,
                max_results=5,
            )
            if found and "results" in found:
                results.extend(found["results"])
        except Exception:
            pass
    
    if not results:
        return {"type": typename, "found": False}
    
    # Parse first result
    result = results[0]
    file = result.get("file", "")
    line_no = result.get("line_number", 0)
    
    # Try to read type definition from file
    signature = {"type": typename, "found": True, "file": file, "line": line_no}
    
    try:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
            if line_no > 0 and line_no <= len(lines):
                # Capture type definition lines (simplified)
                type_lines = []
                for i in range(max(0, line_no - 1), min(len(lines), line_no + 20)):
                    line = lines[i].rstrip()
                    type_lines.append(line)
                    if "{" in line or ";" in line:
                        break
                
                signature["signature"] = "\n".join(type_lines)
    except Exception:
        pass
    
    return signature


def types(
    typename: str,
    kind: str = "all",
    path: str = ".",
) -> dict[str, Any]:
    """Extract type/interface signature.
    
    Args:
        typename: Type name to find
        kind: 'all', 'class', 'interface', 'type', 'struct'
        path: Repository root
    
    Returns:
        Type signature structure
    """
    result = extract_type_signature(typename, path)
    result["kind"] = kind
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extract type/interface signatures"
    )
    parser.add_argument("typename", help="Type name to find")
    parser.add_argument(
        "--kind",
        choices=["all", "class", "interface", "type", "struct"],
        default="all",
        help="Type kind to find",
    )
    parser.add_argument("--path", default=".", help="Repository root path")
    
    args = parser.parse_args()
    
    result = types(
        typename=args.typename,
        kind=args.kind,
        path=args.path,
    )
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
