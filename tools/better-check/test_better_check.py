import importlib.util
import json
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch


path = Path(__file__).with_name(
    "better_check.py"
)

spec = importlib.util.spec_from_file_location(
    "better_check_impl",
    path,
)

better_check = importlib.util.module_from_spec(
    spec
)

assert spec.loader
spec.loader.exec_module(
    better_check
)


class TestBetterCheck(unittest.TestCase):

    @patch.object(
        better_check.subprocess,
        "run",
    )
    def test_run_command_success(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            subprocess.CompletedProcess(
                args=["pytest"],
                returncode=0,
                stdout="10 passed",
                stderr="",
            )
        )

        code, output, timed_out = (
            better_check.run_command(
                ["pytest"]
            )
        )

        self.assertEqual(
            code,
            0,
        )

        self.assertEqual(
            output,
            "10 passed",
        )

        self.assertFalse(
            timed_out
        )

    @patch.object(
        better_check.subprocess,
        "run",
    )
    def test_run_command_failure(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            subprocess.CompletedProcess(
                args=["pytest"],
                returncode=1,
                stdout="2 failed",
                stderr="",
            )
        )

        code, output, timed_out = (
            better_check.run_command(
                ["pytest"]
            )
        )

        self.assertEqual(
            code,
            1,
        )

        self.assertEqual(
            output,
            "2 failed",
        )

        self.assertFalse(
            timed_out
        )

    @patch.object(
        better_check.subprocess,
        "run",
        side_effect=subprocess.TimeoutExpired(
            cmd=["pytest"],
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
            better_check.run_command(
                ["pytest"],
                timeout=10,
            )
        )

        self.assertEqual(
            code,
            124,
        )

        self.assertTrue(
            timed_out
        )

        self.assertIn(
            "timed out",
            output,
        )

    def test_truncate_output_small(self):
        output, truncated = (
            better_check.truncate_output(
                "hello",
                100,
            )
        )

        self.assertEqual(
            output,
            "hello",
        )

        self.assertFalse(
            truncated
        )

    def test_truncate_output_large(self):
        output, truncated = (
            better_check.truncate_output(
                "x" * 1000,
                100,
            )
        )

        self.assertTrue(
            truncated
        )

        self.assertIn(
            "OUTPUT TRUNCATED",
            output,
        )

        self.assertLessEqual(
            len(output),
            100,
        )

    def test_detect_project_python(self):
        with patch.object(
            better_check.Path,
            "cwd",
            return_value=Path("."),
        ):
            with patch.object(
                better_check.Path,
                "exists",
                return_value=True,
            ):
                result = (
                    better_check.detect_project()
                )

        self.assertIn(
            "python",
            result
        )

    @patch.object(
        better_check,
        "detect_project",
        return_value={
            "python": True,
            "javascript": False,
            "typescript": False,
            "rust": False,
            "go": False,
        },
    )
    @patch.object(
        better_check,
        "command_exists",
        return_value=True,
    )
    def test_detect_python_test_command(
        self,
        mock_exists,
        mock_project,
    ):
        command = (
            better_check.detect_test_command()
        )

        self.assertEqual(
            command,
            [
                "pytest",
            ],
        )

    @patch.object(
        better_check,
        "detect_project",
        return_value={
            "python": True,
            "javascript": False,
            "typescript": False,
            "rust": False,
            "go": False,
        },
    )
    @patch.object(
        better_check,
        "command_exists",
        side_effect=lambda command: (
            command == "ruff"
        ),
    )
    def test_detect_python_lint_command(
        self,
        mock_exists,
        mock_project,
    ):
        command = (
            better_check.detect_lint_command()
        )

        self.assertEqual(
            command,
            [
                "ruff",
                "check",
                ".",
            ],
        )

    @patch.object(
        better_check,
        "detect_project",
        return_value={
            "python": True,
            "javascript": False,
            "typescript": False,
            "rust": False,
            "go": False,
        },
    )
    @patch.object(
        better_check,
        "command_exists",
        side_effect=lambda command: (
            command == "mypy"
        ),
    )
    def test_detect_python_typecheck(
        self,
        mock_exists,
        mock_project,
    ):
        command = (
            better_check.detect_typecheck_command()
        )

        self.assertEqual(
            command,
            [
                "mypy",
                ".",
            ],
        )

    @patch.object(
        better_check,
        "detect_project",
        return_value={
            "python": False,
            "javascript": True,
            "typescript": False,
            "rust": False,
            "go": False,
        },
    )
    @patch.object(
        better_check,
        "command_exists",
        side_effect=lambda command: (
            command == "eslint"
        ),
    )
    def test_detect_javascript_lint(
        self,
        mock_exists,
        mock_project,
    ):
        command = (
            better_check.detect_lint_command()
        )

        self.assertEqual(
            command,
            [
                "eslint",
                ".",
            ],
        )

    @patch.object(
        better_check,
        "detect_project",
        return_value={
            "python": False,
            "javascript": False,
            "typescript": True,
            "rust": False,
            "go": False,
        },
    )
    @patch.object(
        better_check,
        "command_exists",
        side_effect=lambda command: (
            command == "tsc"
        ),
    )
    def test_detect_typescript_typecheck(
        self,
        mock_exists,
        mock_project,
    ):
        command = (
            better_check.detect_typecheck_command()
        )

        self.assertEqual(
            command,
            [
                "tsc",
                "--noEmit",
            ],
        )

    @patch.object(
        better_check,
        "detect_project",
        return_value={
            "python": False,
            "javascript": False,
            "typescript": False,
            "rust": True,
            "go": False,
        },
    )
    @patch.object(
        better_check,
        "command_exists",
        return_value=True,
    )
    def test_detect_rust_build(
        self,
        mock_exists,
        mock_project,
    ):
        command = (
            better_check.detect_build_command()
        )

        self.assertEqual(
            command,
            [
                "cargo",
                "build",
            ],
        )

    @patch.object(
        better_check,
        "run_command",
    )
    def test_run_check_passed(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            0,
            "passed",
            False,
        )

        result = better_check.run_check(
            "test",
            ["pytest"],
            60,
            1000,
        )

        self.assertTrue(
            result["available"]
        )

        self.assertTrue(
            result["passed"]
        )

        self.assertFalse(
            result["skipped"]
        )

        self.assertEqual(
            result["exit_code"],
            0,
        )

    @patch.object(
        better_check,
        "run_command",
    )
    def test_run_check_failed(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            1,
            "failed",
            False,
        )

        result = better_check.run_check(
            "test",
            ["pytest"],
            60,
            1000,
        )

        self.assertFalse(
            result["passed"]
        )

        self.assertFalse(
            result["skipped"]
        )

        self.assertEqual(
            result["exit_code"],
            1,
        )

    def test_run_check_skipped(self):
        result = better_check.run_check(
            "build",
            None,
            60,
            1000,
        )

        self.assertFalse(
            result["available"]
        )

        self.assertTrue(
            result["passed"]
        )

        self.assertTrue(
            result["skipped"]
        )

        self.assertIsNone(
            result["exit_code"]
        )

    @patch.object(
        better_check,
        "run_command",
    )
    def test_check_all_pass(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            0,
            "passed",
            False,
        )

        result = better_check.check(
            test_command=["pytest"],
            lint_command=["ruff"],
            typecheck_command=["mypy"],
            build_command=["make", "build"],
        )

        self.assertTrue(
            result["passed"]
        )

        self.assertEqual(
            result["failed"],
            [],
        )

        self.assertEqual(
            result["skipped"],
            [],
        )

        self.assertEqual(
            len(result["checks"]),
            4,
        )

        self.assertEqual(
            mock_run.call_count,
            4,
        )

    @patch.object(
        better_check,
        "run_command",
        side_effect=[
            (0, "tests passed", False),
            (1, "lint failed", False),
            (0, "typecheck passed", False),
            (0, "build passed", False),
        ],
    )
    def test_check_failure(
        self,
        mock_run,
    ):
        result = better_check.check(
            test_command=["pytest"],
            lint_command=["ruff"],
            typecheck_command=["mypy"],
            build_command=["make"],
        )

        self.assertFalse(
            result["passed"]
        )

        self.assertEqual(
            result["failed"],
            ["lint"],
        )

        self.assertEqual(
            len(result["checks"]),
            4,
        )

    @patch.object(
        better_check,
        "run_command",
        side_effect=[
            (1, "tests failed", False),
            (0, "lint passed", False),
            (0, "typecheck passed", False),
            (0, "build passed", False),
        ],
    )
    def test_stop_on_failure(
        self,
        mock_run,
    ):
        result = better_check.check(
            test_command=["pytest"],
            lint_command=["ruff"],
            typecheck_command=["mypy"],
            build_command=["make"],
            stop_on_failure=True,
        )

        self.assertFalse(
            result["passed"]
        )

        self.assertEqual(
            result["failed"],
            ["test"],
        )

        self.assertEqual(
            len(result["checks"]),
            1,
        )

        self.assertEqual(
            mock_run.call_count,
            1,
        )

    @patch.object(
        better_check,
        "run_command",
        return_value=(
            0,
            "x" * 10000,
            False,
        ),
    )
    def test_check_output_is_bounded(
        self,
        mock_run,
    ):
        result = better_check.check(
            test_command=["pytest"],
            lint_command=None,
            typecheck_command=None,
            build_command=None,
            max_output=100,
        )

        check_result = (
            result["checks"][0]
        )

        self.assertTrue(
            check_result[
                "output_truncated"
            ]
        )

        self.assertLessEqual(
            len(check_result["output"]),
            100,
        )

    @patch.object(
        better_check,
        "run_command",
    )
    def test_check_custom_commands(
        self,
        mock_run,
    ):
        mock_run.return_value = (
            0,
            "",
            False,
        )

        result = better_check.check(
            test_command=[
                "python",
                "-m",
                "unittest",
            ],
            lint_command=[
                "ruff",
                "check",
                ".",
            ],
            typecheck_command=[
                "mypy",
                ".",
            ],
            build_command=[
                "make",
                "build",
            ],
        )

        self.assertTrue(
            result["passed"]
        )

        calls = [
            call.args[0]
            for call in mock_run.call_args_list
        ]

        self.assertEqual(
            calls[0],
            [
                "python",
                "-m",
                "unittest",
            ],
        )

        self.assertEqual(
            calls[1],
            [
                "ruff",
                "check",
                ".",
            ],
        )

        self.assertEqual(
            calls[2],
            [
                "mypy",
                ".",
            ],
        )

        self.assertEqual(
            calls[3],
            [
                "make",
                "build",
            ],
        )


if __name__ == "__main__":
    unittest.main()