#!/usr/bin/env python3

import importlib.util
import unittest
from pathlib import Path
from unittest.mock import patch


path = Path(__file__).with_name("better_git.py")

spec = importlib.util.spec_from_file_location(
    "better_git",
    path,
)

better_git = importlib.util.module_from_spec(spec)

assert spec.loader
spec.loader.exec_module(better_git)


branch = better_git.branch
branch_context = better_git.branch_context
changed = better_git.changed
check = better_git.check
commit_context = better_git.commit_context
conflicts = better_git.conflicts
context = better_git.context
diff = better_git.diff
diff_summary = better_git.diff_summary
fix_context = better_git.fix_context
inspect_path = better_git.inspect_path
is_rebasing = better_git.is_rebasing
log_path = better_git.log_path
merge_context = better_git.merge_context
parse_commits = better_git.parse_commits
parse_numstat = better_git.parse_numstat
pr_context = better_git.pr_context
recent = better_git.recent
rebase_context = better_git.rebase_context
remote_context = better_git.remote_context
remotes = better_git.remotes
review = better_git.review
review_branch = better_git.review_branch
show = better_git.show
ship_context = better_git.ship_context
stash_context = better_git.stash_context
stash_list = better_git.stash_list
status = better_git.status
tag_context = better_git.tag_context
tags = better_git.tags
verify_context = better_git.verify_context


class TestParsing(unittest.TestCase):

    def test_parse_commits_with_author(self):
        result = parse_commits(
            "abc\tAndrew\t2026-08-15\tFix auth"
        )

        self.assertEqual(
            result,
            [
                {
                    "commit": "abc",
                    "author": "Andrew",
                    "date": "2026-08-15",
                    "subject": "Fix auth",
                }
            ],
        )

    def test_parse_commits_without_author(self):
        result = parse_commits(
            "abc\t2026-08-15\tFix auth"
        )

        self.assertEqual(
            result,
            [
                {
                    "commit": "abc",
                    "date": "2026-08-15",
                    "subject": "Fix auth",
                }
            ],
        )

    def test_parse_numstat(self):
        result = parse_numstat(
            "3\t1\tfile.py\n"
            "5\t2\tother.py"
        )

        self.assertEqual(
            result,
            [
                {
                    "additions": 3,
                    "deletions": 1,
                    "file": "file.py",
                },
                {
                    "additions": 5,
                    "deletions": 2,
                    "file": "other.py",
                },
            ],
        )

    def test_parse_numstat_binary(self):
        result = parse_numstat(
            "-\t-\timage.png"
        )

        self.assertEqual(
            result[0]["additions"],
            "-",
        )

        self.assertEqual(
            result[0]["deletions"],
            "-",
        )

    def test_parse_empty(self):
        self.assertEqual(
            parse_commits(""),
            [],
        )

        self.assertEqual(
            parse_numstat(""),
            [],
        )


