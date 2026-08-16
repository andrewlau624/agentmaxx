import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

path = Path(__file__).with_name("better_test.py")
spec = importlib.util.spec_from_file_location(
    "better_test_impl",
    path,
)
better_test = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_test)


class TestBetterTest(unittest.TestCase):

    @patch.object(better_test.subprocess, "run")
    def test_run_command_success(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=0,
            stdout="10 passed",
            stderr="",
        )

        code, output, timed_out = better_test.run_command(
            ["pytest"]
        )

        self.assertEqual(code, 0)
        self.assertEqual(output, "10 passed")
        self.assertFalse(timed_out)

    @patch.object(better_test.subprocess, "run")
    def test_run_command_combines_stdout_and_stderr(self, mock_run):
        mock_run.return_value = subprocess.CompletedProcess(
            args=["pytest"],
            returncode=1,
            stdout="stdout",
            stderr="stderr",
        )

        code, output, timed_out = better_test.run_command(
            ["pytest"]
        )

        self.assertEqual(code, 1)
        self.assertEqual(
            output,
            "stdout\nstderr",
        )
        self.assertFalse(timed_out)

    @patch.object(
        better_test.subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(
            cmd=["pytest"],
            timeout=10,
            output="partial output",
            stderr="partial error",
        ),
    )
    def test_run_command_timeout(self, mock_run):
        code, output, timed_out = better_test.run_command(
            ["pytest"],
            timeout=10,
        )

        self.assertEqual(code, 124)
        self.assertIn(
            "partial output",
            output,
        )
        self.assertIn(
            "partial error",
            output,
        )
        self.assertTrue(timed_out)

    def test_truncate_output_does_not_change_small_output(self):
        output = "hello world"

        result, truncated = better_test.truncate_output(
            output,
            100,
        )

        self.assertEqual(result, output)
        self.assertFalse(truncated)

    def test_truncate_output_bounds_large_output(self):
        output = "a" * 1000

        result, truncated = better_test.truncate_output(
            output,
            100,
        )

        self.assertTrue(truncated)
        self.assertIn(
            "OUTPUT TRUNCATED",
            result,
        )
        self.assertLess(
            len(result),
            len(output),
        )

    def test_truncate_output_invalid_limit(self):
        with self.assertRaises(ValueError):
            better_test.truncate_output(
                "hello",
                0,
            )

    @patch.object(better_test.Path, "cwd")
    @patch.object(better_test.subprocess, "run")
    def test_detect_framework_pytest(
        self,
        mock_run,
        mock_cwd,
    ):
        root = mock_cwd.return_value

        def exists(path):
            return str(path) == "pyproject.toml"

        root.__truediv__.side_effect = (
            lambda name: type(
                "FakePath",
                (),
                {
                    "exists": lambda self: (
                        name == "pyproject.toml"
                    )
                },
            )()
        )

        mock_run.return_value = subprocess.CompletedProcess(
            args=["python", "-m", "pytest", "--version"],
            returncode=0,
            stdout="pytest 8.0.0",
            stderr="",
        )

        result = better_test.detect_framework()

        self.assertEqual(
            result,
            "pytest",
        )

    def test_default_command_pytest(self):
        self.assertEqual(
            better_test.default_command("pytest"),
            [
                "python",
                "-m",
                "pytest",
            ],
        )

    def test_default_command_unittest(self):
        self.assertEqual(
            better_test.default_command("unittest"),
            [
                "python",
                "-m",
                "unittest",
                "discover",
            ],
        )

    def test_default_command_npm(self):
        self.assertEqual(
            better_test.default_command("npm"),
            [
                "npm",
                "test",
                "--",
                "--runInBand",
            ],
        )

    def test_default_command_unknown(self):
        with self.assertRaises(RuntimeError):
            better_test.default_command("unknown")

    def test_parse_pytest_passed(self):
        output = """
============================= test session starts =============================
collected 12 items

tests/test_one.py ............
12 passed in 0.42s
"""

        result = better_test.parse_pytest(output)

        self.assertEqual(
            result["framework"],
            "pytest",
        )
        self.assertEqual(
            result["passed"],
            12,
        )
        self.assertEqual(
            result["failed"],
            0,
        )
        self.assertEqual(
            result["errors"],
            0,
        )

    def test_parse_pytest_mixed_results(self):
        output = """
8 passed, 2 failed, 1 skipped, 1 error in 1.23s
"""

        result = better_test.parse_pytest(output)

        self.assertEqual(
            result["passed"],
            8,
        )
        self.assertEqual(
            result["failed"],
            2,
        )
        self.assertEqual(
            result["skipped"],
            1,
        )
        self.assertEqual(
            result["errors"],
            1,
        )

    def test_parse_pytest_failures(self):
        output = """
FAILED tests/test_auth.py::test_login
FAILED tests/test_user.py::test_create
2 failed, 5 passed in 0.5s
"""

        result = better_test.parse_pytest(output)

        self.assertEqual(
            result["failed"],
            2,
        )
        self.assertEqual(
            len(result["failures"]),
            2,
        )

        self.assertIn(
            "test_login",
            result["failures"][0],
        )

    def test_parse_unittest_clean(self):
        output = """
..........
----------------------------------------------------------------------
Ran 10 tests in 0.012s

OK
"""

        result = better_test.parse_unittest(output)

        self.assertEqual(
            result["framework"],
            "unittest",
        )
        self.assertEqual(
            result["passed"],
            10,
        )
        self.assertEqual(
            result["failed"],
            0,
        )
        self.assertEqual(
            result["errors"],
            0,
        )

    def test_parse_unittest_failures(self):
        output = """
.F.E
======================================================================
FAIL: test_one (test_example.TestExample)
----------------------------------------------------------------------
Traceback (most recent call last):
AssertionError

======================================================================
ERROR: test_two (test_example.TestExample)
----------------------------------------------------------------------
Traceback (most recent call last):
RuntimeError

----------------------------------------------------------------------
Ran 4 tests in 0.01s

FAILED (failures=1, errors=1)
"""

        result = better_test.parse_unittest(output)

        self.assertEqual(
            result["passed"],
            2,
        )
        self.assertEqual(
            result["failed"],
            1,
        )
        self.assertEqual(
            result["errors"],
            1,
        )
        self.assertEqual(
            len(result["failures"]),
            2,
        )

    def test_parse_unittest_skipped(self):
        output = """
.s..
----------------------------------------------------------------------
Ran 4 tests in 0.01s

OK (skipped=1)
"""

        result = better_test.parse_unittest(output)

        self.assertEqual(
            result["passed"],
            3,
        )
        self.assertEqual(
            result["skipped"],
            1,
        )

    def test_parse_npm_passing(self):
        output = """
  15 passing (2s)
"""

        result = better_test.parse_npm(output)

        self.assertEqual(
            result["framework"],
            "npm",
        )
        self.assertEqual(
            result["passed"],
            15,
        )
        self.assertEqual(
            result["failed"],
            0,
        )

    def test_parse_npm_failing(self):
        output = """
  10 passing
  2 failing
"""

        result = better_test.parse_npm(output)

        self.assertEqual(
            result["passed"],
            10,
        )
        self.assertEqual(
            result["failed"],
            2,
        )

    def test_parse_npm_failure_lines(self):
        output = """
  5 passing
  1 failing

  1) authentication
  2) user creation
"""

        result = better_test.parse_npm(output)

        self.assertEqual(
            result["failed"],
            1,
        )

    def test_parse_results_pytest(self):
        output = "5 passed"

        result = better_test.parse_results(
            "pytest",
            output,
        )

        self.assertEqual(
            result["passed"],
            5,
        )

    def test_parse_results_unittest(self):
        output = """
.....
Ran 5 tests in 0.01s

OK
"""

        result = better_test.parse_results(
            "unittest",
            output,
        )

        self.assertEqual(
            result["passed"],
            5,
        )

    def test_parse_results_unknown(self):
        result = better_test.parse_results(
            "unknown",
            "whatever",
        )

        self.assertEqual(
            result["framework"],
            "unknown",
        )
        self.assertEqual(
            result["passed"],
            0,
        )
        self.assertEqual(
            result["failed"],
            0,
        )

    def test_extract_failure_context(self):
        output = """
test output

FAIL: test_login

Traceback (most recent call last):
AssertionError: expected 1 got 2

some unrelated output

ERROR: test_database

Traceback (most recent call last):
RuntimeError: database failed
"""

        failures = better_test.extract_failure_context(
            output
        )

        self.assertEqual(
            len(failures),
            2,
        )

        self.assertIn(
            "test_login",
            failures[0],
        )

        self.assertIn(
            "database",
            failures[1],
        )

    @patch.object(
        better_test,
        "detect_framework",
        return_value="unittest",
    )
    @patch.object(
        better_test,
        "run_command",
    )
    def test_test_success(
        self,
        mock_run,
        mock_framework,
    ):
        mock_run.return_value = (
            0,
            """
..........
----------------------------------------------------------------------
Ran 10 tests in 0.01s

OK
""",
            False,
        )

        result = better_test.test()

        self.assertTrue(
            result["passed"]
        )
        self.assertEqual(
            result["exit_code"],
            0,
        )
        self.assertFalse(
            result["timed_out"]
        )
        self.assertEqual(
            result["results"]["passed"],
            10,
        )

    @patch.object(
        better_test,
        "run_command",
    )
    def test_test_failure(self, mock_run):
        mock_run.return_value = (
            1,
            """
.F
======================================================================
FAIL: test_bad (test_example.TestExample)
----------------------------------------------------------------------
Traceback (most recent call last):
AssertionError

----------------------------------------------------------------------
Ran 2 tests in 0.01s

FAILED (failures=1)
""",
            False,
        )

        result = better_test.test(
            command=[
                "python",
                "-m",
                "unittest",
            ],
            framework="unittest",
        )

        self.assertFalse(
            result["passed"]
        )
        self.assertEqual(
            result["exit_code"],
            1,
        )
        self.assertEqual(
            result["results"]["failed"],
            1,
        )
        self.assertTrue(
            result["failures"]
        )

    @patch.object(
        better_test,
        "run_command",
    )
    def test_test_timeout(self, mock_run):
        mock_run.return_value = (
            124,
            "test command timed out",
            True,
        )

        result = better_test.test(
            command=["pytest"],
            framework="pytest",
        )

        self.assertFalse(
            result["passed"]
        )
        self.assertEqual(
            result["exit_code"],
            124,
        )
        self.assertTrue(
            result["timed_out"]
        )

    @patch.object(
        better_test,
        "run_command",
    )
    def test_test_output_is_bounded(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            1,
            "x" * 10000,
            False,
        )

        result = better_test.test(
            command=["pytest"],
            framework="pytest",
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
        better_test,
        "run_command",
    )
    def test_test_custom_command(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            0,
            "5 passed",
            False,
        )

        command = [
            "python",
            "-m",
            "pytest",
            "tests/test_auth.py",
        ]

        result = better_test.test(
            command=command,
            framework="pytest",
        )

        self.assertEqual(
            result["command"],
            command,
        )

        mock_run.assert_called_once_with(
            command,
            timeout=better_test.DEFAULT_TIMEOUT,
        )

    @patch.object(
        better_test,
        "test",
    )
    @patch(
        "builtins.print",
    )
    def test_main_success(
        self,
        mock_print,
        mock_test,
    ):
        mock_test.return_value = {
            "command": ["pytest"],
            "framework": "pytest",
            "passed": True,
            "exit_code": 0,
            "timed_out": False,
            "results": {
                "framework": "pytest",
                "passed": 5,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "failures": [],
            },
            "failures": [],
            "output": "5 passed",
            "output_truncated": False,
        }

        with patch(
            "sys.argv",
            ["better-test"],
        ):
            with self.assertRaises(SystemExit) as exc:
                better_test.main()

        self.assertEqual(
            exc.exception.code,
            0,
        )

        mock_print.assert_called_once()

        printed = mock_print.call_args[0][0]
        parsed = json.loads(printed)

        self.assertTrue(
            parsed["passed"]
        )

    @patch.object(
        better_test,
        "test",
    )
    @patch(
        "builtins.print",
    )
    def test_main_failure(
        self,
        mock_print,
        mock_test,
    ):
        mock_test.return_value = {
            "command": ["pytest"],
            "framework": "pytest",
            "passed": False,
            "exit_code": 1,
            "timed_out": False,
            "results": {
                "framework": "pytest",
                "passed": 4,
                "failed": 1,
                "errors": 0,
                "skipped": 0,
                "failures": [
                    "FAILED tests/test_auth.py::test_login"
                ],
            },
            "failures": [
                "FAILED tests/test_auth.py::test_login"
            ],
            "output": "1 failed",
            "output_truncated": False,
        }

        with patch(
            "sys.argv",
            ["better-test"],
        ):
            with self.assertRaises(SystemExit) as exc:
                better_test.main()

        self.assertEqual(
            exc.exception.code,
            1,
        )

    @patch.object(
        better_test,
        "test",
    )
    @patch(
        "builtins.print",
    )
    def test_main_quiet(
        self,
        mock_print,
        mock_test,
    ):
        mock_test.return_value = {
            "command": ["pytest"],
            "framework": "pytest",
            "passed": True,
            "exit_code": 0,
            "timed_out": False,
            "results": {
                "framework": "pytest",
                "passed": 5,
                "failed": 0,
                "errors": 0,
                "skipped": 0,
                "failures": [],
            },
            "failures": [],
            "output": "5 passed",
            "output_truncated": False,
        }

        with patch(
            "sys.argv",
            [
                "better-test",
                "--quiet",
            ],
        ):
            with self.assertRaises(SystemExit) as exc:
                better_test.main()

        self.assertEqual(
            exc.exception.code,
            0,
        )

        printed = mock_print.call_args[0][0]
        parsed = json.loads(printed)

        self.assertNotIn(
            "output",
            parsed,
        )
        self.assertNotIn(
            "failures",
            parsed,
        )


if __name__ == "__main__":
    unittest.main()