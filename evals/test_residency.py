import json
import tempfile
import unittest
from pathlib import Path

from evals import residency
from evals.doctor import simulate_ttl


def usage(read, write):
    return {"input_tokens": 0, "cache_read_input_tokens": read, "cache_creation_input_tokens": write, "output_tokens": 0}


def transcript(path: Path, records: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    return path


def assistant(mid, t, u, tool=None):
    content = [{"type": "tool_use", "id": tool[0], "name": tool[1], "input": tool[2]}] if tool else []
    return {"type": "assistant", "timestamp": t, "message": {"id": mid, "usage": u, "content": content}}


def result(tool_id, text):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": tool_id, "content": text}]}}


class TestResidency(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "s.jsonl"

    def tearDown(self):
        self.dir.cleanup()

    def test_repeat_read_counts_only_unchanged_file(self):
        read = ("Read", {"file_path": "/a.py"})
        s = residency.load(transcript(self.path, [
            assistant("m1", "2026-10-01T00:00:00Z", usage(0, 1000), ("t1", *read)), result("t1", "x" * 360),
            assistant("m2", "2026-10-01T00:00:10Z", usage(1000, 100), ("t2", *read)), result("t2", "x" * 360),
            assistant("m3", "2026-10-01T00:00:20Z", usage(1100, 100), ("t3", "Edit", {"file_path": "/a.py"})),
            result("t3", "ok"),
            assistant("m4", "2026-10-01T00:00:30Z", usage(1200, 100), ("t4", *read)), result("t4", "x" * 360),
            assistant("m5", "2026-10-01T00:00:40Z", usage(1300, 100)),
        ]))
        r = residency.analyze([s])
        self.assertEqual(r["reread_calls"]["all"], 3)
        self.assertEqual(r["reread_calls"]["dup"], 1)

    def test_long_gap_counts_as_cache_rewrite(self):
        s = residency.load(transcript(self.path, [
            assistant("m1", "2026-10-01T00:00:00Z", usage(0, 50_000)),
            assistant("m2", "2026-10-01T02:00:00Z", usage(0, 60_000)),
        ]))
        self.assertEqual(residency.analyze([s])["busts"]["idle>1h"], 1)

    def test_composition_charges_hidden_output_as_thinking(self):
        out = lambda u, n: {**u, "output_tokens": n}
        s = residency.load(transcript(self.path, [
            assistant("m1", "2026-10-01T00:00:00Z", out(usage(0, 10_000), 1_000)),
            assistant("m2", "2026-10-01T00:00:05Z", out(usage(10_000, 1_500), 0)),
        ]))
        parts = residency.composition([s])
        # m1 has no visible content, so its 1,000 output tokens are thinking, resident on 1 later request
        self.assertEqual(parts["thinking"], 1_000)
        self.assertEqual(parts["prefix (system, tools, summary)"], 10_000)
        self.assertEqual(parts["tool results, prompts, injections"], 0)

    def test_ttl_replay_turns_gaps_into_rewrites(self):
        s = residency.load(transcript(self.path, [
            assistant("m1", "2026-10-01T00:00:00Z", usage(0, 10_000)),
            assistant("m2", "2026-10-01T00:20:00Z", usage(10_000, 0)),
        ]))
        # 20-minute gap: hit under 1h (10k write at 2 + 10k read at 0.1), miss under 5m (20k writes at 1.25)
        self.assertEqual(simulate_ttl([s], 3600), 21_000)
        self.assertEqual(simulate_ttl([s], 300), 25_000)


if __name__ == "__main__":
    unittest.main()
