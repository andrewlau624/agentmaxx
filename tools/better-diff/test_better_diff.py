#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_diff.py")
spec = importlib.util.spec_from_file_location("better_diff_impl", path)
better_diff = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_diff)

diff = better_diff.diff


class TestDiffGeneration(unittest.TestCase):
    def test_diff_output_structure(self):
        result = diff(path=".", commits=1)
        self.assertIn("path", result)

    def test_path_parameter(self):
        result = diff(path=".", commits=1)
        self.assertEqual(result["path"], ".")


if __name__ == "__main__":
    unittest.main()
