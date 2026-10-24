import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

HERE = pathlib.Path(__file__).parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rl = load("research_log")


def entry(kind, text, session, ts=1.0):
    return dict(kind=kind, ts=ts, session=session, text=text)


class TestNormalise(unittest.TestCase):
    def test_strips_site_punctuation_and_stopwords(self):
        self.assertEqual(rl.normalise("site:usethinkscript.com RSI-divergence backtest, for the win!"),
                         frozenset({"rsi", "divergence", "backtest", "win"}))

    def test_jaccard(self):
        self.assertEqual(rl.jaccard(frozenset("abc"), frozenset("abd")), 0.5)
        self.assertEqual(rl.jaccard(frozenset(), frozenset()), 0.0)


class TestDecide(unittest.TestCase):
    def test_same_session_needs_0_8(self):
        prior = entry("search", "schwab margin requirement leveraged etf tqqq maintenance", "s1")
        self.assertIs(rl.decide([prior], "s1", "WebSearch", "schwab margin requirement leveraged etf tqqq maintenance percent"), prior)
        self.assertIsNone(rl.decide([prior], "s1", "WebSearch", "schwab margin leveraged etf tqqq maintenance percent rules"))

    def test_cross_session_needs_0_6(self):
        prior = entry("search", "schwab ira limited margin unsettled funds good faith violation", "s1")
        self.assertIs(rl.decide([prior], "s2", "WebSearch", "schwab ira limited margin unsettled funds good faith violation same day"), prior)
        self.assertIsNone(rl.decide([prior], "s2", "WebSearch", "fidelity ira cash account settlement rules trading"))

    def test_entity_swap_in_same_session_passes(self):
        prior = entry("search", "First Bank completes second-step conversion", "s1")
        self.assertIsNone(rl.decide([prior], "s1", "WebSearch", "Second Savings completes second-step conversion"))

    def test_angle_change_passes(self):
        prior = entry("search", "kalshi liquidity incentive program rules dollars per day market maker", "s1")
        self.assertIsNone(rl.decide([prior], "s2", "WebSearch", "kalshi liquidity incentive program market maker earnings reddit"))
        self.assertIsNone(rl.decide([prior], "s2", "WebSearch", "kalshi liquidity incentive program market maker limitations"))

    def test_short_queries_never_denied(self):
        prior = entry("search", "schwab margin", "s1")
        self.assertIsNone(rl.decide([prior], "s1", "WebSearch", "schwab margin"))

    def test_each_prior_denied_once_per_session(self):
        prior = entry("search", "esports betting market efficiency favourite longshot bias study", "s1", ts=1.0)
        q = "esports betting market efficiency favourite longshot bias csgo study"
        items = [prior]
        self.assertIs(rl.decide(items, "s2", "WebSearch", q), prior)
        items.append(dict(kind="deny", ts=2.0, session="s2", text=q, prior_ts=1.0, prior_text=prior["text"]))
        self.assertIsNone(rl.decide(items, "s2", "WebSearch", q))
        # a third session still gets the warning
        self.assertIs(rl.decide(items, "s3", "WebSearch", q), prior)

    def test_fetch_dedupes_exact_url_same_session_only(self):
        prior = entry("fetch", "https://docs.example.com/a", "s1")
        self.assertIs(rl.decide([prior], "s1", "WebFetch", "https://docs.example.com/a"), prior)
        self.assertIsNone(rl.decide([prior], "s1", "WebFetch", "https://docs.example.com/b"))
        self.assertIsNone(rl.decide([prior], "s2", "WebFetch", "https://docs.example.com/a"))


