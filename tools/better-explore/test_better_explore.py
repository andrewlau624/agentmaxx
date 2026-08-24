#!/usr/bin/env python3

import importlib.util
import json
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_explore.py")
spec = importlib.util.spec_from_file_location("better_explore_impl", path)
better_explore = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_explore)

explore = better_explore.explore
score_candidate = better_explore.score_candidate
extract_imports = better_explore.extract_imports
classify_file = better_explore.classify_file
CodeGraph = better_explore.CodeGraph


class TestClassification(unittest.TestCase):
    def test_entry_point_routes(self):
        self.assertEqual(classify_file("src/routes/users.py"), "entry_point")

    def test_entry_point_handlers(self):
        self.assertEqual(classify_file("app/handlers/auth.py"), "entry_point")

    def test_service_file(self):
        self.assertEqual(classify_file("src/user_service.py"), "service")

    def test_model_file(self):
        self.assertEqual(classify_file("src/models/user.py"), "model")

    def test_test_file(self):
        self.assertEqual(classify_file("tests/test_user.py"), "test")


class TestCodeGraph(unittest.TestCase):
    def test_distance_to_entry_point(self):
        graph = CodeGraph()
        graph.add_entry_point("routes/api.py")
        graph.add_relationship("routes/api.py", "services/user_service.py")
        graph.add_relationship("services/user_service.py", "models/user.py")

        # Entry point itself
        self.assertEqual(graph.distance_from_entry_points("routes/api.py"), 0)

        # One hop away
        self.assertEqual(graph.distance_from_entry_points("services/user_service.py"), 1)

        # Two hops away
        self.assertEqual(graph.distance_from_entry_points("models/user.py"), 2)

    def test_no_path_to_entry_point(self):
        graph = CodeGraph()
        graph.add_entry_point("routes/api.py")

        # Unrelated file returns max_distance (6)
        self.assertEqual(graph.distance_from_entry_points("utils/helpers.py"), 6)


class TestScoring(unittest.TestCase):
    def test_entry_point_boost(self):
        graph = CodeGraph()
        graph.add_entry_point("routes/api.py")

        score_ep = score_candidate("routes/api.py", 0, graph, 0)
        score_other = score_candidate("utils/helpers.py", 0, graph, 1)

        # Entry points and closer files score higher
        self.assertGreater(score_ep, score_other)

    def test_distance_penalty(self):
        graph = CodeGraph()

        score_close = score_candidate("service.py", 50, graph, 1)
        score_far = score_candidate("service.py", 50, graph, 5)

        # Closer files score higher, distance is penalized
        self.assertGreater(score_close, score_far)


class TestImports(unittest.TestCase):
    def test_python_imports(self):
        code = "from mymodule import foo\nimport bar.baz"
        imports = extract_imports(code, "test.py")
        self.assertIn("mymodule", imports)
        self.assertIn("bar.baz", imports)

    def test_typescript_imports(self):
        code = "import { foo } from './utils';"
        imports = extract_imports(code, "test.ts")
        self.assertIn("./utils", imports)

    def test_go_imports(self):
        code = 'import "github.com/user/package"'
        imports = extract_imports(code, "test.go")
        self.assertIn("github.com/user/package", imports)


if __name__ == "__main__":
    unittest.main()
