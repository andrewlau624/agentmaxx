import importlib.util
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_edit.py")
spec = importlib.util.spec_from_file_location("better_edit_impl", path)
better_edit = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_edit)

edit_many = better_edit.edit_many


class TestBetterEdit(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "example.py"
        self.path.write_text("alpha\nbeta\ngamma\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_applies_single_edit(self):
        result = edit_many(
            [{"path": str(self.path), "old": "beta", "new": "BETA"}]
        )

        self.assertEqual(self.path.read_text(), "alpha\nBETA\ngamma\n")
        self.assertEqual(result["files_changed"], 1)
        self.assertEqual(result["edits"][0]["line"], 2)

    def test_applies_multiple_edits_across_files(self):
        second = Path(self.temp_dir.name) / "second.py"
        second.write_text("one\ntwo\n")

        result = edit_many(
            [
                {"path": str(self.path), "old": "alpha", "new": "ALPHA"},
                {"path": str(second), "old": "two", "new": "TWO"},
            ]
        )

        self.assertEqual(self.path.read_text(), "ALPHA\nbeta\ngamma\n")
        self.assertEqual(second.read_text(), "one\nTWO\n")
        self.assertEqual(result["files_changed"], 2)

    def test_sequential_edits_to_same_file_apply_in_order(self):
        edit_many(
            [
                {"path": str(self.path), "old": "alpha", "new": "ALPHA"},
                {"path": str(self.path), "old": "ALPHA", "new": "FINAL"},
            ]
        )

        self.assertEqual(self.path.read_text(), "FINAL\nbeta\ngamma\n")

    def test_missing_text_raises_without_writing(self):
        with self.assertRaises(ValueError):
            edit_many([{"path": str(self.path), "old": "missing", "new": "x"}])

        self.assertEqual(self.path.read_text(), "alpha\nbeta\ngamma\n")

    def test_non_unique_text_requires_replace_all(self):
        self.path.write_text("dup\ndup\n")

        with self.assertRaises(ValueError):
            edit_many([{"path": str(self.path), "old": "dup", "new": "x"}])

    def test_replace_all_replaces_every_occurrence(self):
        self.path.write_text("dup\ndup\n")

        result = edit_many(
            [
                {
                    "path": str(self.path),
                    "old": "dup",
                    "new": "x",
                    "replace_all": True,
                }
            ]
        )

        self.assertEqual(self.path.read_text(), "x\nx\n")
        self.assertEqual(result["edits"][0]["occurrences"], 2)

    def test_failure_in_second_edit_writes_nothing(self):
        second = Path(self.temp_dir.name) / "second.py"
        second.write_text("one\ntwo\n")

        with self.assertRaises(ValueError):
            edit_many(
                [
                    {"path": str(self.path), "old": "alpha", "new": "ALPHA"},
                    {"path": str(second), "old": "missing", "new": "x"},
                ]
            )

        self.assertEqual(self.path.read_text(), "alpha\nbeta\ngamma\n")
        self.assertEqual(second.read_text(), "one\ntwo\n")

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            edit_many(
                [
                    {
                        "path": str(self.path.with_name("missing.py")),
                        "old": "x",
                        "new": "y",
                    }
                ]
            )

    def test_requires_at_least_one_edit(self):
        with self.assertRaises(ValueError):
            edit_many([])

    def test_old_equal_new_rejected(self):
        with self.assertRaises(ValueError):
            edit_many([{"path": str(self.path), "old": "beta", "new": "beta"}])


if __name__ == "__main__":
    unittest.main()