class TestHook(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name) / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "--allow-empty", "-m", "root"],
                       cwd=self.repo, check=True)
        self.old_home, rl.HOME = rl.HOME, pathlib.Path(self.tmp.name) / "research"

    def tearDown(self):
        rl.HOME = self.old_home
        self.tmp.cleanup()

    def run_hook(self, tool, inp, session="s1", env=None):
        event = dict(hook_event_name="PreToolUse", tool_name=tool, tool_input=inp, session_id=session, cwd=str(self.repo))
        out = io.StringIO()
        with unittest.mock.patch.object(sys, "stdin", io.StringIO(json.dumps(event))), \
                unittest.mock.patch.object(sys, "stdout", out), \
                unittest.mock.patch.dict(os.environ, env or {}, clear=False):
            self.assertEqual(rl.hook(), 0)
        return json.loads(out.getvalue()) if out.getvalue() else None

    def test_allows_and_logs_then_denies_then_lets_rerun_through(self):
        q = "schwab margin requirement leveraged etf tqqq maintenance"
        self.assertIsNone(self.run_hook("WebSearch", {"query": q}))
        self.assertIsNone(self.run_hook("WebSearch", {"query": "coinbase nano bitcoin perpetual futures funding rate"}))
        out = self.run_hook("WebSearch", {"query": q + " percent"}, session="s2")
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["hookEventName"], "PreToolUse")
        self.assertEqual(hso["permissionDecision"], "deny")
        self.assertIn("Near-duplicate of a query already run", hso["permissionDecisionReason"])
        self.assertIn(q, hso["permissionDecisionReason"])
        self.assertIsNone(self.run_hook("WebSearch", {"query": q + " percent"}, session="s2"))
        kinds = [i["kind"] for i in rl.load(rl.path_for(str(self.repo)))]
        self.assertEqual(kinds, ["search", "search", "deny", "search"])

    def test_fetch_denied_only_on_exact_repeat(self):
        self.assertIsNone(self.run_hook("WebFetch", {"url": "https://x.io/docs/1", "prompt": "p"}))
        self.assertIsNone(self.run_hook("WebFetch", {"url": "https://x.io/docs/2", "prompt": "p"}))
        out = self.run_hook("WebFetch", {"url": "https://x.io/docs/1", "prompt": "again"})
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_disabled_by_env(self):
        q = "schwab margin requirement leveraged etf tqqq maintenance"
        self.assertIsNone(self.run_hook("WebSearch", {"query": q}))
        self.assertIsNone(self.run_hook("WebSearch", {"query": q}, env={"AGENTMAXX_RESEARCH_LOG": "0"}))
        self.assertEqual(len(rl.load(rl.path_for(str(self.repo)))), 1)

    def test_other_events_ignored(self):
        event = dict(hook_event_name="PostToolUse", tool_name="WebSearch", tool_input={"query": "a b c d"}, cwd=str(self.repo))
        with unittest.mock.patch.object(sys, "stdin", io.StringIO(json.dumps(event))):
            self.assertEqual(rl.hook(), 0)
        self.assertEqual(rl.load(rl.path_for(str(self.repo))), [])

    def test_cap_drops_oldest(self):
        old, rl.MAX_ENTRIES = rl.MAX_ENTRIES, 5
        try:
            path = rl.path_for(str(self.repo))
            for i in range(8):
                rl.append(path, entry("search", f"query {i}", "s1", ts=i))
            self.assertEqual([i["text"] for i in rl.load(path)], [f"query {i}" for i in range(3, 8)])
        finally:
            rl.MAX_ENTRIES = old

    def test_recent_lists_last_n(self):
        for i in range(4):
            self.run_hook("WebSearch", {"query": f"distinct topic number {i} alpha{i} beta{i} gamma{i}"})
        text = rl.recent(str(self.repo), 2)
        self.assertEqual(len(text.splitlines()), 2)
        self.assertIn("alpha3", text)
        self.assertNotIn("alpha1", text)
        self.assertEqual(rl.recent(str(self.tmp.name), 5), "(no research logged for this repo)")

    def test_key_shared_across_clones_and_set_outside_git(self):
        clone = pathlib.Path(self.tmp.name) / "clone"
        subprocess.run(["git", "clone", "-q", str(self.repo), str(clone)], check=True)
        self.assertEqual(rl.repo_key(str(self.repo)), rl.repo_key(str(clone)))
        self.assertTrue(rl.repo_key(self.tmp.name).startswith("dir-"))


if __name__ == "__main__":
    unittest.main()
