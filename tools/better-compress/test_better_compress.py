import importlib.util
import json
import unittest
from pathlib import Path

path = Path(__file__).with_name("better_compress.py")
spec = importlib.util.spec_from_file_location("better_compress_impl", path)
better_compress = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(better_compress)


def rows(n=300):
    return [{"id": i, "status": "ok", "region": "us-east-1",
             "message": "request completed successfully", "ignore": None} for i in range(n)]


BIG_JSON = json.dumps(rows(), indent=2)
BIG_LOG = "".join(f"[10:{m:02d}:00] INFO worker: compiled module_{m:03d} ok\n" * 4 for m in range(200))
BIG_DIFF = ("diff --git a/f.py b/f.py\n+++ b/f.py\n@@ -1,3 +1,3 @@\n" + "-old\n+new\n" * 400)


class TestClassify(unittest.TestCase):
    def test_json(self):
        self.assertEqual(better_compress.classify(BIG_JSON), "json")

    def test_broken_json_is_not_json(self):
        self.assertNotEqual(better_compress.classify("{not json"), "json")

    def test_diff(self):
        self.assertEqual(better_compress.classify(BIG_DIFF), "diff")

    def test_timestamped_log(self):
        self.assertEqual(better_compress.classify(BIG_LOG), "log")

    def test_prose(self):
        self.assertEqual(better_compress.classify("hello " * 2000), "text")


class TestCrushJson(unittest.TestCase):
    def test_row_header_keeps_count_schema_and_drops_null_keys(self):
        out = better_compress.crush_json_text(BIG_JSON, 6000)
        self.assertIn("[300 rows]", out)
        self.assertIn("status:str", out)
        self.assertNotIn("ignore", out)
        self.assertLess(len(out), len(BIG_JSON))

    def test_omitted_rows_noted_with_tail_kept(self):
        out = better_compress.crush_json_text(BIG_JSON, 1000)
        self.assertIn("rows omitted", out)
        self.assertIn('"id":299', out)

    def test_small_json_compacts(self):
        out = better_compress.crush_json_text('{"a": 1, "b": [1, 2]}', 6000)
        self.assertEqual(json.loads(out), {"a": 1, "b": [1, 2]})

    def test_big_dict_summarizes_per_key(self):
        obj = {f"k{i}": "x" * 500 for i in range(50)}
        out = better_compress.crush_json_text(json.dumps(obj), 1000)
        self.assertIn("k0:", out)
        self.assertIn("omitted", out)

    def test_non_json_returns_none(self):
        self.assertIsNone(better_compress.crush_json_text("nope", 100))


class TestCompressText(unittest.TestCase):
    def test_small_input_passes_through(self):
        out, info = better_compress.compress_text("tiny", budget=6000)
        self.assertEqual((out, info["backend"]), ("tiny", "passthrough"))

    def test_builtin_shrinks_log(self):
        out, info = better_compress.compress_text(BIG_LOG, command="make", budget=2000,
                                                  backend="builtin", spill=False)
        self.assertEqual(info["backend"], "builtin")
        self.assertLess(len(out), len(BIG_LOG))
        self.assertIn("module_199", out)  # tail kept

    def test_builtin_crushes_json(self):
        out, info = better_compress.compress_text(BIG_JSON, budget=2000, backend="builtin", spill=False)
        self.assertEqual(info["kind"], "json")
        self.assertIn("[300 rows]", out)

    def test_failed_backend_falls_back_to_builtin(self):
        real = better_compress.load_headroom
        better_compress._headroom_tried = True
        better_compress._headroom = None
        try:
            out, info = better_compress.compress_text(BIG_JSON, budget=2000, backend="headroom", spill=False)
            self.assertEqual(info["backend"], "builtin")
            self.assertIn("[300 rows]", out)
        finally:
            better_compress._headroom_tried = False
            better_compress._headroom = None

    def test_never_empty_never_expands(self):
        blob = "".join(f"line {i} {'x' * 50}\n" for i in range(500))
        out, _ = better_compress.compress_text(blob, budget=2000, backend="builtin", spill=False)
        self.assertTrue(out.strip())
        self.assertLess(len(out), len(blob))

    def test_result_fits_budget(self):
        out, _ = better_compress.compress_text(BIG_LOG, budget=1000, backend="builtin", spill=False)
        self.assertLessEqual(len(out), 1000 + 300)  # budget plus the note line

    def test_spill_pointer_names_a_real_file(self):
        out, _ = better_compress.compress_text(BIG_LOG, budget=1000, backend="builtin", spill=True)
        m = [w for w in out.split() if w.startswith("/tmp/") or "/agentmaxx-out/" in w]
        self.assertTrue(m and Path(m[0].rstrip(")")).is_file())


class TestRun(unittest.TestCase):
    def test_wrap_argv_only_for_covered_commands(self):
        self.assertEqual(better_compress.wrap_argv(["git", "log"], "/bin/lowfat"),
                         ["/bin/lowfat", "git", "log"])
        self.assertEqual(better_compress.wrap_argv(["rm", "-rf", "x"], "/bin/lowfat"), ["rm", "-rf", "x"])
        self.assertEqual(better_compress.wrap_argv(["git", "log"], None), ["git", "log"])

    def test_run_command_captures(self):
        res = better_compress.run_command(["echo", "hi"])
        self.assertIn("hi", res["text"])
        self.assertEqual(res["returncode"], 0)

    def test_run_command_missing_is_fail_open(self):
        res = better_compress.run_command(["/nonexistent-binary-xyz"])
        self.assertEqual(res["returncode"], 127)
        self.assertTrue(res["text"])


if __name__ == "__main__":
    unittest.main()
