#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_error.py")
spec = importlib.util.spec_from_file_location("better_error_impl", path)
better_error = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_error)

error = better_error.error


class TestErrorParsing(unittest.TestCase):
    def test_parse_python_error(self):
        trace = """
Traceback (most recent call last):
  File "src/service.py", line 42, in authenticate
    user = get_user(user_id)
  File "src/db.py", line 15, in get_user
    return db.query(user_id)
AttributeError: 'NoneType' object has no attribute 'query'
        """
        result = error(content=trace)
        self.assertIn("error_type", result)
        self.assertIn("message", result)

    def test_output_structure(self):
        trace = "ValueError: invalid literal"
        result = error(content=trace)
        self.assertIn("error_type", result)
        self.assertIn("message", result)


if __name__ == "__main__":
    unittest.main()
