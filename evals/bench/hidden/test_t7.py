import unittest, warnings
from shopkit.inventory import Inventory
class T(unittest.TestCase):
    def test_all_or_nothing(self):
        inv = Inventory({"A": 5, "B": 2})
        self.assertFalse(inv.reserve_many({"A": 3, "B": 3}))
        self.assertEqual(inv.available("A"), 5); self.assertEqual(inv.available("B"), 2)
    def test_success(self):
        inv = Inventory({"A": 5, "B": 2})
        self.assertTrue(inv.reserve_many({"A": 2, "B": 1}))
        self.assertEqual(inv.available("A"), 3); self.assertEqual(inv.available("B"), 1)
    def test_exact_stock(self):
        inv = Inventory({"A": 3, "B": 1})
        self.assertTrue(inv.reserve_many({"A": 3, "B": 1}))
        self.assertEqual(inv.available("A"), 0); self.assertEqual(inv.available("B"), 0)
        self.assertFalse(inv.reserve_many({"A": 1}))
    def test_rollback_keeps_prior_reservations(self):
        inv = Inventory({"A": 4, "B": 1})
        self.assertTrue(inv.reserve("A", 1))
        self.assertFalse(inv.reserve_many({"A": 2, "B": 2}))
        self.assertEqual(inv.available("A"), 3); self.assertEqual(inv.available("B"), 1)
    def test_reserve_last_unit_one_by_one(self):
        # invariant also encoded by the visible tests: stock can be reserved down to exactly zero
        inv = Inventory({"KB-01": 400})
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for _ in range(400):
                self.assertTrue(inv.reserve("KB-01", 1))
        self.assertEqual(inv.available("KB-01"), 0)
        self.assertFalse(inv.reserve("KB-01", 1))
    def test_empty(self):
        self.assertTrue(Inventory({}).reserve_many({}))
