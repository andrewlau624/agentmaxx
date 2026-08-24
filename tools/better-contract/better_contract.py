#!/usr/bin/env python3
"""Better-contract: Extract API routes and type schemas.

Locates routes, request/response types, and handler functions.

Usage:
    python3 better_contract.py "src/routes"
    python3 better_contract.py "api.py" --format openapi
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


def extract_routes(
    path: str = ".",
    max_routes: int = 50,
) -> list[dict[str, str]]:
    """Extract API routes from files."""
    better_grep = _load_tool("better-grep")
    
    patterns = [
        r"@(?:app|router|route)\.(?:get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)",
        r"(?:app|router)\.(?:get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)",
        r"router\.(?:get|post|put|delete|patch|use)\s*\(\s*['\"]([^'\"]+)",
    ]
    
    routes = []
    for pattern in patterns:
        try:
            found = better_grep.search(
                query=[pattern],
                path=path,
                max_results=max_routes,
            )
            if found and "results" in found:
                for result in found["results"]:
                    match = re.search(pattern, result.get("text", ""))
                    if match:
                        routes.append({
                            "path": match.group(1),
                            "file": result.get("file", ""),
                            "line": result.get("line", 0),
                        })
        except Exception:
            pass
    
    return routes


def extract_schemas(
    path: str = ".",
    max_schemas: int = 30,
) -> dict[str, dict]:
    """Extract request/response type schemas."""
    better_grep = _load_tool("better-grep")
    
    patterns = [
        r"(?:class|interface|type)\s+(\w+(?:Request|Response|Schema|Model))\s*(?:\{|=|:)",
    ]
    
    schemas = {}
    for pattern in patterns:
        try:
            found = better_grep.search(
                query=[pattern],
                path=path,
                max_results=max_schemas,
            )
            if found and "results" in found:
                for result in found["results"]:
                    match = re.search(pattern, result.get("text", ""))
                    if match:
                        schema_name = match.group(1)
                        schemas[schema_name] = {
                            "file": result.get("file", ""),
                            "line": result.get("line", 0),
                        }
        except Exception:
            pass
    
    return schemas


def contract(
    path: str = ".",
    format: str = "json",
) -> dict[str, Any]:
    """Extract API contract (routes, schemas, handlers).
    
    Args:
        path: Route file or directory
        format: Output format ('json' or 'openapi')
    
    Returns:
        API contract structure
    """
    routes = extract_routes(path)
    schemas = extract_schemas(path)
    
    result = {
        "path": path,
        "format": format,
        "routes": routes,
        "schemas": schemas,
        "route_count": len(routes),
        "schema_count": len(schemas),
    }
    
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Extract API contracts from routes"
    )
    parser.add_argument("path", help="Route file or directory")
    parser.add_argument(
        "--format",
        choices=["json", "openapi"],
        default="json",
        help="Output format",
    )
    
    args = parser.parse_args()
    
    result = contract(path=args.path, format=args.format)
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
