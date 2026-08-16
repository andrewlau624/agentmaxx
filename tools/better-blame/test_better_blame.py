#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE / "better_blame.py"

SPEC = importlib.util.spec_from_file_location(
    "better_blame",
    MODULE_PATH,
)

if SPEC is None or SPEC.loader is None:
    raise ImportError(
        f"Unable to load {MODULE_PATH}"
    )

better_blame = importlib.util.module_from_spec(SPEC)

sys.modules[SPEC.name] = better_blame

SPEC.loader.exec_module(better_blame)


class TestBlame(unittest.TestCase):

    @patch(
        "better_blame.run_git",
        return_value=(
            "abc123 1 1 1\n"
            "author Andrew Lau\n"
            "author-time 1720000000\n"
            "summary Add feature\n"
            "\tfirst line\n"
            "def456 2 2 1\n"
            "author Jane Doe\n"
            "author-time 1720000100\n"
            "summary Fix bug\n"
            "\tsecond line\n"
        ),
    )
    def test_blame_returns_compact_records(self, mock_run_git):
        records = better_blame.blame(
            "example.py"
        )

        self.assertEqual(len(records), 2)

        self.assertEqual(
            records[0]["line"],
            1,
        )

        self.assertEqual(
            records[0]["commit"],
            "abc123",
        )

        self.assertEqual(
            records[0]["author"],
            "Andrew Lau",
        )

        self.assertEqual(
            records[0]["summary"],
            "Add feature",
        )

        self.assertEqual(
            records[0]["content"],
            "first line",
        )

        mock_run_git.assert_called_once_with(
            [
                "blame",
                "--porcelain",
                "--",
                "example.py",
            ],
            cwd=None,
        )

    @patch(
        "better_blame.run_git",
        return_value=(
            "abc123 10 10 1\n"
            "author Andrew\n"
            "summary Test\n"
            "\tline 10\n"
            "abc123 11 11 1\n"
            "author Andrew\n"
            "summary Test\n"
            "\tline 11\n"
            "abc123 12 12 1\n"
            "author Andrew\n"
            "summary Test\n"
            "\tline 12\n"
        ),
    )
    def test_bounded_blame(self, mock_run_git):
        records = better_blame.blame(
            "example.py",
            start_line=10,
            end_line=12,
        )

        self.assertEqual(
            len(records),
            3,
        )

        mock_run_git.assert_called_once_with(
            [
                "blame",
                "--porcelain",
                "-L",
                "10,12",
                "--",
                "example.py",
            ],
            cwd=None,
        )

    @patch(
        "better_blame.run_git",
        return_value=(
            "abc123 4 4 1\n"
            "author Andrew\n"
            "summary Test\n"
            "\tline\n"
        ),
    )
    def test_revision_is_passed(self, mock_run_git):
        better_blame.blame(
            "example.py",
            revision="HEAD~2",
        )

        mock_run_git.assert_called_once_with(
            [
                "blame",
                "--porcelain",
                "HEAD~2",
                "--",
                "example.py",
            ],
            cwd=None,
        )


class TestBlameContext(unittest.TestCase):

    @patch(
        "better_blame.blame",
        return_value=[
            {
                "line": 8,
                "commit": "a",
                "author": "Andrew",
                "date": "",
                "summary": "",
                "content": "eight",
            },
            {
                "line": 9,
                "commit": "b",
                "author": "Andrew",
                "date": "",
                "summary": "",
                "content": "nine",
            },
            {
                "line": 10,
                "commit": "c",
                "author": "Andrew",
                "date": "",
                "summary": "",
                "content": "ten",
            },
            {
                "line": 11,
                "commit": "d",
                "author": "Andrew",
                "date": "",
                "summary": "",
                "content": "eleven",
            },
            {
                "line": 12,
                "commit": "e",
                "author": "Andrew",
                "date": "",
                "summary": "",
                "content": "twelve",
            },
        ],
    )
    def test_context(self, mock_blame):
        result = better_blame.blame_context(
            "example.py",
            10,
            context=2,
        )

        self.assertEqual(
            len(result),
            5,
        )

        mock_blame.assert_called_once_with(
            "example.py",
            revision=None,
            start_line=8,
            end_line=12,
            cwd=None,
        )


