import unittest, json, tempfile, os
from shopkit.order import Order
from shopkit import report, store, tax
from shopkit.money import to_money
class T(unittest.TestCase):
    def test_normalized(self):
        o = Order("R1", " ca ").add("KB-01")
        self.assertEqual(o.region, "CA")
        self.assertEqual(o.tax(), to_money("3.62"))
        self.assertIn('"region": "CA"', report.render([o]))
    def test_unknown_rejected(self):
        with self.assertRaises(ValueError):
            Order("R2", "ZZ")
    def test_zero_rate_region_ok(self):
        self.assertEqual(Order("R3", "or").add("MUG-7").tax(), to_money(0))
    def test_store_roundtrip(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, "o.json")
        json.dump([{"id": "Z", "region": "tx ", "lines": [["MS-02", 1]]}], open(p, "w"))
        self.assertEqual(store.load_orders(p)[0].region, "TX")
        bad = os.path.join(d, "b.json"); json.dump([{"id": "Q", "region": "XX", "lines": []}], open(bad, "w"))
        with self.assertRaises(ValueError):
            store.load_orders(bad)
    def test_rate_for_unknown_raises(self):
        with self.assertRaises(ValueError):
            tax.rate_for("ZZ")