class TestBasicCommands(unittest.TestCase):

    @patch.object(better_git, "run_git")
    def test_status(self, mock_git):
        mock_git.side_effect = [
            "main",
            "M  staged.py\n M unstaged.py\n?? new.py",
        ]

        result = status()

        self.assertEqual(
            result["branch"],
            "main",
        )

        self.assertEqual(
            result["staged"],
            ["staged.py"],
        )

        self.assertEqual(
            result["unstaged"],
            ["unstaged.py"],
        )

        self.assertEqual(
            result["untracked"],
            ["new.py"],
        )

    @patch.object(better_git, "run_git")
    def test_status_both_staged_and_unstaged(self, mock_git):
        mock_git.side_effect = [
            "feature",
            "MM file.py",
        ]

        result = status()

        self.assertEqual(
            result["staged"],
            ["file.py"],
        )

        self.assertEqual(
            result["unstaged"],
            ["file.py"],
        )

    @patch.object(better_git, "run_git")
    def test_branch_with_upstream(self, mock_git):
        mock_git.side_effect = [
            "feature",
            "origin/feature",
            "2\t1",
        ]

        result = branch()

        self.assertEqual(
            result["branch"],
            "feature",
        )

        self.assertEqual(
            result["upstream"],
            "origin/feature",
        )

        self.assertEqual(
            result["ahead"],
            2,
        )

        self.assertEqual(
            result["behind"],
            1,
        )

    @patch.object(better_git, "run_git")
    def test_branch_without_upstream(self, mock_git):
        mock_git.side_effect = [
            "feature",
            RuntimeError("no upstream"),
        ]

        result = branch()

        self.assertEqual(
            result["branch"],
            "feature",
        )

        self.assertEqual(
            result["upstream"],
            "",
        )

        self.assertEqual(
            result["ahead"],
            0,
        )

        self.assertEqual(
            result["behind"],
            0,
        )

    @patch.object(better_git, "run_git")
    def test_diff(self, mock_git):
        mock_git.side_effect = [
            "unstaged diff",
            "staged diff",
        ]

        result = diff()

        self.assertEqual(
            result["unstaged"],
            "unstaged diff",
        )

        self.assertEqual(
            result["staged"],
            "staged diff",
        )

    @patch.object(better_git, "run_git")
    def test_diff_path(self, mock_git):
        mock_git.side_effect = [
            "unstaged",
            "staged",
        ]

        result = diff("file.py")

        self.assertEqual(
            result,
            {
                "unstaged": "unstaged",
                "staged": "staged",
            },
        )

        self.assertEqual(
            mock_git.call_args_list[0].args,
            ("diff", "--", "file.py"),
        )

        self.assertEqual(
            mock_git.call_args_list[1].args,
            ("diff", "--cached", "--", "file.py"),
        )

    @patch.object(better_git, "run_git")
    def test_changed(self, mock_git):
        mock_git.side_effect = [
            "3\t1\tfile.py",
            "5\t2\tother.py",
        ]

        result = changed()

        self.assertEqual(
            len(result["files"]),
            2,
        )

        self.assertEqual(
            result["files"][0]["state"],
            "staged",
        )

        self.assertEqual(
            result["files"][1]["state"],
            "unstaged",
        )

    @patch.object(better_git, "run_git")
    def test_diff_summary(self, mock_git):
        mock_git.side_effect = [
            "file.py | 4 +++-",
            "other.py | 2 +-",
        ]

        result = diff_summary()

        self.assertEqual(
            len(result["unstaged"]),
            1,
        )

        self.assertEqual(
            len(result["staged"]),
            1,
        )

    @patch.object(better_git, "run_git")
    def test_recent(self, mock_git):
        mock_git.return_value = (
            "abc\tAndrew\t2026-08-15\tFix auth\n"
            "def\tAndrew\t2026-08-14\tAdd tests"
        )

        result = recent(2)

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[0]["commit"],
            "abc",
        )

    def test_recent_rejects_invalid_limit(self):
        with self.assertRaises(ValueError):
            recent(0)

    @patch.object(better_git, "run_git")
    def test_log_path(self, mock_git):
        mock_git.return_value = (
            "abc\t2026-08-15\tFix auth\n"
            "def\t2026-08-14\tAdd tests"
        )

        result = log_path(
            "file.py",
            2,
        )

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[0]["commit"],
            "abc",
        )

    @patch.object(better_git, "run_git")
    def test_conflicts(self, mock_git):
        mock_git.return_value = "a.py\nb.py"

        self.assertEqual(
            conflicts(),
            ["a.py", "b.py"],
        )

    @patch.object(better_git, "run_git")
    def test_show(self, mock_git):
        mock_git.side_effect = [
            "abc\nAndrew\n2026-08-15\nFix auth",
            " file.py | 2 +-",
        ]

        result = show("abc")

        self.assertEqual(
            result["commit"],
            "abc",
        )

        self.assertEqual(
            result["author"],
            "Andrew",
        )

        self.assertEqual(
            result["subject"],
            "Fix auth",
        )

        self.assertEqual(
            result["files"],
            [" file.py | 2 +-"],
        )


