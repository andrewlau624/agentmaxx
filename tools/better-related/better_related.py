#!/usr/bin/env python3
"""Better-related: Find all file relationships at once.

Locates imports, tests, dependents, and config references for a file.

Usage:
    python3 better_related.py src/auth/service.py
    python3 better_related.py config/settings.py --kind imports
"""

import argparse
import json
import re
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


def find_imported_by(
    file: str,
    path: str = ".",
    max_results: int = 20,
) -> list[str]:
    """Find files that import this file."""
    better_grep = _load_tool("better-grep")
    
    # Extract module name from file
    module = Path(file).stem
    
    patterns = [
        rf"(?:from|import)\s+[.\w]*{re.escape(module)}",
        rf"require\s*\(\s*['\"][^'\"]*{re.escape(module)}['\"]",
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
                for r in found["results"]:
                    results.append(r.get("file", ""))
        except Exception:
            pass
    
    return list(set(filter(None, results)))[:max_results]


def find_imports(
    file: str,
    path: str = ".",
) -> list[str]:
    """Find what this file imports."""
    try:
        with open(file, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return []
    
    imports = set()
    
    # Python imports
    for match in re.finditer(r"(?:from|import)\s+([.\w]+)", content):
        imports.add(match.group(1))
    
    # JS/TS imports
    for match in re.finditer(r"(?:from|import)\s+['\"]([^'\"]+)['\"]", content):
        imports.add(match.group(1))
    
    # Go imports
    for match in re.finditer(r'import\s+["\']([^"\']+)["\']', content):
        imports.add(match.group(1))
    
    return sorted(list(imports))


def find_tests(
    file: str,
    path: str = ".",
    max_results: int = 10,
) -> list[str]:
    """Find test files for this file."""
    better_grep = _load_tool("better-grep")
    
    base = Path(file).stem
    patterns = [
        rf"test.*{re.escape(base)}",
        rf"{re.escape(base)}.*test",
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
                for r in found["results"]:
                    f = r.get("file", "")
                    if "test" in f.lower():
                        results.append(f)
        except Exception:
            pass
    
    return list(set(results))[:max_results]


def related(
    file: str,
    kind: str = "all",
    path: str = ".",
    max_results: int = 20,
) -> dict[str, Any]:
    """Get all relationships for a file.
    
    Args:
        file: File path to analyze
        kind: 'all', 'imports', 'imported_by', 'tests', 'dependents'
        path: Repository root
        max_results: Max results per category
    
    Returns:
        Relationship structure
    """
    result = {
        "file": file,
        "kind": kind,
    }
    
    if kind in ("all", "imports"):
        result["imports"] = find_imports(file, path)
    
    if kind in ("all", "imported_by"):
        result["imported_by"] = find_imported_by(file, path, max_results)
    
    if kind in ("all", "tests"):
        result["tests"] = find_tests(file, path, max_results)
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Find all relationships for a file"
    )
    parser.add_argument("file", help="File to analyze")
    parser.add_argument(
        "--kind",
        choices=["all", "imports", "imported_by", "tests", "dependents"],
        default="all",
        help="Type of relationships to find",
    )
    parser.add_argument("--path", default=".", help="Repository root path")
    parser.add_argument(
        "--max-results",
        type=int,
        default=20,
        help="Maximum results per category",
    )
    
    args = parser.parse_args()
    
    result = related(
        file=args.file,
        kind=args.kind,
        path=args.path,
        max_results=args.max_results,
    )
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
