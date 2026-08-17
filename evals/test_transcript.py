import json
import tempfile
import unittest
from pathlib import Path

from evals.transcript import parse_session, parse_sessions, total


def write_transcript(path: Path, turns: list[dict]) -> None:
    lines = [json.dumps({"message": {"usage": usage}}) for usage in turns]
    path.write_text("\n".join(lines) + "\n")


class TestParseSession(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "session.jsonl"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sums_usage_across_turns(self):
        write_transcript(
            self.path,
            [
                {
                    "input_tokens": 100,
                    "cache_creation_input_tokens": 50,
                    "cache_read_input_tokens": 200,
                    "output_tokens": 10,
                },
                {
                    "input_tokens": 20,
                    "cache_creation_input_tokens": 0,
                    "cache_read_input_tokens": 400,
                    "output_tokens": 5,
                },
            ],
        )

        usage = parse_session(self.path)

        self.assertEqual(usage.turns, 2)
        self.assertEqual(usage.raw, 120)
        self.assertEqual(usage.cache_write, 50)
        self.assertEqual(usage.cache_read, 600)
        self.assertEqual(usage.output, 15)

    def test_ignores_lines_without_usage(self):
        self.path.write_text(
            json.dumps({"message": {"content": []}}) + "\n"
            + json.dumps({"type": "summary"}) + "\n"
        )

        self.assertEqual(parse_session(self.path).turns, 0)

    def test_skips_malformed_lines(self):
        self.path.write_text("not json at all\n\n")

        self.assertEqual(parse_session(self.path).turns, 0)

    def test_missing_usage_fields_default_to_zero(self):
        write_transcript(self.path, [{}])

        usage = parse_session(self.path)

        self.assertEqual(usage.turns, 1)
        self.assertEqual(usage.raw, 0)
        self.assertEqual(usage.weighted_cost, 0)

    def test_null_usage_fields_default_to_zero(self):
        write_transcript(self.path, [{"input_tokens": None, "output_tokens": 4}])

        usage = parse_session(self.path)

        self.assertEqual(usage.raw, 0)
        self.assertEqual(usage.output, 4)

    def test_weighted_cost_applies_documented_weights(self):
        write_transcript(
            self.path,
            [
                {
                    "input_tokens": 100,
                    "cache_creation_input_tokens": 100,
                    "cache_read_input_tokens": 100,
                    "output_tokens": 100,
                }
            ],
        )

        # 100*1.0 + 100*1.25 + 100*0.1 + 100*5.0
        self.assertEqual(parse_session(self.path).weighted_cost, 735.0)

    def test_cheap_cache_reads_beat_expensive_output(self):
        """A run can read far more tokens and still cost less."""
        heavy_reads = Path(self.temp_dir.name) / "reads.jsonl"
        heavy_output = Path(self.temp_dir.name) / "output.jsonl"
        write_transcript(heavy_reads, [{"cache_read_input_tokens": 100_000}])
        write_transcript(heavy_output, [{"output_tokens": 10_000}])

        self.assertLess(
            parse_session(heavy_reads).weighted_cost,
            parse_session(heavy_output).weighted_cost,
        )


class TestAggregate(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_total_sums_multiple_sessions(self):
        first = Path(self.temp_dir.name) / "a.jsonl"
        second = Path(self.temp_dir.name) / "b.jsonl"
        write_transcript(first, [{"input_tokens": 10, "output_tokens": 1}])
        write_transcript(second, [{"input_tokens": 20, "output_tokens": 2}])

        aggregate = total(parse_sessions([first, second]))

        self.assertEqual(aggregate.raw, 30)
        self.assertEqual(aggregate.output, 3)
        self.assertEqual(aggregate.turns, 2)

    def test_total_of_no_sessions_is_zero(self):
        self.assertEqual(total([]).weighted_cost, 0)


if __name__ == "__main__":
    unittest.main()
