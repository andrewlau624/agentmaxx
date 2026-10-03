import unittest

from evals.tells import RULES, SOURCES, score

SLOP = """## Overview

Certainly! This tool stands as a testament to careful design, highlighting the power of automation.
It's not just a linter — it's a platform. Experts say it plays a pivotal role, and it delves into the intricate details.

- **Speed:** fast
- **Safety:** safe

I hope this helps!
"""

PLAIN = """I wrote this because the old script took nine minutes on our CI box and nobody knew why.
It turned out to be a DNS lookup in a loop. Now it caches the result per host. Runs in 40s.
If you run it on a laptop with no network, set OFFLINE=1 or it will hang for a while first.
"""


class TestTells(unittest.TestCase):
    def test_every_rule_names_its_evidence(self):
        for kind, rules in RULES.items():
            for name in rules:
                self.assertTrue(SOURCES[kind].get(name), f"{kind}:{name} has no source")

    def test_prose_slop_scores_high_and_plain_scores_zero(self):
        slop, plain = score(SLOP, "prose"), score(PLAIN, "prose")
        for rule in ("significance padding", "participle tail", "negative parallelism", "vague attribution",
                     "GPT-era word", "chatbot phrasing", "inline-header list item"):
            self.assertIn(rule, slop["hits"], rule)
        self.assertEqual(plain["count"], 0)

    def test_code_fences_and_inline_code_are_ignored_in_prose(self):
        r = score("Run `delve --pivotal` then:\n\n```\ntapestry()\n```\n", "prose")
        self.assertEqual(r["count"], 0)

    def test_em_dash_counts_only_above_the_human_rate(self):
        self.assertNotIn("spaced em dash", score("one — two " + "word " * 400, "prose")["hits"])
        self.assertIn("spaced em dash", score("a — b — c — d — e", "prose")["hits"])

    def test_ui_template(self):
        html = ('<div class="bg-gradient-to-r from-indigo-500 to-purple-600">'
                '<h1 class="bg-clip-text text-transparent">Unlock the power of AI</h1>'
                '<div class="rounded-2xl shadow-lg p-6 backdrop-blur">✨</div></div>'
                '<style>body{background:#f6f1e7;color:#111111} a{color:#8b5cf6}</style>')
        hits = score(html, "ui")["hits"]
        for rule in ("purple gradient", "gradient text", "hype copy", "large uniform radius + shadow", "glassmorphism",
                     "purple color", "cream background (second-order default)", "tinted near-black"):
            self.assertIn(rule, hits, rule)

    def test_neutral_ui_is_clean(self):
        html = '<main style="font-family: Charter, serif; background:#ffffff; color:#1d1d1f"><h1>Orders</h1></main>'
        self.assertEqual(score(html, "ui")["count"], 0)

    def test_code_diff_scores_added_lines_only(self):
        diff = ("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1,5 @@\n"
                "-    # TODO: implement\n+def load(x):\n+    try:\n+        return x()\n"
                "+    except Exception:\n+        pass\n")
        r = score(diff, "code")
        self.assertIn("swallowed exception", r["hits"])
        self.assertNotIn("placeholder", r["hits"])

    def test_commit_message(self):
        self.assertIn("chatbot phrasing", score("Fix parser\n\nLet me know if you want more tests.\n", "commit")["hits"])
        self.assertEqual(score("fix tax on discounted orders\n\nCo-Authored-By: X <x@y>\n", "commit")["count"], 0)


if __name__ == "__main__":
    unittest.main()
