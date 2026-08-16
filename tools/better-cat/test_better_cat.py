import importlib.util
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_cat.py")
spec = importlib.util.spec_from_file_location("better_cat_impl", path)
better_cat = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_cat)

inspect = better_cat.inspect


class TestBetterCat(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "example.py"
        self.path.write_text(
            "line one\n"
            "line two\n"
            "line three\n"
            "line four\n"
            "line five\n"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_inspects_requested_range(self):
        result = inspect(str(self.path), start=2, end=4)

        self.assertEqual(result["start"], 2)
        self.assertEqual(result["end"], 4)
        self.assertEqual(
            result["content"],
            "2: line two\n3: line three\n4: line four",
        )
        self.assertFalse(result["truncated"])

    def test_defaults_to_entire_file(self):
        result = inspect(str(self.path))

        self.assertEqual(result["start"], 1)
        self.assertEqual(result["end"], 5)
        self.assertEqual(result["total_lines"], 5)

    def test_output_limit_truncates(self):
        result = inspect(str(self.path), max_output_chars=20)

        self.assertTrue(result["truncated"])
        self.assertLessEqual(len(result["content"]), 20)

    def test_invalid_start(self):
        with self.assertRaises(ValueError):
            inspect(str(self.path), start=0)

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            inspect(str(self.path), start=4, end=2)

    def test_invalid_output_limit(self):
        with self.assertRaises(ValueError):
            inspect(str(self.path), max_output_chars=0)

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            inspect(str(self.path.with_name("missing.py")))


if __name__ == "__main__":
    unittest.main()