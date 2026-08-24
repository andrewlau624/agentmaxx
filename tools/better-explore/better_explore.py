#!/usr/bin/env python3

"""Repository code discovery agent — enhanced with code graph analysis.

Discovers the minimum necessary context for a task by:
1. Running initial keyword searches to find candidate files
2. Building a lightweight code graph (imports/calls)
3. Ranking candidates by code relationship, not just keyword matching
4. Returning a prioritized reading list with explanations

The ranking understands:
- Distance from entry points (routes, handlers, services)
- Import/call relationships between files
- Test co-location (files tested together are likely related)
- Keyword relevance (but weighted lower than code relationships)
"""

import argparse
import importlib.util
import json
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


TOOLS_ROOT = Path(__file__).resolve().parent.parent


def _load_tool(directory: str, module: str):
    """Load a sibling tool module by path."""
    path = TOOLS_ROOT / directory / f"{module}.py"
    spec = importlib.util.spec_from_file_location(module, path)

    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load tool module: {path}")

    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)

    return loaded


better_grep = _load_tool("better-grep", "better_grep")


class CodeGraph:
    """Lightweight code graph: imports, calls, and test relationships."""

    def __init__(self):
        self.imports: dict[str, set[str]] = defaultdict(set)
        self.called_by: dict[str, set[str]] = defaultdict(set)
        self.tests_for: dict[str, set[str]] = defaultdict(set)
        self.entry_points: set[str] = set()

    def add_import(self, from_file: str, to_module: str) -> None:
        """Record that from_file imports to_module."""
        self.imports[from_file].add(to_module)

    def add_relationship(self, from_file: str, to_file: str) -> None:
        """Record that from_file calls/uses to_file."""
        self.called_by[to_file].add(from_file)

    def add_entry_point(self, file: str) -> None:
        """Mark a file as an entry point (route, handler, main)."""
        self.entry_points.add(file)

    def add_test(self, test_file: str, source_file: str) -> None:
        """Record that test_file tests source_file."""
        self.tests_for[source_file].add(test_file)

    def distance_from_entry_points(
        self,
        file: str,
        max_distance: int = 5,
    ) -> int:
        """Shortest distance from file to any entry point.
        
        Lower distance = more directly related to entry points.
        """
        if file in self.entry_points:
            return 0

        visited = {file}
        queue = deque([(file, 0)])

        while queue:
            current, dist = queue.popleft()

            if dist >= max_distance:
                continue

            # Check what calls this file
            for caller in self.called_by[current]:
                if caller in self.entry_points:
                    return dist + 1

                if caller not in visited:
                    visited.add(caller)
                    queue.append((caller, dist + 1))

        return max_distance + 1


def extract_imports(content: str, file: str) -> set[str]:
    """Extract import paths from source code.

    Handles Python, TypeScript, JavaScript, and Go.
    Returns relative module/file references.
    """
    imports = set()

    # Python: from X import Y, import X.Y
    python_imports = re.findall(
        r"(?:from|import)\s+([.\w/]+)",
        content,
    )
    imports.update(python_imports)

    # TypeScript/JavaScript: from/import "path"
    ts_imports = re.findall(
        r"(?:from|import)\s+['\"]([^'\"]+)['\"]",
        content,
    )
    imports.update(ts_imports)

    # Go: import "path"
    go_imports = re.findall(
        r"import\s+\(?['\"]([^'\"]+)['\"]",
        content,
    )
    imports.update(go_imports)

    return imports


def classify_file(file: str) -> str:
    """Classify file by role: entry_point, service, model, test, other."""
    name = Path(file).name.lower()
    parts = file.lower().split("/")
    file_lower = file.lower()

    # Check for test first (overrides all other classification)
    if any(p in parts for p in {"test", "tests"}) or name.startswith("test_"):
        return "test"

    # Entry points: routes, handlers, main, cli
    if any(p in parts for p in {"route", "routes", "handler", "handlers", "main", "cli"}):
        return "entry_point"

    # Services: *service.py, *manager.py
    if name.endswith(("service.py", "manager.py")):
        return "service"

    # Models: *model.py or in models/ directory
    if name.endswith(("model.py", "models.py", "schema.py")) or any(p in {"model", "models"} for p in parts):
        return "model"

    return "other"


def build_code_graph(
    candidates: list[dict[str, Any]],
    repo_path: str = ".",
    max_files_to_analyze: int = 50,
) -> CodeGraph:
    """Build code graph from candidate files and their relationships.
    
    This is a lightweight analysis — we only examine files we know about
    from the search, not the whole repository.
    """
    graph = CodeGraph()

    candidate_files = {c["file"]: c for c in candidates[:max_files_to_analyze]}

    # Classify files
    for file in candidate_files:
        file_type = classify_file(file)
        if file_type == "entry_point":
            graph.add_entry_point(file)

    # Extract imports and build graph
    for file in candidate_files:
        # Try to read the file if it exists and is reasonably small
        file_path = Path(repo_path) / file
        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(errors="ignore")
            if len(content) > 100000:
                continue

            imports = extract_imports(content, file)

            # Find which other candidates this imports
            for imp in imports:
                imp_lower = imp.lower().replace(".", "/")
                for other in candidate_files:
                    if other == file:
                        continue
                    if imp_lower in other.lower():
                        graph.add_relationship(file, other)
        except Exception:
            continue

    return graph


