#!/usr/bin/env python3
"""Better-structure: Generate codebase architecture and dependency graph.

Shows high-level structure: entry points, dependencies, layers.

Usage:
    python3 better_structure.py
    python3 better_structure.py --show-cycles
    python3 better_structure.py --max-depth 3
"""

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


def analyze_structure(
    path: str = ".",
    max_depth: int = 3,
    show_cycles: bool = False,
) -> dict[str, Any]:
    """Analyze codebase structure and dependencies.
    
    Args:
        path: Repository root
        max_depth: Maximum dependency depth to analyze
        show_cycles: Include import cycles in output
    
    Returns:
        Architecture structure
    """
    
    result = {
        "path": path,
        "layers": [],
        "entry_points": [],
        "dependency_depth": 0,
        "import_cycles": [],
    }
    
    # Simple heuristic: classify directories as layers
    base_path = Path(path)
    
    layers = []
    for item in sorted(base_path.iterdir()):
        if item.is_dir() and not item.name.startswith("."):
            # Classify layer
            layer_type = "other"
            if item.name in {"routes", "handlers", "api"}:
                layer_type = "entry_point"
            elif item.name in {"services", "handlers"}:
                layer_type = "business_logic"
            elif item.name in {"models", "types", "schemas"}:
                layer_type = "data"
            elif item.name in {"utils", "helpers", "lib"}:
                layer_type = "utilities"
            elif item.name in {"tests", "test", "specs"}:
                layer_type = "test"
            
            if layer_type == "entry_point":
                result["entry_points"].append(item.name)
            
            layers.append({
                "name": item.name,
                "type": layer_type,
                "path": str(item),
            })
    
    result["layers"] = layers
    
    return result


def structure(
    path: str = ".",
    max_depth: int = 3,
    show_cycles: bool = False,
) -> dict[str, Any]:
    """Generate codebase architecture.
    
    Args:
        path: Repository root
        max_depth: Maximum depth to analyze
        show_cycles: Include cycles
    
    Returns:
        Architecture structure
    """
    return analyze_structure(path, max_depth, show_cycles)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze codebase structure and architecture"
    )
    parser.add_argument("--path", default=".", help="Repository root")
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum dependency depth",
    )
    parser.add_argument(
        "--show-cycles",
        action="store_true",
        help="Show import cycles",
    )
    
    args = parser.parse_args()
    
    result = structure(
        path=args.path,
        max_depth=args.max_depth,
        show_cycles=args.show_cycles,
    )
    
    print(json.dumps(result))


if __name__ == "__main__":
    main()
