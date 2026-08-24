#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_symbol.py")
spec = importlib.util.spec_from_file_location("better_symbol_impl", path)
better_symbol = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_symbol)

symbol = better_symbol.symbol


class TestSymbolFinding(unittest.TestCase):
    def test_definition_kind(self):
        result = symbol("authenticate", kind="definition", path=".", max_results=5)
        self.assertEqual(result["kind"], "definition")
        self.assertEqual(result["symbol"], "authenticate")

    def test_usage_kind(self):
        result = symbol("authenticate", kind="usage", path=".", max_results=5)
        self.assertEqual(result["kind"], "usage")
        self.assertIsInstance(result["results"], list)

    def test_implementation_kind(self):
        result = symbol("Handler", kind="implementation", path=".", max_results=5)
        self.assertEqual(result["kind"], "implementation")

    def test_output_structure(self):
        result = symbol("test", kind="definition", path=".", max_results=3)
        self.assertIn("symbol", result)
        self.assertIn("kind", result)
        self.assertIn("results", result)
        self.assertIn("total_found", result)


if __name__ == "__main__":
    unittest.main()