def score_candidate(
    file: str,
    keyword_score: int,
    graph: CodeGraph,
    graph_distance: int,
) -> int:
    """Score a candidate based on keyword match + code graph position.
    
    Factors:
    - Base keyword score (existing logic)
    - Distance from entry points (closer = better)
    - Is it a service/model (high signal)
    - Has tests (high signal)
    """
    score = keyword_score

    # Entry points and services are high-signal
    file_type = classify_file(file)
    if file_type == "entry_point":
        score += 50
    elif file_type == "service":
        score += 30
    elif file_type == "model":
        score += 20

    # Distance from entry points: closer is better
    # Max of 6 means very distant files get penalized
    distance_penalty = max(0, (graph_distance - 1) * 15)
    score -= distance_penalty

    # Has tests: boosted
    if graph.tests_for.get(file):
        score += 25

    return score


def search_initial(
    task: str,
    path: str = ".",
    max_results: int = 30,
    max_output_chars: int = 5000,
) -> list[dict[str, Any]]:
    """Initial broad search to identify candidate files.

    Extracts key phrases from task and searches for them.
    """
    # Extract likely search terms from task
    common_words = {
        "the", "a", "an", "and", "or", "but", "if", "for", "to",
        "from", "by", "with", "be", "is", "are", "was", "were",
        "this", "that", "these", "those", "what", "which", "who",
        "when", "where", "why", "how", "should", "must", "add",
        "fix", "implement", "refactor", "create", "build", "setup",
    }

    words = re.findall(r"\b\w+\b", task.lower())
    queries = [
        w for w in words
        if len(w) > 3 and w not in common_words
    ][:5]

    if not queries:
        queries = [task.split()[0]] if task.split() else [""]

    try:
        found = better_grep.search(
            query=queries,
            path=path,
            max_results=max_results,
            max_output_chars=max_output_chars,
        )
    except Exception:
        return []

    candidates = []
    for result in found.get("results", []):
        candidates.append({
            "file": result["file"],
            "line": result["line"],
            "text": result["text"],
            "keyword_score": result.get("_score", 0),
        })

    return candidates


def explore(
    task: str,
    path: str = ".",
    num_candidates: int = 5,
    max_searches: int = 30,
) -> dict[str, Any]:
    """Explore repository to find minimum context for a task.

    Returns:
        Dictionary with:
        - candidates: ranked list of files to read
        - scores: score for each candidate
        - reasoning: explanation of ranking
        - entry_points: identified entry points
    """
    if not task.strip():
        raise ValueError("task description is required")

    # Initial search
    candidates = search_initial(
        task=task,
        path=path,
        max_results=max_searches,
    )

    if not candidates:
        return {
            "candidates": [],
            "reasoning": ["No matching files found"],
            "entry_points": [],
            "total_matched": 0,
        }

    # Group by file, keeping highest-scoring instance
    by_file: dict[str, dict[str, Any]] = {}
    for cand in candidates:
        file = cand["file"]
        if file not in by_file or cand["keyword_score"] > by_file[file]["keyword_score"]:
            by_file[file] = cand

    # Build code graph
    graph = build_code_graph(list(by_file.values()), path, max_files_to_analyze=50)

    # Re-score with graph information
    scored = []
    for file, cand in by_file.items():
        distance = graph.distance_from_entry_points(file, max_distance=6)
        final_score = score_candidate(
            file,
            cand["keyword_score"],
            graph,
            distance,
        )
        scored.append({
            "file": file,
            "score": final_score,
            "distance": distance,
            "type": classify_file(file),
        })

    ranked = sorted(scored, key=lambda x: -x["score"])[:num_candidates]

    reasoning = []
    for i, item in enumerate(ranked, 1):
        score = item["score"]
        file_type = item["type"]
        distance = item["distance"]
        reasoning.append(
            f"{i}. {item['file']} (score: {score}, type: {file_type}, distance: {distance})"
        )

    return {
        "candidates": [r["file"] for r in ranked],
        "scores": [r["score"] for r in ranked],
        "reasoning": reasoning,
        "entry_points": sorted(graph.entry_points),
        "total_matched": len(candidates),
        "total_unique": len(by_file),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Explore repository to find candidate files for a task. "
            "Uses code graph analysis to rank by relevance, not just keywords."
        )
    )

    parser.add_argument(
        "task",
        help="Description of the task to explore",
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Repository root path",
    )
    parser.add_argument(
        "--num-candidates",
        type=int,
        default=5,
        help="Number of top candidates to return",
    )
    parser.add_argument(
        "--max-searches",
        type=int,
        default=30,
        help="Maximum number of search results to consider",
    )

    args = parser.parse_args()

    try:
        output = explore(
            task=args.task,
            path=args.path,
            num_candidates=args.num_candidates,
            max_searches=args.max_searches,
        )
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    print(json.dumps(output, separators=(",", ":")))


if __name__ == "__main__":
    main()



def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Explore repository to find candidate files for a task. "
            "Returns a ranked reading list with explanations."
        )
    )

    parser.add_argument(
        "task",
        help="Description of the task to explore",
    )
    parser.add_argument(
        "--path",
        default=".",
        help="Repository root path",
    )
    parser.add_argument(
        "--num-candidates",
        type=int,
        default=5,
        help="Number of top candidates to return",
    )
    parser.add_argument(
        "--max-searches",
        type=int,
        default=30,
        help="Maximum number of search results to consider",
    )

    args = parser.parse_args()

    try:
        output = explore(
            task=args.task,
            path=args.path,
            num_candidates=args.num_candidates,
            max_searches=args.max_searches,
        )
    except (RuntimeError, ValueError) as exc:
        parser.error(str(exc))

    print(json.dumps(output, separators=(",", ":")))


if __name__ == "__main__":
    main()
