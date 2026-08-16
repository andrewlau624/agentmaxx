import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).with_name(
    "better_lint.py"
)

spec = importlib.util.spec_from_file_location(
    "better_lint_impl",
    path,
)

better_lint = importlib.util.module_from_spec(
    spec
)

assert spec.loader
spec.loader.exec_module(
    better_lint
)


class TestBetterLint(unittest.TestCase):

    @patch.object(
        better_lint.subprocess,
        "run",
    )
    def test_run_command_success(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            subprocess.CompletedProcess(
                args=["ruff", "check", "."],
                returncode=0,
                stdout="",
                stderr="",
            )
        )

        code, output, timed_out = (
            better_lint.run_command(
                ["ruff", "check", "."]
            )
        )

        self.assertEqual(code, 0)
        self.assertEqual(output, "")
        self.assertFalse(timed_out)

    @patch.object(
        better_lint.subprocess,
        "run",
    )
    def test_run_command_failure(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            subprocess.CompletedProcess(
                args=["ruff", "check", "."],
                returncode=1,
                stdout="foo.py:1:1: E501 line too long",
                stderr="",
            )
        )

        code, output, timed_out = (
            better_lint.run_command(
                ["ruff", "check", "."]
            )
        )

        self.assertEqual(code, 1)
        self.assertIn(
            "E501",
            output,
        )
        self.assertFalse(timed_out)

    @patch.object(
        better_lint.subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(
            cmd=["ruff"],
            timeout=10,
            output="partial",
            stderr="error",
        ),
    )
    def test_run_command_timeout(
        self,
        mock_run,
    ):
        code, output, timed_out = (
            better_lint.run_command(
                ["ruff"],
                timeout=10,
            )
        )

        self.assertEqual(code, 124)
        self.assertTrue(timed_out)
        self.assertIn(
            "timed out",
            output,
        )

    def test_truncate_small_output(self):
        output, truncated = (
            better_lint.truncate_output(
                "hello",
                100,
            )
        )

        self.assertEqual(
            output,
            "hello",
        )
        self.assertFalse(truncated)

    def test_truncate_large_output(self):
        output, truncated = (
            better_lint.truncate_output(
                "x" * 1000,
                100,
            )
        )

        self.assertTrue(truncated)
        self.assertIn(
            "OUTPUT TRUNCATED",
            output,
        )
        self.assertLess(
            len(output),
            1000,
        )

    def test_parse_location_with_column(self):
        result = better_lint.parse_location(
            "foo.py:10:5: E501 line too long"
        )

        self.assertEqual(
            result["file"],
            "foo.py",
        )
        self.assertEqual(
            result["line"],
            10,
        )
        self.assertEqual(
            result["column"],
            5,
        )
        self.assertEqual(
            result["message"],
            "E501 line too long",
        )

    def test_parse_location_without_column(self):
        result = better_lint.parse_location(
            "foo.py:10: error"
        )

        self.assertEqual(
            result["file"],
            "foo.py",
        )
        self.assertEqual(
            result["line"],
            10,
        )

    def test_parse_location_parentheses(self):
        result = better_lint.parse_location(
            "foo.py(10,5): error"
        )

        self.assertEqual(
            result["file"],
            "foo.py",
        )
        self.assertEqual(
            result["line"],
            10,
        )
        self.assertEqual(
            result["column"],
            5,
        )

    def test_parse_location_invalid(self):
        result = better_lint.parse_location(
            "this is not an error"
        )

        self.assertIsNone(result)

    def test_parse_ruff(self):
        output = """
foo.py:10:5: E501 line too long
bar.py:20:1: F401 unused import
"""

        result = better_lint.parse_ruff(
            output
        )

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[0]["file"],
            "foo.py",
        )
        self.assertEqual(
            result[0]["code"],
            "E501",
        )
        self.assertEqual(
            result[0]["line"],
            10,
        )

    def test_parse_flake8(self):
        output = """
foo.py:3:1: F401 unused import
foo.py:8:5: E501 line too long
"""

        result = better_lint.parse_flake8(
            output
        )

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[1]["code"],
            "E501",
        )

    def test_parse_eslint(self):
        output = """
src/app.js:10:4: no-unused-vars
src/main.js:20:2: semi
"""

        result = better_lint.parse_eslint(
            output
        )

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[0]["file"],
            "src/app.js",
        )

    def test_parse_errors_ruff(self):
        output = (
            "foo.py:1:1: E501 too long"
        )

        result = better_lint.parse_errors(
            "ruff",
            output,
        )

        self.assertEqual(
            len(result),
            1,
        )

    def test_parse_errors_generic(self):
        output = (
            "foo.py:4:2: some error"
        )

        result = better_lint.parse_errors(
            "pylint",
            output,
        )

        self.assertEqual(
            len(result),
            1,
        )

    def test_default_command_ruff(self):
        self.assertEqual(
            better_lint.default_command(
                "ruff"
            ),
            [
                "ruff",
                "check",
                ".",
            ],
        )

    def test_default_command_flake8(self):
        self.assertEqual(
            better_lint.default_command(
                "flake8"
            ),
            [
                "flake8",
                ".",
            ],
        )

    def test_default_command_eslint(self):
        self.assertEqual(
            better_lint.default_command(
                "eslint"
            ),
            [
                "eslint",
                ".",
            ],
        )

    def test_default_command_clippy(self):
        self.assertEqual(
            better_lint.default_command(
                "clippy"
            ),
            [
                "cargo",
                "clippy",
                "--all-targets",
                "--all-features",
            ],
        )

    def test_default_command_unknown(self):
        with self.assertRaises(
            RuntimeError
        ):
            better_lint.default_command(
                "unknown"
            )

    @patch.object(
        better_lint,
        "run_command",
    )
    def test_lint_success(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            0,
            "",
            False,
        )

        result = better_lint.lint(
            command=[
                "ruff",
                "check",
                ".",
            ],
            linter="ruff",
        )

        self.assertTrue(
            result["passed"]
        )
        self.assertEqual(
            result["exit_code"],
            0,
        )
        self.assertEqual(
            result["error_count"],
            0,
        )

    @patch.object(
        better_lint,
        "run_command",
    )
    def test_lint_failure(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            1,
            "foo.py:10:5: E501 line too long",
            False,
        )

        result = better_lint.lint(
            command=[
                "ruff",
                "check",
                ".",
            ],
            linter="ruff",
        )

        self.assertFalse(
            result["passed"]
        )
        self.assertEqual(
            result["exit_code"],
            1,
        )
        self.assertEqual(
            result["error_count"],
            1,
        )
        self.assertEqual(
            result["errors"][0]["code"],
            "E501",
        )

    @patch.object(
        better_lint,
        "run_command",
    )
    def test_lint_timeout(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            124,
            "lint command timed out",
            True,
        )

        result = better_lint.lint(
            command=["ruff"],
            linter="ruff",
        )

        self.assertFalse(
            result["passed"]
        )
        self.assertTrue(
            result["timed_out"]
        )
        self.assertEqual(
            result["exit_code"],
            124,
        )

    @patch.object(
        better_lint,
        "run_command",
    )
    def test_lint_output_is_bounded(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            1,
            "x" * 10000,
            False,
        )

        result = better_lint.lint(
            command=["ruff"],
            linter="ruff",
            max_output=100,
        )

        self.assertTrue(
            result["output_truncated"]
        )
        self.assertIn(
            "OUTPUT TRUNCATED",
            result["output"],
        )

    @patch.object(
        better_lint,
        "detect_linter",
        return_value="ruff",
    )
    @patch.object(
        better_lint,
        "run_command",
    )
    def test_lint_auto_detect(
        self,
        mock_run,
        mock_detect,
    ):
        mock_run.return_value = (
            0,
            "",
            False,
        )

        result = better_lint.lint()

        self.assertEqual(
            result["linter"],
            "ruff",
        )

        self.assertEqual(
            result["command"],
            [
                "ruff",
                "check",
                ".",
            ],
        )

    @patch.object(
        better_lint,
        "lint",
    )
    @patch(
        "builtins.print",
    )
    def test_main_success(
        self,
        mock_print,
        mock_lint,
    ):
        mock_lint.return_value = {
            "linter": "ruff",
            "command": [
                "ruff",
                "check",
                ".",
            ],
            "passed": True,
            "exit_code": 0,
            "timed_out": False,
            "error_count": 0,
            "errors": [],
            "output": "",
            "output_truncated": False,
        }

        with patch(
            "sys.argv",
            ["better-lint"],
        ):
            better_lint.main()

        mock_print.assert_called_once()

        output = json.loads(
            mock_print.call_args[0][0]
        )

        self.assertTrue(
            output["passed"]
        )

    @patch.object(
        better_lint,
        "lint",
    )
    @patch(
        "builtins.print",
    )
    def test_main_quiet(
        self,
        mock_print,
        mock_lint,
    ):
        mock_lint.return_value = {
            "linter": "ruff",
            "command": [
                "ruff",
                "check",
                ".",
            ],
            "passed": True,
            "exit_code": 0,
            "timed_out": False,
            "error_count": 0,
            "errors": [],
            "output": "",
            "output_truncated": False,
        }

        with patch(
            "sys.argv",
            [
                "better-lint",
                "--quiet",
            ],
        ):
            better_lint.main()

        output = json.loads(
            mock_print.call_args[0][0]
        )

        self.assertNotIn(
            "output",
            output,
        )


if __name__ == "__main__":
    unittest.main()