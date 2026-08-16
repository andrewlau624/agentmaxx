import tempfile
import unittest
from pathlib import Path

import importlib.util
from pathlib import Path

path = Path(__file__).with_name("better_tree.py")
spec = importlib.util.spec_from_file_location(
    "better_tree_impl",
    path,
)
better_tree = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_tree)
tree = better_tree.tree


class TestBetterTree(unittest.TestCase):
    def test_tree_lists_files_and_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("print('hello')")
            (root / "README.md").write_text("# Test")

            result = tree(tmp, max_depth=3)

            paths = {
                entry["path"]
                for entry in result["entries"]
            }

            self.assertIn("src", paths)
            self.assertIn("src/main.py", paths)
            self.assertIn("README.md", paths)

    def test_file_size_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            content = "hello world"
            (root / "test.txt").write_text(content)

            result = tree(tmp)

            file_entry = next(
                entry
                for entry in result["entries"]
                if entry["path"] == "test.txt"
            )

            self.assertEqual(
                file_entry["type"],
                "file",
            )

            self.assertEqual(
                file_entry["size"],
                len(content.encode()),
            )

    def test_common_directories_are_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / ".git").mkdir()
            (root / "node_modules").mkdir()
            (root / "__pycache__").mkdir()
            (root / "src").mkdir()

            result = tree(tmp)

            paths = {
                entry["path"]
                for entry in result["entries"]
            }

            self.assertNotIn(".git", paths)
            self.assertNotIn("node_modules", paths)
            self.assertNotIn("__pycache__", paths)
            self.assertIn("src", paths)

    def test_hidden_files_are_ignored_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / ".env").write_text("SECRET=value")
            (root / "main.py").write_text("print('hello')")

            result = tree(tmp)

            paths = {
                entry["path"]
                for entry in result["entries"]
            }

            self.assertNotIn(".env", paths)
            self.assertIn("main.py", paths)

    def test_hidden_files_can_be_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / ".env").write_text("SECRET=value")

            result = tree(
                tmp,
                show_hidden=True,
            )

            paths = {
                entry["path"]
                for entry in result["entries"]
            }

            self.assertIn(".env", paths)

    def test_ignored_directories_can_be_included(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "node_modules").mkdir()
            (root / "node_modules" / "package.js").write_text("x")

            result = tree(
                tmp,
                include_ignored=True,
            )

            paths = {
                entry["path"]
                for entry in result["entries"]
            }

            self.assertIn("node_modules", paths)
            self.assertIn(
                "node_modules/package.js",
                paths,
            )

    def test_depth_zero_only_lists_direct_children(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "src").mkdir()
            (root / "src" / "main.py").write_text("x")
            (root / "README.md").write_text("readme")

            result = tree(
                tmp,
                max_depth=0,
            )

            paths = {
                entry["path"]
                for entry in result["entries"]
            }

            self.assertIn("src", paths)
            self.assertIn("README.md", paths)
            self.assertNotIn("src/main.py", paths)

    def test_depth_one_includes_one_child_level(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "src").mkdir()
            (root / "src" / "lib").mkdir()
            (root / "src" / "main.py").write_text("x")
            (root / "src" / "lib" / "util.py").write_text("x")

            result = tree(
                tmp,
                max_depth=1,
            )

            paths = {
                entry["path"]
                for entry in result["entries"]
            }

            self.assertIn("src", paths)
            self.assertIn("src/main.py", paths)
            self.assertIn("src/lib", paths)
            self.assertNotIn(
                "src/lib/util.py",
                paths,
            )

    def test_max_entries_bounds_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            for index in range(20):
                (root / f"file-{index}.txt").write_text("x")

            result = tree(
                tmp,
                max_entries=5,
            )

            self.assertEqual(
                result["count"],
                5,
            )

            self.assertEqual(
                len(result["entries"]),
                5,
            )

            self.assertTrue(
                result["truncated"]
            )

    def test_not_truncated_when_under_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "a.txt").write_text("a")
            (root / "b.txt").write_text("b")

            result = tree(
                tmp,
                max_entries=10,
            )

            self.assertFalse(
                result["truncated"]
            )

    def test_invalid_depth(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                tree(
                    tmp,
                    max_depth=-1,
                )

    def test_invalid_max_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                tree(
                    tmp,
                    max_entries=0,
                )

    def test_missing_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "does-not-exist"

            with self.assertRaises(RuntimeError):
                tree(str(missing))

    def test_file_as_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "file.txt"
            path.write_text("hello")

            with self.assertRaises(RuntimeError):
                tree(str(path))

    def test_entries_are_sorted_directories_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            (root / "z-file.txt").write_text("x")
            (root / "a-dir").mkdir()
            (root / "b-file.txt").write_text("x")
            (root / "b-dir").mkdir()

            result = tree(tmp)

            names = [
                entry["name"]
                for entry in result["entries"]
            ]

            self.assertEqual(
                names,
                [
                    "a-dir",
                    "b-dir",
                    "b-file.txt",
                    "z-file.txt",
                ],
            )


if __name__ == "__main__":
    unittest.main()