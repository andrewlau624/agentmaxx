import json
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from evals.doctor import apply_plan, best_uniform_ttl, compute_plan, installed_skills


class TestBestUniformTtl(unittest.TestCase):
    def test_mixed_machine_recommends_nothing(self):
        # Observed mixed bill; uniform 1h beats uniform 5m head-to-head but not observed.
        self.assertIsNone(best_uniform_ttl(1000.0, 1420.0, 1060.0))

    def test_uniform_5m_machine_gets_1h(self):
        ttl, saved = best_uniform_ttl(1400.0, 1420.0, 1060.0)
        self.assertEqual(ttl, "1h")
        self.assertAlmostEqual(saved, (1400 - 1060) / 1400)

    def test_small_gain_stays_silent(self):
        self.assertIsNone(best_uniform_ttl(1000.0, 1200.0, 980.0))


class TestComputePlan(unittest.TestCase):
    def test_statuses(self):
        settings = {"env": {"SAME": "1", "DIFF": "5m"}}
        plan = compute_plan(settings, {"SAME": "1", "DIFF": "5m", "SHELL": "x"},
                            {"SAME": "1", "DIFF": "1h", "NEW": "v", "SHELL": "y"})
        by_key = {k: s for k, _, _, s in plan["env"]}
        self.assertEqual(by_key, {"SAME": "noop", "DIFF": "conflict", "NEW": "write", "SHELL": "conflict"})

    def test_shell_value_marks_conflict_not_write(self):
        plan = compute_plan({}, {"K": "shell-val"}, {"K": "wanted"})
        self.assertEqual(plan["env"], [("K", "wanted", "shell-val (shell)", "conflict")])


class TestApplyPlan(unittest.TestCase):
    def test_writes_only_writes_and_backs_up(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            orig = {"env": {"KEEP": "1", "DIFF": "5m"}, "other": [1]}
            path.write_text(json.dumps(orig))
            plan = {"env": [("NEW", "v", None, "write"), ("DIFF", "1h", "5m", "conflict"),
                            ("KEEP", "1", "1", "noop")]}
            backup = apply_plan(path, json.loads(path.read_text()), plan)
            self.assertEqual(json.loads(backup.read_text()), orig)
            got = json.loads(path.read_text())
            self.assertEqual(got["env"], {"KEEP": "1", "DIFF": "5m", "NEW": "v"})
            self.assertEqual(got["other"], [1])

    def test_missing_file_starts_empty(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "settings.json"
            plan = {"env": [("A", "b", None, "write")]}
            apply_plan(path, {}, plan)
            self.assertEqual(json.loads(path.read_text())["env"], {"A": "b"})


class TestInstalledSkills(unittest.TestCase):
    def test_parses_frontmatter_names(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / ".claude" / "skills" / "a").mkdir(parents=True)
            (root / ".agents" / "skills" / "b").mkdir(parents=True)
            (root / ".claude" / "skills" / "a" / "SKILL.md").write_text("---\nname: alpha\n---\n")
            (root / ".agents" / "skills" / "b" / "SKILL.md").write_text("---\nname: beta\n---\n")
            (root / ".claude" / "skills" / "junk.md").write_text("name: nope\n")
            with unittest.mock.patch("pathlib.Path.home", return_value=root):
                self.assertEqual(installed_skills(), {"alpha", "beta"})


if __name__ == "__main__":
    unittest.main()
