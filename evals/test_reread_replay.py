import unittest

from evals.reread_replay import classify_reads, overlaps, span


def res(at, name, inp, size=3600):
    return ("result", at, name, inp, size)


class RereadTests(unittest.TestCase):
    def test_ranges(self):
        self.assertEqual(span({}), (1, float("inf")))
        self.assertEqual(span({"offset": 10, "limit": 5}), (10, 14))
        self.assertTrue(overlaps((1, 50), (40, 90)))
        self.assertFalse(overlaps((1, 50), (51, 90)))

    def test_classify_and_invalidate(self):
        r = {"file_path": "/a/b.py", "offset": 1, "limit": 100}
        ev = [res(1, "Read", r), res(2, "Read", r), res(3, "Read", {**r, "offset": 50, "limit": 100}),
              res(4, "Read", {**r, "offset": 5000, "limit": 10}), res(5, "Edit", r), res(6, "Read", r),
              res(7, "Bash", {"command": "sed -i s/a/b/ /a/b.py"}), res(8, "Read", r)]
        self.assertEqual([k[0] for k in classify_reads(ev)], ["first", "exact", "overlap", "disjoint", "first", "first"])


if __name__ == "__main__":
    unittest.main()
