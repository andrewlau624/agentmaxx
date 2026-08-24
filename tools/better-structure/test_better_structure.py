#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_structure.py")
spec = importlib.util.spec_from_file_location("better_structure_impl", path)
better_structure = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_structure)

structure = better_structure.structure


class TestStructureAnalysis(unittest.TestCase):
    def test_basic_structure(self):
        result = structure(path=".")
        self.assertIn("path", result)
        self.assertIn("layers", result)
        self.assertIn("entry_points", result)

    def test_output_structure(self):
        result = structure(path=".", max_depth=2)
        self.assertIsInstance(result["layers"], list)
        self.assertIsInstance(result["entry_points"], list)


if __name__ == "__main__":
    unittest.main()
