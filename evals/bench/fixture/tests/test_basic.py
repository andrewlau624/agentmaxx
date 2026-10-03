import unittest, logging, warnings
from datetime import date
from shopkit.order import Order
from shopkit.inventory import Inventory
from shopkit.money import to_money

logging.basicConfig(level=logging.DEBUG)


class TestOrders(unittest.TestCase):
    def test_simple_total(self):
        o = Order("A1", "OR").add("MUG-7", 2)
        self.assertEqual(o.total(), to_money("16.50"))

    def test_untaxed_books(self):
        o = Order("A2", "CA").add("BK-10")
        self.assertEqual(o.tax(), to_money(0))

    def test_inventory_noise(self):
        inv = Inventory({"KB-01": 400})
        for i in range(400):
            warnings.warn(f"legacy reserve path used for batch {i}", DeprecationWarning)
            self.assertTrue(inv.reserve("KB-01", 1))
        self.assertEqual(inv.available("KB-01"), 0)


if __name__ == "__main__":
    unittest.main()
