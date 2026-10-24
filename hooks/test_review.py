import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
import unittest.mock

HERE = pathlib.Path(__file__).parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


review = load("review")


def record(kind, content, **extra):
    r = {"type": kind, "message": {"role": kind, "content": content}, "timestamp": "2026-10-01T00:00:00Z"}
    r.update(extra)
    return json.dumps(r)


def write_transcript(path, lines):
    path.write_text("\n".join(lines) + "\n")
    return str(path)


EDIT = record("assistant", [{"type": "tool_use", "name": "Edit", "input": {"file_path": "a.py"}}])
TYPED = record("user", "Make parse() handle empty input by returning [].")


class TestTaskStatement(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_skips_meta_sidechain_commands_and_tool_results(self):
        path = write_transcript(self.dir / "t.jsonl", [
            record("user", "injected", isMeta=True),
            record("user", "side quest", isSidechain=True),
            record("user", "<command-name>/clear</command-name>"),
            record("user", [{"type": "tool_result", "content": "ok"}]),
            record("user", [{"type": "text", "text": "  Fix the thing  "}]),
            record("user", "second prompt, must not win"),
        ])
        self.assertEqual(review.task_statement(path), "Fix the thing")

    def test_trims_long_prompts(self):
        path = write_transcript(self.dir / "t.jsonl", [record("user", "x" * 5000)])
        out = review.task_statement(path, limit=100)
        self.assertTrue(out.endswith("[...]"))
        self.assertLessEqual(len(out), 110)

    def test_missing_transcript_is_empty(self):
        self.assertEqual(review.task_statement(str(self.dir / "nope.jsonl")), "")

    def test_headless_from_transcript_or_env(self):
        path = write_transcript(self.dir / "t.jsonl", [record("user", "bench task", entrypoint="sdk-cli")])
        self.assertTrue(review.headless(path))
        typed = write_transcript(self.dir / "u.jsonl", [TYPED])
        self.assertFalse(review.headless(typed))
        with unittest.mock.patch.dict(os.environ, {"CLAUDE_CODE_ENTRYPOINT": "sdk-cli"}):
            self.assertTrue(review.headless(typed))


class TestParseGaps(unittest.TestCase):
    def test_plain_list(self):
        gaps = review.parse_gaps('[{"file": "a.py", "line": 3, "gap": "empty input raises"}]')
        self.assertEqual(gaps, [{"file": "a.py", "line": 3, "gap": "empty input raises"}])

    def test_junk_and_fences_around_list(self):
        raw = 'Here is my review:\n```json\n[{"file":"a.py","line":null,"gap":"x"}]\n```\nHope that helps.'
        self.assertEqual(review.parse_gaps(raw), [{"file": "a.py", "line": None, "gap": "x"}])

    def test_cli_json_envelope(self):
        raw = json.dumps({"type": "result", "result": '[{"file":"b.py","line":1,"gap":"y"}]', "cost_usd": 0.01})
        self.assertEqual(review.parse_gaps(raw), [{"file": "b.py", "line": 1, "gap": "y"}])

    def test_empty_list_and_garbage(self):
        self.assertEqual(review.parse_gaps("[]"), [])
        self.assertEqual(review.parse_gaps(json.dumps({"result": "[]"})), [])
        self.assertIsNone(review.parse_gaps("the reviewer crashed"))
        self.assertIsNone(review.parse_gaps(""))

    def test_caps_at_max_and_drops_blank_gaps(self):
        items = [{"file": "f", "line": i, "gap": f"g{i}"} for i in range(9)] + [{"file": "f", "gap": ""}]
        self.assertEqual(len(review.parse_gaps(json.dumps(items))), review.MAX_GAPS)


class TestDiffFiltering(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        self.git("init", "-q")
        self.git("config", "user.email", "t@t")
        self.git("config", "user.name", "t")
        (pathlib.Path(self.repo) / "a.py").write_text("def f():\n    return 1\n")
        (pathlib.Path(self.repo) / "package-lock.json").write_text("{}\n")
        (pathlib.Path(self.repo) / "big.py").write_text("x = 0\n" * 10)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "init")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, check=True, capture_output=True)

    def test_empty_tree_is_none(self):
        self.assertIsNone(review.collect_diff(self.repo))

    def test_includes_staged_unstaged_and_untracked(self):
        (pathlib.Path(self.repo) / "a.py").write_text("def f():\n    return 2\n")
        (pathlib.Path(self.repo) / "new.py").write_text("y = 1\n")
        diff = review.collect_diff(self.repo)
        self.assertIn("return 2", diff)
        self.assertIn("new.py", diff)
        self.assertIn("+y = 1", diff)
        self.git("add", "a.py")  # staged edits still count
        self.assertIn("return 2", review.collect_diff(self.repo))

    def test_drops_lockfiles_and_oversized_files(self):
        (pathlib.Path(self.repo) / "package-lock.json").write_text('{"a": 1}\n')
        (pathlib.Path(self.repo) / "big.py").write_text("x = 1\n" * 10)  # 20 changed lines
        (pathlib.Path(self.repo) / "a.py").write_text("def f():\n    return 3\n")
        diff = review.collect_diff(self.repo, max_file=15)
        self.assertNotIn("package-lock", diff)
        self.assertNotIn("big.py", diff)
        self.assertIn("return 3", diff)
        # only a lockfile changed: nothing reviewable
        (pathlib.Path(self.repo) / "a.py").write_text("def f():\n    return 1\n")
        (pathlib.Path(self.repo) / "big.py").write_text("x = 0\n" * 10)
        self.assertIsNone(review.collect_diff(self.repo))

    def test_total_over_cap_is_none(self):
        (pathlib.Path(self.repo) / "a.py").write_text("def f():\n    return 4\n")
        (pathlib.Path(self.repo) / "new.py").write_text("y = 1\n" * 8)
        self.assertIsNotNone(review.collect_diff(self.repo, max_total=50))
        self.assertIsNone(review.collect_diff(self.repo, max_total=5))


