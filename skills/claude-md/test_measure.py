import importlib.util
import pathlib
import tempfile
import unittest

HERE = pathlib.Path(__file__).parent
spec = importlib.util.spec_from_file_location("measure", HERE / "measure.py")
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)

DOC = """# Project memory

Short intro.

## Objective (user, 2026-10-01)
- Make money.
- Never trade without a backtest.

## Session log
2026-10-02: tried X, got 0.3%.
2026-10-03: tried Y, got 0.1%.
""" + "\n".join(f"- row {i} value {i * 3}" for i in range(200)) + """

### Data-buy rule (user, permanent)
- Never buy data over $50 without asking.

## 4. Methodology standards (non-negotiable)
- Pre-register every test.
- Report the CI, not the point estimate.
"""


class TestMeasure(unittest.TestCase):
    def test_classification(self):
        secs = measure.sections(DOC)
        verdicts = {s["heading"]: s["verdict"] for s in secs}
        self.assertEqual(verdicts["Objective (user, 2026-10-01)"], "keep")
        self.assertEqual(verdicts["Session log"], "move")
        self.assertEqual(verdicts["4. Methodology standards (non-negotiable)"], "keep")
        self.assertEqual(measure.hoisted(secs)[0][0], "Data-buy rule (user, permanent)")

    def test_apply_keeps_every_line_and_a_backup(self):
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d)
            path = root / "CLAUDE.md"
            path.write_text(DOC)
            secs = measure.sections(DOC)
            measure.apply(path, secs, root / "docs" / "memory")
            new = path.read_text()
            moved = "".join(p.read_text() for p in (root / "docs" / "memory").glob("[0-9]*.md"))
            backups = list((root / "docs" / "memory").glob("CLAUDE.md.*.before-diet"))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), DOC)
            for line in DOC.splitlines():
                if line.strip() and not line.startswith("## "):
                    self.assertIn(line.strip(), new + moved, line)
            self.assertIn("Never buy data over $50", new)          # hoisted user rule
            self.assertNotIn("row 150 value 450", new)             # log moved out
            self.assertIn("docs/memory/INDEX.md", new)
            self.assertIn("Session log", (root / "docs" / "memory" / "INDEX.md").read_text())
            self.assertLess(len(new), len(DOC) / 4)


if __name__ == "__main__":
    unittest.main()