class TestCompoundWorkflows(unittest.TestCase):

    @patch.object(better_git, "run_git")
    def test_check(self, mock_git):
        mock_git.side_effect = [
            # branch()
            "main",
            "origin/main",
            "0\t0",

            # status()
            "main",
            "",

            # changed()
            "",
            "",

            # diff_summary()
            "",
            "",

            # conflicts()
            "",
        ]

        result = check()

        self.assertIn(
            "branch",
            result,
        )

        self.assertIn(
            "status",
            result,
        )

        self.assertIn(
            "changed",
            result,
        )

        self.assertIn(
            "diff_summary",
            result,
        )

        self.assertIn(
            "conflicts",
            result,
        )

    @patch.object(better_git, "run_git")
    def test_context(self, mock_git):
        mock_git.side_effect = [
            # status
            "main",
            "",

            # log_path
            "abc\t2026-08-15\tChange file",

            # diff
            "unstaged",
            "staged",
        ]

        result = context("file.py")

        self.assertEqual(
            result["path"],
            "file.py",
        )

        self.assertIn(
            "history",
            result,
        )

        self.assertIn(
            "diff",
            result,
        )

        self.assertIn(
            "status",
            result,
        )

    @patch.object(better_git, "run_git")
    def test_review(self, mock_git):
        mock_git.side_effect = [
            # branch
            "main",
            "",
            "",

            # status
            "main",
            "",

            # changed
            "",
            "",

            # diff summary
            "",
            "",

            # diff
            "unstaged",
            "staged",

            # conflicts
            "",
        ]

        result = review()

        self.assertIn(
            "branch",
            result,
        )

        self.assertIn(
            "status",
            result,
        )

        self.assertIn(
            "changed",
            result,
        )

        self.assertIn(
            "diff_summary",
            result,
        )

        self.assertIn(
            "diff",
            result,
        )

        self.assertIn(
            "conflicts",
            result,
        )

    @patch.object(better_git, "run_git")
    def test_review_branch(self, mock_git):
        mock_git.side_effect = [
            # merge-base
            "abc123",

            # commits
            "def456\t2026-08-15\tAdd feature",

            # numstat
            "1\t2\tfile.py",

            # stat
            "file.py | 3 ++-",

            # full diff
            "full diff",

            # branch()
            "main",
            "origin/main",
            "0\t0",
        ]

        result = review_branch("main")

        self.assertEqual(
            result["base"],
            "main",
        )

        self.assertEqual(
            result["merge_base"],
            "abc123",
        )

        self.assertEqual(
            len(result["commits"]),
            1,
        )

        self.assertEqual(
            result["commits"][0]["commit"],
            "def456",
        )

        self.assertEqual(
            result["diff"],
            "full diff",
        )

        self.assertEqual(
            result["branch"]["branch"],
            "main",
        )

    @patch.object(better_git, "run_git")
    def test_commit_context(self, mock_git):
        mock_git.side_effect = [
            # status
            "main",
            "M  file.py",

            # branch
            "main",
            "",

            # recent
            "abc\tAndrew\t2026-08-15\tCommit",

            # changed
            "1\t1\tfile.py",
            "",

            # diff summary
            "file.py | 2 +-",
            "",

            # conflicts
            "",
        ]

        result = commit_context()

        self.assertTrue(
            result["ready_to_commit"]
        )

        self.assertFalse(
            result["unstaged_work"]
        )

    @patch.object(better_git, "run_git")
    def test_fix_context(self, mock_git):
        mock_git.side_effect = [
            # status
            "main",
            " M file.py",

            # branch
            "main",
            "",

            # changed
            "",
            "1\t1\tfile.py",

            # diff summary
            "file.py | 2 +-",
            "",

            # diff
            "unstaged diff",
            "staged diff",

            # conflicts
            "conflict.py",
        ]

        result = fix_context()

        self.assertTrue(
            result["has_conflicts"]
        )

        self.assertEqual(
            result["conflicts"],
            ["conflict.py"],
        )

    @patch.object(better_git, "run_git")
    def test_merge_context(self, mock_git):
        mock_git.side_effect = [
            # status
            "main",
            "UU file.py",

            # branch
            "main",
            "",

            # conflicts
            "file.py",

            # changed
            "",
            "",

            # diff summary
            "",
            "",

            # diff
            "merge diff",
            "staged merge diff",
        ]

        result = merge_context()

        self.assertTrue(
            result["has_conflicts"]
        )

        self.assertEqual(
            result["conflicts"],
            ["file.py"],
        )

    @patch.object(better_git, "run_git")
    @patch.object(better_git, "is_rebasing")
    def test_rebase_context(
        self,
        mock_rebasing,
        mock_git,
    ):
        mock_rebasing.return_value = True

        mock_git.side_effect = [
            # status
            "feature",
            "UU file.py",

            # branch
            "feature",
            "origin/feature",
            "1\t0",

            # conflicts
            "file.py",

            # changed
            "",
            "",

            # diff summary
            "",
            "",

            # diff
            "unstaged",
            "staged",
        ]

        result = rebase_context()

        self.assertTrue(
            result["rebasing"]
        )

        self.assertEqual(
            result["conflicts"],
            ["file.py"],
        )

    @patch.object(better_git, "run_git")
    @patch.object(better_git, "is_rebasing")
    def test_rebase_context_not_rebasing(
        self,
        mock_rebasing,
        mock_git,
    ):
        mock_rebasing.return_value = False

        mock_git.side_effect = [
            # status
            "main",
            "",

            # branch
            "main",
            "",
            
            # conflicts
            "",

            # changed
            "",
            "",

            # diff summary
            "",
            "",

            # diff
            "",
            "",
        ]

        result = rebase_context()

        self.assertFalse(
            result["rebasing"]
        )

        self.assertEqual(
            result["conflicts"],
            [],
        )

    @patch.object(better_git, "run_git")
    def test_ship_context_clean(self, mock_git):
        mock_git.side_effect = [
            # branch
            "main",
            "origin/main",
            "0\t0",

            # status
            "main",
            "",

            # conflicts
            "",

            # changed
            "",
            "",

            # diff summary
            "",
            "",

            # recent
            "abc\tAndrew\t2026-08-15\tCommit",
        ]

        result = ship_context()

        self.assertTrue(
            result["clean"]
        )

        self.assertTrue(
            result["ready_to_ship"]
        )

    @patch.object(better_git, "run_git")
    def test_ship_context_not_ready_with_changes(
        self,
        mock_git,
    ):
        mock_git.side_effect = [
            # branch
            "main",
            "origin/main",
            "0\t0",

            # status
            "main",
            " M file.py",

            # conflicts
            "",

            # changed
            "",
            "1\t1\tfile.py",

            # diff summary
            "file.py | 2 +-",
            "",

            # recent
            "abc\tAndrew\t2026-08-15\tCommit",
        ]

        result = ship_context()

        self.assertFalse(
            result["clean"]
        )

        self.assertFalse(
            result["ready_to_ship"]
        )


