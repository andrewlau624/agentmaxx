import unittest, io, contextlib, csv, json, tempfile, os
from shopkit.order import Order
from shopkit import report
class T(unittest.TestCase):
    def orders(self):
        return [Order("A1","OR").add("MUG-7",2), Order("A2","CA").add("BK-10")]
    def test_render_csv(self):
        out = report.render(self.orders(), "csv")
        rows = list(csv.reader(io.StringIO(out)))
        self.assertEqual(rows[0], ["order_id","region","subtotal","discount","tax","total"])
        self.assertEqual(rows[1][0], "A1"); self.assertEqual(rows[1][5], "16.50")
        self.assertEqual(len([r for r in rows if r]), 3)
    def test_cli_csv(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "o.json")
        json.dump([{"id":"Z9","region":"TX","lines":[["MS-02",1]]}], open(p,"w"))
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            report.main([p, "--format", "csv"])
        self.assertIn("Z9,TX,19.50", buf.getvalue())
    def test_json_still_works(self):
        self.assertEqual(json.loads(report.render(self.orders()))["count"], 2)
