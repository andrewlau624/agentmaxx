#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_related.py")
spec = importlib.util.spec_from_file_location("better_related_impl", path)
better_related = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_related)

related = better_related.related


class TestRelationships(unittest.TestCase):
    def test_all_kind(self):
        result = related("test.py", kind="all", path=".")
        self.assertEqual(result["kind"], "all")

    def test_imports_kind(self):
        result = related("test.py", kind="imports", path=".")
        self.assertIn("imports", result)

    def test_output_structure(self):
        result = related("test.py", kind="all", path=".")
        self.assertIn("file", result)
        self.assertIn("kind", result)


if __name__ == "__main__":
    unittest.main()
