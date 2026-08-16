import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).with_name("better_grep.py")
spec = importlib.util.spec_from_file_location("better_grep_impl", path)
better_grep = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_grep)

search = better_grep.search
score_match = better_grep.score_match


class TestScoreMatch(unittest.TestCase):
    def test_definition_ranks_above_normal_match(self):
        definition = {
            "file": "src/auth.py",
            "line": 10,
            "column": 1,
            "text": "def authenticate(user):",
        }
        normal = {
            "file": "src/auth.py",
            "line": 20,
            "column": 5,
            "text": "authenticate(user)",
        }

        self.assertGreater(
            score_match("authenticate", definition),
            score_match("authenticate", normal),
        )

    def test_source_ranks_above_documentation(self):
        source = {
            "file": "src/auth.py",
            "line": 10,
            "column": 1,
            "text": "authenticate(user)",
        }
        documentation = {
            "file": "README.md",
            "line": 10,
            "column": 1,
            "text": "authenticate(user)",
        }

        self.assertGreater(
            score_match("authenticate", source),
            score_match("authenticate", documentation),
        )

    def test_lockfile_is_deprioritized(self):
        source = {
            "file": "src/app.py",
            "line": 10,
            "column": 1,
            "text": "dependency",
        }
        lockfile = {
            "file": "package-lock.json",
            "line": 10,
            "column": 1,
            "text": "dependency",
        }

        self.assertGreater(
            score_match("dependency", source),
            score_match("dependency", lockfile),
        )


class TestSearch(unittest.TestCase):
    @patch.object(better_grep.subprocess, "run")
    def test_returns_structured_matches(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({
                "type": "match",
                "data": {
                    "path": {"text": "src/auth.py"},
                    "line_number": 10,
                    "lines": {"text": "def authenticate(user):\n"},
                    "submatches": [{"start": 4}],
                },
            }),
            stderr="",
        )

        result = search("authenticate")

        self.assertEqual(
            result["results"],
            [{
                "file": "src/auth.py",
                "line": 10,
                "column": 5,
                "text": "def authenticate(user):",
            }],
        )
        self.assertFalse(result["truncated"])

    @patch.object(better_grep.subprocess, "run")
    def test_ignores_non_match_rg_events(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="\n".join([
                json.dumps({"type": "begin", "data": {}}),
                json.dumps({
                    "type": "match",
                    "data": {
                        "path": {"text": "src/app.py"},
                        "line_number": 4,
                        "lines": {"text": "search()\n"},
                        "submatches": [{"start": 0}],
                    },
                }),
                json.dumps({"type": "end", "data": {}}),
            ]),
            stderr="",
        )

        result = search("search")

        self.assertEqual(len(result["results"]), 1)
        self.assertEqual(result["results"][0]["file"], "src/app.py")

    @patch.object(better_grep.subprocess, "run")
    def test_max_results_truncates(self, mock_run):
        matches = [
            json.dumps({
                "type": "match",
                "data": {
                    "path": {"text": f"src/file{i}.py"},
                    "line_number": 1,
                    "lines": {"text": f"match{i}\n"},
                    "submatches": [{"start": 0}],
                },
            })
            for i in range(3)
        ]

        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="\n".join(matches),
            stderr="",
        )

        result = search("match", max_results=2)

        self.assertEqual(len(result["results"]), 2)
        self.assertTrue(result["truncated"])

    @patch.object(better_grep.subprocess, "run")
    def test_max_output_chars_bounds_results(self, mock_run):
        matches = [
            json.dumps({
                "type": "match",
                "data": {
                    "path": {"text": f"src/file{i}.py"},
                    "line_number": 1,
                    "lines": {"text": f"match{i}\n"},
                    "submatches": [{"start": 0}],
                },
            })
            for i in range(5)
        ]

        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout="\n".join(matches),
            stderr="",
        )

        result = search("match", max_output_chars=100)

        self.assertLessEqual(
            sum(
                len(json.dumps(match, separators=(",", ":")))
                for match in result["results"]
            ),
            100,
        )
        self.assertTrue(result["truncated"])

    @patch.object(better_grep.subprocess, "run")
    def test_no_matches(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="",
        )

        result = search("missing")

        self.assertEqual(result["results"], [])
        self.assertFalse(result["truncated"])

    @patch.object(better_grep.subprocess, "run")
    def test_rg_failure_raises(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=2,
            stdout="",
            stderr="invalid regex",
        )

        with self.assertRaises(RuntimeError):
            search("[")

    @patch.object(
        better_grep.subprocess,
        "run",
        side_effect=FileNotFoundError,
    )
    def test_missing_rg_raises(self, mock_run):
        with self.assertRaises(RuntimeError):
            search("test")

    def test_invalid_max_results(self):
        with self.assertRaises(ValueError):
            search("test", max_results=0)

    def test_invalid_max_output_chars(self):
        with self.assertRaises(ValueError):
            search("test", max_output_chars=0)


if __name__ == "__main__":
    unittest.main()