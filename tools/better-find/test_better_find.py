import importlib.util
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_find.py")
spec = importlib.util.spec_from_file_location("better_find_impl", path)
better_find = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_find)

find = better_find.find


class TestFind(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)

        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("")
        (root / "src" / "utils.py").write_text("")
        (root / "README.md").write_text("")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_finds_files(self):
        result = find(self.temp_dir.name)

        self.assertEqual(len(result["results"]), 3)
        self.assertFalse(result["truncated"])

    def test_filters_by_name(self):
        result = find(
            self.temp_dir.name,
            name="*.py",
        )

        self.assertEqual(len(result["results"]), 2)

    def test_finds_directories(self):
        result = find(
            self.temp_dir.name,
            file_type="dir",
        )

        self.assertEqual(
            result["results"],
            [str(Path(self.temp_dir.name) / "src")],
        )

    def test_respects_max_results(self):
        result = find(
            self.temp_dir.name,
            max_results=1,
        )

        self.assertEqual(len(result["results"]), 1)
        self.assertTrue(result["truncated"])

    def test_missing_path(self):
        with self.assertRaises(FileNotFoundError):
            find("/does/not/exist")

    def test_invalid_limit(self):
        with self.assertRaises(ValueError):
            find(self.temp_dir.name, max_results=0)


if __name__ == "__main__":
    unittest.main()
