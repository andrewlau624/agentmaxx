import unittest
from shopkit.inventory import Inventory
class T(unittest.TestCase):
    def test_reserve_to_zero(self):
        inv = Inventory({"X": 3})
        self.assertTrue(inv.reserve("X", 3)); self.assertEqual(inv.available("X"), 0)
        self.assertFalse(inv.reserve("X", 1))
    def test_over(self):
        self.assertFalse(Inventory({"X": 2}).reserve("X", 3))
