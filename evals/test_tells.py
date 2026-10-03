import unittest

from evals.tells import score

SLOP = """## Overview

Great question! This robust tool seamlessly integrates with your workflow, highlighting the power of automation.
It's not just a linter, it's a complete platform. In today's fast-paced world, it is crucial to leverage it.

- **Speed:** fast
- **Safety:** safe

Hope this helps! Let me know if you want more.
"""

PLAIN = """I wrote this because the old script took nine minutes on our CI box and nobody knew why.
It turned out to be a DNS lookup in a loop. Now it caches the result per host. Runs in 40s.
If you run it on a laptop with no network, set OFFLINE=1 or it will hang for a while first.
"""


class TestTells(unittest.TestCase):
    def test_prose_slop_scores_high_and_plain_scores_zero(self):
        slop, plain = score(SLOP, "prose"), score(PLAIN, "prose")
        for rule in ("filler word", "not X, it's Y", "opener", "closing offer", "bold-label bullet", "participle tail"):
            self.assertIn(rule, slop["hits"], rule)
        self.assertEqual(plain["count"], 0)

    def test_code_fences_and_inline_code_are_ignored_in_prose(self):
        r = score("Run `leverage --robust` then:\n\n```\nseamless()\n```\n", "prose")
        self.assertEqual(r["count"], 0)

    def test_single_em_dash_is_punctuation_but_a_pileup_counts(self):
        self.assertNotIn("em dash", score("one — two " + "word " * 100, "prose")["hits"])
        self.assertIn("em dash", score("a — b — c — d — e", "prose")["hits"])

    def test_ui_template(self):
        html = ('<div class="bg-gradient-to-r from-indigo-500 to-purple-600">'
                '<h1 class="bg-clip-text text-transparent">Unlock the power of AI</h1>'
                '<div class="rounded-2xl shadow-lg p-6 hover:-translate-y-1">✨</div></div>')
        hits = score(html, "ui")["hits"]
        for rule in ("purple/indigo gradient", "gradient text", "template copy", "rounded-2xl + shadow card", "hover lift"):
            self.assertIn(rule, hits, rule)

    def test_code_diff_scores_added_lines_only(self):
        diff = ("diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1,4 @@\n"
                "-    # loop through items\n+def process_data(x):\n+    try:\n+        return x()\n"
                "+    except Exception:\n+        pass\n")
        r = score(diff, "code")
        self.assertIn("generic name", r["hits"])
        self.assertIn("swallowed exception", r["hits"])
        self.assertNotIn("comment restates code", r["hits"])

    def test_commit_message(self):
        self.assertIn("this commit", score("This commit adds a feature\n", "commit")["hits"])
        self.assertEqual(score("fix tax on discounted orders\n\nCo-Authored-By: X <x@y>\n", "commit")["count"], 0)


if __name__ == "__main__":
    unittest.main()
