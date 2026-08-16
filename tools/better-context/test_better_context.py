import importlib.util
import tempfile
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_context.py")
spec = importlib.util.spec_from_file_location("better_context_impl", path)
better_context = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_context)

collect = better_context.collect


class TestCollect(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

        (self.root / "auth.py").write_text(
            "\n".join(f"filler {index}" for index in range(1, 30))
            + "\ndef authenticate(user):\n"
            + "    return True\n"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_returns_source_window_around_match(self):
        result = collect("authenticate", path=str(self.root))

        self.assertEqual(len(result["regions"]), 1)

        region = result["regions"][0]

        self.assertEqual(region["match_line"], 30)
        self.assertIn("def authenticate(user):", region["content"])
        self.assertLess(region["start"], region["match_line"])

    def test_context_lines_bounds_window(self):
        result = collect(
            "authenticate",
            path=str(self.root),
            context_lines=2,
        )

        region = result["regions"][0]

        self.assertEqual(region["start"], 28)
        self.assertEqual(region["end"], 31)

    def test_accepts_multiple_queries(self):
        result = collect(
            ["authenticate", "filler 1"],
            path=str(self.root),
        )

        self.assertEqual(result["queries"], ["authenticate", "filler 1"])
        self.assertGreaterEqual(len(result["regions"]), 1)

    def test_no_match_returns_empty(self):
        result = collect("nonexistent_symbol", path=str(self.root))

        self.assertEqual(result["regions"], [])

    def test_invalid_max_hits(self):
        with self.assertRaises(ValueError):
            collect("authenticate", path=str(self.root), max_hits=0)

    def test_invalid_context_lines(self):
        with self.assertRaises(ValueError):
            collect(
                "authenticate",
                path=str(self.root),
                context_lines=-1,
            )

    def test_invalid_output_limit(self):
        with self.assertRaises(ValueError):
            collect(
                "authenticate",
                path=str(self.root),
                max_output_chars=0,
            )


if __name__ == "__main__":
    unittest.main()