class TestVerification(unittest.TestCase):

    @patch.object(better_git, "run_git")
    def test_verify_context_clean(self, mock_git):
        mock_git.side_effect = [
            # status
            "main",
            "",

            # conflicts
            "",

            # branch
            "main",
            "",

            # changed
            "",
            "",

            # diff summary
            "",
            "",
        ]

        result = verify_context()

        self.assertFalse(
            result["has_conflicts"]
        )

        self.assertFalse(
            result["has_changes"]
        )

        self.assertTrue(
            result["clean"]
        )

    @patch.object(better_git, "run_git")
    def test_verify_context_failed(self, mock_git):
        mock_git.side_effect = [
            # status
            "main",
            " M file.py",

            # conflicts
            "",

            # branch
            "main",
            "",

            # changed
            "",
            "1\t1\tfile.py",

            # diff summary
            "file.py | 2 +-",
            "",
        ]

        result = verify_context()

        self.assertFalse(
            result["has_conflicts"]
        )

        self.assertTrue(
            result["has_changes"]
        )

        self.assertFalse(
            result["clean"]
        )


class TestStash(unittest.TestCase):

    @patch.object(better_git, "run_git")
    def test_stash_list(self, mock_git):
        mock_git.return_value = (
            "stash@{0}\tabc123\tWIP on main"
        )

        result = stash_list()

        self.assertEqual(
            len(result),
            1,
        )

        self.assertEqual(
            result[0]["stash"],
            "stash@{0}",
        )

        self.assertEqual(
            result[0]["commit"],
            "abc123",
        )

    @patch.object(better_git, "run_git")
    def test_stash_context(self, mock_git):
        mock_git.side_effect = [
            # branch
            "main",
            "",

            # status
            "main",
            "",

            # changed
            "",
            "",

            # diff summary
            "",
            "",

            # stash list
            "stash@{0}\tabc123\tWIP",

            # conflicts
            "",
        ]

        result = stash_context()

        self.assertIn(
            "stashes",
            result,
        )

        self.assertEqual(
            len(result["stashes"]),
            1,
        )


class TestTags(unittest.TestCase):

    @patch.object(better_git, "run_git")
    def test_tags(self, mock_git):
        mock_git.return_value = (
            "v1.0.0\tabc123\t2026-08-15\tRelease"
        )

        result = tags(20)

        self.assertEqual(
            len(result),
            1,
        )

        self.assertEqual(
            result[0]["tag"],
            "v1.0.0",
        )

        self.assertEqual(
            result[0]["commit"],
            "abc123",
        )

    @patch.object(better_git, "run_git")
    def test_tag_context(self, mock_git):
        mock_git.side_effect = [
            # branch
            "main",
            "",

            # describe
            "v1.0.0",

            # tags
            "v1.0.0\tabc123\t2026-08-15\tRelease",

            # recent
            "abc123\tAndrew\t2026-08-15\tRelease",
        ]

        result = tag_context()

        self.assertEqual(
            result["current"],
            "v1.0.0",
        )

        self.assertEqual(
            len(result["tags"]),
            1,
        )


