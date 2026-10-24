import importlib.util
import io
import json
import pathlib
import time
import unittest
import unittest.mock

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("prompt_guard", HERE / "prompt_guard.py")
pg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pg)


def run(prompt, env=None):
    event = {"hook_event_name": "UserPromptSubmit", "prompt": prompt, "session_id": "s", "cwd": "/tmp", "transcript_path": "/tmp/t.jsonl"}
    out = io.StringIO()
    with unittest.mock.patch("sys.stdin", io.StringIO(json.dumps(event))), unittest.mock.patch("sys.stdout", out), \
            unittest.mock.patch.dict("os.environ", env or {}, clear=False):
        rc = pg.main()
    return rc, out.getvalue()


class TestMisread(unittest.TestCase):
    FIRE = [
        # the typed prompts that preceded or were real misread corrections in the 30-day transcript mine
        "wow did i do a good job", "no i meant with the minute/seconds idea", "no two repos app and server",
        "no the useThinkScript forum",
        # deictic with nothing in the prompt to point at
        "fix it", "add it to the alert?", "the other one", "do the same for the rest", "go do it", "so how about now",
        # correction openers
        "no", "wait", "actually use the first approach", "not that, the other", "i meant the server",
        # typo-heavy
        "can you tihnk about waht else", "why does none of the resaerch involve probabilities i fele like thats super important",
    ]
    SKIP = [
        "ok", "yes", "continue", "go", "done", "thanks", "go ahead", "stop",
        "/usage", "/commit now", "/loop 5m /foo",
        '<pasted_content id="1">\nfoo\nbar\n</pasted_content>', '{"a": 1, "b": 2}', "```\nfoo\n```",
        "add it to hooks/lessons.py", "run the tests in hooks/ again", "update README.md to mention the new flag",
        "browse schwab forums for as many strategies you can", "how long does hist probe take",
        "push this to a private repo on GitHub",
        "regardless at the end of these trades for the btc and eth, if youre confident in both and ready to trade them, run a combo",
    ]

    def test_fires(self):
        for p in self.FIRE:
            self.assertTrue(pg.misread(p), p)

    def test_skips(self):
        for p in self.SKIP:
            self.assertFalse(pg.misread(p), p)

    def test_typo_heuristic(self):
        self.assertEqual(pg.typo_count(["tihnk", "waht", "about", "else"]), 2)
        self.assertEqual(pg.typo_count(["polymarket", "sharadar", "supabase", "legs", "loop", "hold"]), 0)
        self.assertTrue(pg.known("alerts") and pg.known("tested") and pg.known("thats"))


class TestAssumption(unittest.TestCase):
    FIRE = [
        "make the auth work with supabase, i think we should migrate the session store too",
        "integrate stripe into the checkout flow, it should probably just work with the existing cart",
        "intiial is all free follow coding practice and conventions as pacific-server and site so code is maintainable "
        "no need for server fully maybe for now only thing needed is like a local supabase auth env and then all of the app wil be demo",
        "with this exact same ui and everything - create a slideshow pitch and make it a geniune pitch thats good and the pitch "
        "im envisioning is that trades is a skill that will always live and the new generation of people in trades eventually want "
        "to start their own so might as well make it easily accessible",
    ]
    SKIP = [
        "integrate stripe in src/checkout/pay.ts using the existing CartContext",
        "refactor the parser", "deploy it", "fix the typo in the readme please",
        "should i keep it running then and is it promising", "how much should i expect with the current iteration",
        "please update README.md to mention the new flag, it should say the default is off",
        "/loop 5m /foo", '<pasted_content id="1">\nintegrate x\nmaybe y\nprobably z\n</pasted_content>',
    ]

    def test_fires(self):
        for p in self.FIRE:
            self.assertTrue(pg.assumption(p), p)

    def test_skips(self):
        for p in self.SKIP:
            self.assertFalse(pg.assumption(p), p)


class TestHook(unittest.TestCase):
    def test_lines_are_short(self):
        self.assertLessEqual(len(pg.MISREAD_LINE), 220)
        self.assertLessEqual(len(pg.ASSUMPTION_LINE), 220)

    def test_emits_context_only_when_firing(self):
        rc, out = run("fix that")
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out), {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": pg.MISREAD_LINE}})
        rc, out = run("make the auth work with supabase, i think we should migrate the session store too")
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["additionalContext"], pg.ASSUMPTION_LINE)
        self.assertEqual(run("ok"), (0, ""))
        self.assertEqual(run("update README.md to mention the new flag"), (0, ""))

    def test_both_guards_join_lines(self):
        note = pg.guard("integrate stripe into the checkout flow, it should probably just work with the existing cart")
        self.assertEqual(note.split("\n"), [pg.MISREAD_LINE, pg.ASSUMPTION_LINE])

    def test_disabled_and_bad_input(self):
        self.assertEqual(run("fix that", {"AGENTMAXX_PROMPT_GUARD": "0"}), (0, ""))
        out = io.StringIO()
        with unittest.mock.patch("sys.stdin", io.StringIO("not json")), unittest.mock.patch("sys.stdout", out):
            self.assertEqual(pg.main(), 0)
        self.assertEqual(out.getvalue(), "")
        with unittest.mock.patch("sys.stdin", io.StringIO(json.dumps({"prompt": None}))), unittest.mock.patch("sys.stdout", out):
            self.assertEqual(pg.main(), 0)
        self.assertEqual(out.getvalue(), "")

    def test_fast(self):
        prompts = (TestMisread.FIRE + TestMisread.SKIP + TestAssumption.FIRE + TestAssumption.SKIP) * 5
        t0 = time.perf_counter()
        for p in prompts:
            pg.guard(p)
        self.assertLess((time.perf_counter() - t0) / len(prompts), 0.002)  # 2 ms per prompt in-process


if __name__ == "__main__":
    unittest.main()
