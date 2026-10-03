import unittest
from shopkit.order import Order
from shopkit.money import to_money
class T(unittest.TestCase):
    def test_discount_before_tax(self):
        o = Order("H1", "CA", coupon_code="BIG25").add("KB-01", 3)  # 149.97
        self.assertEqual(o.discount(), to_money("25.00"))
        self.assertEqual(o.tax(), to_money("9.06"))     # 7.25% of 124.97
        self.assertEqual(o.total(), to_money("134.03"))
    def test_percent_coupon(self):
        o = Order("H2", "NY", coupon_code="SAVE10").add("DSK-3")  # 389.00
        self.assertEqual(o.tax(), to_money("31.07"))    # 8.875% of 350.10
        self.assertEqual(o.total(), to_money("381.17"))
    def test_no_coupon_unchanged(self):
        o = Order("H3", "WA").add("MS-02", 2)
        self.assertEqual(o.total(), to_money("41.54"))
    def test_tax_never_negative(self):
        o = Order("H4", "CA", coupon_code="BIG25").add("BK-10", 9)  # all untaxed 108
        self.assertEqual(o.tax(), to_money(0))
        self.assertEqual(o.total(), to_money("83.00"))
