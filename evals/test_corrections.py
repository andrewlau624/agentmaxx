import json
import tempfile
import unittest
from pathlib import Path

from evals import corrections


def record(text, ts="2026-10-01T10:00:00Z", **extra):
    return json.dumps({"type": "user", "timestamp": ts, "entrypoint": "cli", "message": {"content": text}, **extra})


class TestCorrections(unittest.TestCase):
    def test_typed_corrections_only(self):
        root = Path(tempfile.mkdtemp())
        (root / "p").mkdir()
        (root / "p" / "a.jsonl").write_text("\n".join([
            record("no, you forgot to run the migration tests"),
            record("what if instead of polling we stream it"),
            record("<system-reminder>no</system-reminder>"),
            json.dumps({"type": "user", "timestamp": "2026-10-01T10:00:00Z",
                        "message": {"content": [{"type": "tool_result", "content": "no"}]}}),
        ]))
        (root / "p" / "b.jsonl").write_text(record("stop, you forgot the migration tests again", ts="2026-10-02T10:00:00Z"))
        (root / "bench").mkdir()
        (root / "bench" / "c.jsonl").write_text(record("no", entrypoint="sdk-cli", promptSource="sdk"))
        stats = corrections.scan(10_000, root)
        self.assertEqual(sorted(t for _, _, t in stats["corrections"]),
                         ["no, you forgot to run the migration tests", "stop, you forgot the migration tests again"])
        self.assertEqual(sum(n for _, n in stats["weeks"].values()), 3)
        self.assertEqual(len(stats["repeats"]), 1)


if __name__ == "__main__":
    unittest.main()
