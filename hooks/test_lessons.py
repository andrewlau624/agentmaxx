import importlib.util
import io
import json
import os
import pathlib
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

HERE = pathlib.Path(__file__).parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lessons = load("lessons")


def run_hook(mode, event):
    out = io.StringIO()
    with mock.patch("sys.stdin", io.StringIO(json.dumps(event))), redirect_stdout(out):
        lessons.hook(mode)
    return out.getvalue()


class TestCorrectionRegex(unittest.TestCase):
    def test_openers_need_a_correction_shape(self):
        for p in ["no i meant the btc one", "No. Use pnpm here", "nope, the other file", "wait but youre forgetting the fee",
                  "actually - i want the 15m version", "still not a fan of the footer", "its not loading",
                  "undo all changes", "shorter please", "this is not for the test", "just do verifications",
                  "i meant the current strategy", "im not a big fan of this", "stop asking me and run it"]:
            self.assertTrue(lessons.CORRECTION.search(p), p)
        for p in ["no", "no riscv?", "no 169 today?", "no Jev https://example.com/post", "no other way to dig deeper?",
                  "wait yesterday i was sick", "wait for the build to finish", "still waiting on the deploy",
                  "i asked chatgpt about it", "known issue: noise in logs", "just checking in"]:
            self.assertFalse(lessons.CORRECTION.search(p), p)


class TestEvidence(unittest.TestCase):
    def setUp(self):
        self.path = pathlib.Path(tempfile.mkdtemp()) / "l.md"

    def test_old_and_new_lines_parse(self):
        self.path.write_text(
            "- [L1 h=0 x=0 2026-10-06] Use pnpm, never npm, in this repo\n"
            "- [L2 h=1 x=0 2026-10-07] Keep commit messages short\n"
            "  evidence: I ran npm install and wrote a four-paragraph commit message\n"
            "- [L3 h=0 x=0 2026-10-08] Deliver decks as .pptx\n")
        items = lessons.load(self.path)
        self.assertEqual([i["id"] for i in items], ["L1", "L2", "L3"])
        self.assertNotIn("evidence", items[0])
        self.assertEqual(items[1]["evidence"], "I ran npm install and wrote a four-paragraph commit message")
        self.assertEqual(items[2]["text"], "Deliver decks as .pptx")
        lessons.save(self.path, items)
        self.assertEqual(lessons.load(self.path), items)

    def test_add_stores_and_updates_evidence(self):
        self.assertEqual(lessons.add(self.path, "Use pnpm, never npm", "I ran `npm install`\nto set up"), "added L1")
        self.assertEqual(lessons.load(self.path)[0]["evidence"], "I ran `npm install` to set up")
        self.assertEqual(lessons.add(self.path, "Use pnpm never npm!"), "updated L1")
        self.assertEqual(lessons.load(self.path)[0]["evidence"], "I ran `npm install` to set up")
        self.assertEqual(lessons.add(self.path, "No npm here", "x" * 500), "added L2")
        self.assertEqual(len(lessons.load(self.path)[1]["evidence"]), lessons.EVIDENCE_CHARS)

    def test_last_assistant_text_skips_tool_only_turns(self):
        transcript = self.path.with_suffix(".jsonl")
        transcript.write_text("\n".join([
            json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "I will switch to npm now."}]}}),
            json.dumps({"type": "assistant", "message": {"content": [{"type": "thinking", "thinking": "hmm"},
                                                                       {"type": "tool_use", "name": "Bash", "input": {}}]}}),
            json.dumps({"type": "user", "message": {"content": "no, pnpm"}}),
        ]))
        self.assertEqual(lessons.last_assistant_text(str(transcript)), "I will switch to npm now.")
        self.assertEqual(lessons.last_assistant_text(str(transcript) + ".missing"), "")

    def test_prompt_hook_quotes_the_evidence(self):
        transcript = self.path.with_suffix(".jsonl")
        transcript.write_text(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "text", "text": "Done: I ran npm install; it's \"fast\" enough."}]}}) + "\n")
        out = run_hook("prompt", {"prompt": "no, use pnpm", "cwd": str(self.path.parent), "transcript_path": str(transcript)})
        self.assertIn("--evidence 'Done: I ran npm install; it'\"'\"'s \"fast\" enough.'", out)
        self.assertEqual(run_hook("prompt", {"prompt": "add csv export", "cwd": str(self.path.parent)}), "")


class TestFailureHook(unittest.TestCase):
    def setUp(self):
        self.home = pathlib.Path(tempfile.mkdtemp())
        self.repo = tempfile.mkdtemp()
        subprocess.run("git init -q && git commit -q --allow-empty -m init", shell=True, cwd=self.repo, check=True)
        self.old_home, lessons.HOME = lessons.HOME, self.home / "lessons"
        lessons.add(lessons.path_for(self.repo, False), "Use pnpm, never npm, in this repo")
        lessons.add(lessons.path_for(self.repo, False), "Run the migration tests before touching models")
        lessons.add(lessons.path_for(self.repo, True), "Never retry a failing deploy more than once")

    def tearDown(self):
        lessons.HOME = self.old_home

    def test_render_leaves_evidence_out(self):
        lessons.add(lessons.path_for(self.repo, False), "Prefer uv over pip", "I ran pip install SECRETWORD")
        out = lessons.render(self.repo)
        self.assertIn("Prefer uv over pip", out)
        self.assertNotIn("SECRETWORD", out)
        self.assertNotIn("evidence", out)

    def test_matches_error_and_command_once_per_session(self):
        event = {"tool_name": "Bash", "tool_input": {"command": "npm install"}, "session_id": "s1", "cwd": self.repo,
                 "error": "npm ERR! code ERESOLVE\nnpm ERR! could not resolve dependency"}
        out = json.loads(run_hook("failure", event))
        ctx = out["hookSpecificOutput"]["additionalContext"]
        self.assertEqual(out["hookSpecificOutput"]["hookEventName"], "PostToolUseFailure")
        self.assertTrue(ctx.startswith("Lessons that match this failure:\n- (this repo, L1) Use pnpm"), ctx)
        self.assertNotIn("migration", ctx)
        self.assertNotIn("deploy", ctx)
        self.assertEqual(run_hook("failure", event), "")  # same session: already injected
        self.assertIn("Use pnpm", run_hook("failure", dict(event, session_id="s2")))
        self.assertTrue((self.home / "lessons" / "fired" / "s1.json").exists())

    def test_no_overlap_means_silence(self):
        self.assertEqual(run_hook("failure", {"tool_name": "Edit", "tool_input": {"file_path": "/x/y.go"},
                                              "session_id": "s3", "cwd": self.repo, "error": "String not found"}), "")
        self.assertEqual(run_hook("failure", {"tool_name": "Bash", "tool_input": "weird", "session_id": "s3",
                                              "cwd": self.repo, "error": None}), "")

    def test_caps_at_three_best_matches(self):
        for rule in ["Check the deploy logs before retrying", "Deploy only from main after the tests pass",
                     "A deploy that fails twice needs a human, stop retrying", "Roll back the deploy before debugging logs",
                     "Deploy logs live in fly logs, read them before retrying"]:
            lessons.add(lessons.path_for(self.repo, True), rule)
        ctx = json.loads(run_hook("failure", {"tool_name": "Bash", "tool_input": {"command": "./deploy.sh"},
                                              "session_id": "s4", "cwd": self.repo,
                                              "error": "deploy failed: retrying is pointless, check logs"}))
        self.assertEqual(ctx["hookSpecificOutput"]["additionalContext"].count("\n- "), 3)


if __name__ == "__main__":
    unittest.main()
