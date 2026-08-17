import json
import tempfile
import unittest
from pathlib import Path

from evals.compare import compare_arms


def write_transcript(path: Path, turns: list[dict]) -> None:
    lines = [json.dumps({"message": {"usage": usage}}) for usage in turns]
    path.write_text("\n".join(lines) + "\n")


class TestCompareArms(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.control = Path(self.temp_dir.name) / "control.jsonl"
        self.treatment = Path(self.temp_dir.name) / "treatment.jsonl"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_reports_weighted_savings(self):
        write_transcript(self.control, [{"cache_read_input_tokens": 1000}])
        write_transcript(self.treatment, [{"cache_read_input_tokens": 500}])

        result = compare_arms([self.control], [self.treatment])

        self.assertEqual(result["control"]["cache_read"], 1000)
        self.assertEqual(result["treatment"]["cache_read"], 500)
        self.assertEqual(result["weighted_savings_pct"], 50.0)

    def test_more_cached_reads_can_still_be_cheaper(self):
        """The reason this reports a weighted index, not token counts."""
        write_transcript(
            self.control,
            [{"cache_creation_input_tokens": 400_000, "output_tokens": 7_000}],
        )
        write_transcript(
            self.treatment,
            [{"cache_creation_input_tokens": 186_000, "output_tokens": 6_000}],
        )

        result = compare_arms([self.control], [self.treatment])

        self.assertGreater(result["weighted_savings_pct"], 0)

    def test_regression_reports_negative_savings(self):
        write_transcript(self.control, [{"output_tokens": 100}])
        write_transcript(self.treatment, [{"output_tokens": 200}])

        result = compare_arms([self.control], [self.treatment])

        self.assertEqual(result["weighted_savings_pct"], -100.0)

    def test_arms_may_hold_several_transcripts(self):
        extra = Path(self.temp_dir.name) / "control-2.jsonl"
        write_transcript(self.control, [{"output_tokens": 100}])
        write_transcript(extra, [{"output_tokens": 100}])
        write_transcript(self.treatment, [{"output_tokens": 100}])

        result = compare_arms([self.control, extra], [self.treatment])

        self.assertEqual(result["control"]["output"], 200)
        self.assertEqual(result["control"]["turns"], 2)

    def test_reports_cache_hit_rate_per_arm(self):
        write_transcript(
            self.control,
            [
                {
                    "cache_creation_input_tokens": 100,
                    "cache_read_input_tokens": 100,
                }
            ],
        )
        write_transcript(
            self.treatment,
            [
                {
                    "cache_creation_input_tokens": 100,
                    "cache_read_input_tokens": 900,
                }
            ],
        )

        result = compare_arms([self.control], [self.treatment])

        self.assertEqual(result["control"]["cache_hit_rate"], 0.5)
        self.assertEqual(result["treatment"]["cache_hit_rate"], 0.9)

    def test_requires_both_arms_nonempty(self):
        write_transcript(self.control, [{"output_tokens": 1}])

        with self.assertRaises(ValueError):
            compare_arms([], [self.control])

        with self.assertRaises(ValueError):
            compare_arms([self.control], [])


if __name__ == "__main__":
    unittest.main()