class TestRemotes(unittest.TestCase):

    @patch.object(better_git, "run_git")
    def test_remotes(self, mock_git):
        mock_git.return_value = (
            "origin\tgit@github.com:example/repo.git\t(fetch)\n"
            "origin\tgit@github.com:example/repo.git\t(push)\n"
        )

        result = remotes()

        self.assertEqual(
            len(result),
            2,
        )

        self.assertEqual(
            result[0]["name"],
            "origin",
        )

    @patch.object(better_git, "run_git")
    def test_remote_context(self, mock_git):
        mock_git.side_effect = [
            # branch
            "main",
            "origin/main",
            "0\t0",

            # remotes
            "origin\tgit@github.com:example/repo.git\t(fetch)",

            # status
            "main",
            "",

            # recent
            "abc\tAndrew\t2026-08-15\tCommit",
        ]

        result = remote_context()

        self.assertIn(
            "remotes",
            result,
        )

        self.assertEqual(
            result["branch"]["branch"],
            "main",
        )


class TestPRContext(unittest.TestCase):

    @patch.object(better_git, "run_git")
    def test_pr_context_with_upstream(self, mock_git):
        mock_git.side_effect = [
            # branch
            "feature",
            "origin/feature",
            "2\t0",

            # status
            "feature",
            "",

            # recent
            "abc\tAndrew\t2026-08-15\tFeature",

            # changed
            "1\t2\tfile.py",
            "",

            # diff summary
            "file.py | 3 ++-",
            "",

            # conflicts
            "",

            # merge base
            "base123",

            # commits
            "abc\t2026-08-15\tFeature",

            # branch diff
            "file.py | 3 ++-",
        ]

        result = pr_context()

        self.assertEqual(
            result["upstream"],
            "origin/feature",
        )

        self.assertEqual(
            result["merge_base"],
            "base123",
        )

        self.assertEqual(
            len(result["commits"]),
            1,
        )

        self.assertEqual(
            result["branch_diff"],
            ["file.py | 3 ++-"],
        )

    @patch.object(better_git, "run_git")
    def test_pr_context_without_upstream(self, mock_git):
        mock_git.side_effect = [
            # branch
            "feature",
            RuntimeError("no upstream"),

            # status
            "feature",
            "",

            # recent
            "abc\tAndrew\t2026-08-15\tFeature",

            # changed
            "",
            "",

            # diff summary
            "",
            "",

            # conflicts
            "",
        ]

        result = pr_context()

        self.assertEqual(
            result["upstream"],
            "",
        )

        self.assertEqual(
            result["merge_base"],
            "",
        )

        self.assertEqual(
            result["commits"],
            [],
        )

        self.assertEqual(
            result["branch_diff"],
            [],
        )


class TestInspect(unittest.TestCase):

    @patch.object(better_git, "run_git")
    def test_inspect_path(self, mock_git):
        mock_git.side_effect = [
            # log
            "abc\t2026-08-15\tFix",

            # diff
            "unstaged",
            "staged",

            # status
            "main",
            "",
        ]

        result = inspect_path("file.py")

        self.assertEqual(
            result["path"],
            "file.py",
        )

        self.assertIn(
            "history",
            result,
        )

        self.assertIn(
            "diff",
            result,
        )

        self.assertIn(
            "status",
            result,
        )


class TestRebaseDetection(unittest.TestCase):

    @patch.object(
        better_git,
        "run_git",
        side_effect=[
            "/tmp/repo/.git/rebase-merge",
        ],
    )
    @patch.object(
        better_git.subprocess,
        "run",
    )
    def test_is_rebasing_true(
        self,
        mock_run,
        mock_git,
    ):
        mock_run.return_value.returncode = 0

        self.assertTrue(
            is_rebasing()
        )

    @patch.object(
        better_git,
        "run_git",
        side_effect=RuntimeError("not git"),
    )
    def test_is_rebasing_false(self, mock_git):
        self.assertFalse(
            is_rebasing()
        )


if __name__ == "__main__":
    unittest.main()