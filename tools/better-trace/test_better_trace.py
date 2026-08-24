#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_trace.py")
spec = importlib.util.spec_from_file_location("better_trace_impl", path)
better_trace = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_trace)

trace = better_trace.trace


class TestTracing(unittest.TestCase):
    def test_callers_direction(self):
        result = trace("authenticate", direction="callers", depth=2, path=".")
        self.assertEqual(result["direction"], "callers")
        self.assertIn("callers", result)

    def test_callees_direction(self):
        result = trace("authenticate", direction="callees", depth=2, path=".")
        self.assertEqual(result["direction"], "callees")
        self.assertIn("callees", result)

    def test_both_direction(self):
        result = trace("authenticate", direction="both", depth=2, path=".")
        self.assertEqual(result["direction"], "both")

    def test_output_structure(self):
        result = trace("test", direction="callers", depth=1, path=".")
        self.assertIn("function", result)
        self.assertIn("direction", result)
        self.assertIn("depth", result)


if __name__ == "__main__":
    unittest.main()