class TestDecide(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = pathlib.Path(self.tmp.name)
        self.state = unittest.mock.patch.object(review, "STATE", str(self.dir / "state"))
        self.state.start()
        self.env = unittest.mock.patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop("AGENTMAXX_REVIEW", None)
        os.environ.pop("CLAUDE_CODE_ENTRYPOINT", None)
        self.transcript = write_transcript(self.dir / "t.jsonl", [TYPED, EDIT])
        self.diff = unittest.mock.patch.object(review, "collect_diff", return_value="--- a/a.py\n+++ b/a.py\n+x\n")
        self.diff.start()

    def tearDown(self):
        self.diff.stop()
        self.env.stop()
        self.state.stop()
        self.tmp.cleanup()

    def event(self, **extra):
        e = {"session_id": "s1", "cwd": self.tmp.name, "transcript_path": self.transcript,
             "stop_hook_active": False, "last_assistant_message": "Done."}
        e.update(extra)
        return e

    def test_blocks_on_gaps_and_prompt_has_task_and_diff(self):
        seen = {}

        def fake(prompt, cwd):
            seen["prompt"] = prompt
            return json.dumps({"result": '[{"file":"a.py","line":2,"gap":"empty input still raises"}]'})

        out = review.decide(self.event(), run=fake)
        self.assertEqual(out["decision"], "block")
        self.assertIn("found 1 gap:", out["reason"])
        self.assertIn("- a.py:2 empty input still raises", out["reason"])
        self.assertIn("say why each is not a gap", out["reason"])
        self.assertIn("Make parse() handle empty input", seen["prompt"])
        self.assertIn("+x", seen["prompt"])
        self.assertIn("Done.", seen["prompt"])
        self.assertTrue(review.already_reviewed("s1"))
        self.assertTrue((self.dir / "state" / "s1.raw").exists())

    def test_allows_on_empty_list_and_records(self):
        self.assertIsNone(review.decide(self.event(), run=lambda p, c: "[]"))
        self.assertTrue(review.already_reviewed("s1"))

    def test_allows_when_reviewer_fails(self):
        self.assertIsNone(review.decide(self.event(), run=lambda p, c: None))
        self.assertIsNone(review.decide(self.event(session_id="s2"), run=lambda p, c: "not json at all"))
        self.assertTrue(review.already_reviewed("s1"))
        self.assertTrue(review.already_reviewed("s2"))

    def test_at_most_once_per_session(self):
        calls = []

        def fake(prompt, cwd):
            calls.append(1)
            return '[{"file":"a.py","line":1,"gap":"g"}]'

        self.assertIsNotNone(review.decide(self.event(), run=fake))
        self.assertIsNone(review.decide(self.event(), run=fake))
        self.assertEqual(len(calls), 1)
        # a different session is reviewed on its own
        self.assertIsNotNone(review.decide(self.event(session_id="s9"), run=fake))
        self.assertEqual(len(calls), 2)

    def test_silent_exits(self):
        boom = unittest.mock.Mock(side_effect=AssertionError("reviewer must not run"))
        self.assertIsNone(review.decide(self.event(stop_hook_active=True), run=boom))
        with unittest.mock.patch.dict(os.environ, {"AGENTMAXX_REVIEW": "0"}):
            self.assertIsNone(review.decide(self.event(), run=boom))
        with unittest.mock.patch.dict(os.environ, {"CLAUDE_CODE_ENTRYPOINT": "sdk-cli"}):
            self.assertIsNone(review.decide(self.event(), run=boom))
        no_edit = write_transcript(self.dir / "ne.jsonl", [TYPED])
        self.assertIsNone(review.decide(self.event(transcript_path=no_edit), run=boom))
        bench = write_transcript(self.dir / "b.jsonl", [record("user", "task", entrypoint="sdk-cli"), EDIT])
        self.assertIsNone(review.decide(self.event(transcript_path=bench), run=boom))
        with unittest.mock.patch.object(review, "collect_diff", return_value=None):
            self.assertIsNone(review.decide(self.event(), run=boom))
        self.assertFalse(review.already_reviewed("s1"))

    def test_main_prints_block_json(self):
        with unittest.mock.patch.object(review, "run_reviewer", lambda p, c: '[{"file":"a.py","line":1,"gap":"g"}]'), \
                unittest.mock.patch("sys.stdin", __import__("io").StringIO(json.dumps(self.event()))), \
                unittest.mock.patch("sys.stdout", new_callable=__import__("io").StringIO) as out:
            self.assertEqual(review.main(), 0)
        self.assertEqual(json.loads(out.getvalue())["decision"], "block")


if __name__ == "__main__":
    unittest.main()
