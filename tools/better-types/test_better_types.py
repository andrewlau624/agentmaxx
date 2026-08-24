#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_types.py")
spec = importlib.util.spec_from_file_location("better_types_impl", path)
better_types = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_types)

types = better_types.types


class TestTypeExtraction(unittest.TestCase):
    def test_basic_extraction(self):
        result = types("Test", kind="all", path=".")
        self.assertIn("type", result)
        self.assertIn("kind", result)

    def test_output_structure(self):
        result = types("Test", path=".")
        self.assertIn("type", result)


if __name__ == "__main__":
    unittest.main()