class TestCommitContext(unittest.TestCase):

    @patch(
        "better_blame.run_git",
        return_value=(
            "abc123\n"
            "Andrew Lau\n"
            "andrew@example.com\n"
            "2026-08-15T12:00:00-07:00\n"
            "Add better blame\n"
            " file.py | 10 +++++++---\n"
            " 1 file changed, 7 insertions(+), 3 deletions(-)\n"
        ),
    )
    def test_commit_context(self, mock_run_git):
        result = better_blame.commit_context(
            "abc123"
        )

        self.assertEqual(
            result["commit"],
            "abc123",
        )

        self.assertEqual(
            result["author"],
            "Andrew Lau",
        )

        self.assertEqual(
            result["email"],
            "andrew@example.com",
        )

        self.assertEqual(
            result["summary"],
            "Add better blame",
        )

        self.assertIn(
            "file.py",
            result["stat"],
        )

        mock_run_git.assert_called_once_with(
            [
                "show",
                "--no-renames",
                "--format=%H%n%an%n%ae%n%aI%n%s",
                "--stat",
                "abc123",
            ],
            cwd=None,
        )


class TestValidation(unittest.TestCase):

    def test_invalid_start_line(self):
        with self.assertRaises(ValueError):
            better_blame.blame(
                "file.py",
                start_line=0,
            )

    def test_invalid_end_line(self):
        with self.assertRaises(ValueError):
            better_blame.blame(
                "file.py",
                end_line=0,
            )

    def test_invalid_range(self):
        with self.assertRaises(ValueError):
            better_blame.blame(
                "file.py",
                start_line=10,
                end_line=5,
            )

    def test_invalid_max_lines(self):
        with self.assertRaises(ValueError):
            better_blame.blame(
                "file.py",
                max_lines=0,
            )

    def test_invalid_context(self):
        with self.assertRaises(ValueError):
            better_blame.blame_context(
                "file.py",
                10,
                context=-1,
            )

    def test_invalid_context_line(self):
        with self.assertRaises(ValueError):
            better_blame.blame_context(
                "file.py",
                0,
            )


class TestFormatting(unittest.TestCase):

    def test_format_empty_records(self):
        self.assertEqual(
            better_blame.format_records([]),
            "",
        )

    def test_format_records(self):
        records = [
            {
                "line": 1,
                "commit": "1234567890abcdef",
                "author": "Andrew",
                "date": "2026-08-15",
                "content": "hello",
            }
        ]

        result = better_blame.format_records(
            records
        )

        self.assertIn(
            "1234567890",
            result,
        )

        self.assertIn(
            "Andrew",
            result,
        )

        self.assertIn(
            "hello",
            result,
        )


class TestRealGitRepository(unittest.TestCase):

    def test_blame_real_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            subprocess.run(
                ["git", "init"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            subprocess.run(
                [
                    "git",
                    "config",
                    "user.name",
                    "Test User",
                ],
                cwd=root,
                check=True,
            )

            subprocess.run(
                [
                    "git",
                    "config",
                    "user.email",
                    "test@example.com",
                ],
                cwd=root,
                check=True,
            )

            target = root / "example.py"

            target.write_text(
                "one\n"
                "two\n"
                "three\n",
                encoding="utf-8",
            )

            subprocess.run(
                ["git", "add", "example.py"],
                cwd=root,
                check=True,
            )

            subprocess.run(
                [
                    "git",
                    "commit",
                    "-m",
                    "Initial commit",
                ],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            records = better_blame.blame(
                "example.py",
                cwd=root,
            )

            self.assertEqual(
                len(records),
                3,
            )

            self.assertEqual(
                records[0]["author"],
                "Test User",
            )

            self.assertEqual(
                records[0]["content"],
                "one",
            )


class TestMain(unittest.TestCase):

    @patch(
        "better_blame.blame",
        return_value=[
            {
                "line": 1,
                "commit": "abcdef123456",
                "author": "Andrew",
                "date": "2026",
                "summary": "Test",
                "content": "hello",
            }
        ],
    )
    def test_main(self, mock_blame):
        result = better_blame.main(
            ["example.py"]
        )

        self.assertEqual(
            result,
            0,
        )

        mock_blame.assert_called_once_with(
            "example.py",
            revision=None,
            start_line=None,
            end_line=None,
            max_lines=None,
        )


if __name__ == "__main__":
    unittest.main()