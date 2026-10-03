import unittest
from datetime import date
from shopkit.order import Order
from shopkit.money import to_money
D = date(2026, 4, 1)
class T(unittest.TestCase):
    def test_single_still_works(self):
        o = Order("S1", "OR", coupon_code="SAVE10", placed_on=D).add("DSK-3")
        self.assertEqual(o.discount(), to_money("38.90"))
    def test_percent_then_amount(self):
        # 389 -> SAVE10 -38.90 -> 350.10 ; SPRING 15% of 350.10 = 52.52 -> 297.58 ; BIG25 -25 -> 272.58
        o = Order("S2", "OR", coupon_code="BIG25, save10,SPRING", placed_on=D).add("DSK-3")
        self.assertEqual(o.discount(), to_money("116.42"))
        self.assertEqual(o.total(), to_money("272.58"))
    def test_min_subtotal_uses_pre_discount(self):
        o = Order("S3", "OR", coupon_code="SAVE10,BIG25", placed_on=D).add("KB-01", 2)  # 99.98 < 100
        self.assertEqual(o.discount(), to_money("10.00"))
    def test_expired_ignored_and_unknown_ignored(self):
        o = Order("S4", "OR", coupon_code="SPRING,NOPE,SAVE10", placed_on=date(2026, 10, 3)).add("DSK-3")
        self.assertEqual(o.discount(), to_money("38.90"))
    def test_cap_at_subtotal(self):
        o = Order("S5", "OR", coupon_code="BIG25", placed_on=D).add("BK-10", 9).add("MUG-7")  # 116.25
        self.assertEqual(o.total(), to_money("91.25"))
        o2 = Order("S6", "OR", coupon_code="SAVE10,BIG25", placed_on=D).add("BK-10", 9)  # 108 -> 97.20 -> 72.20
        self.assertEqual(o2.discount(), to_money("35.80"))
    def test_duplicate_code_applies_once(self):
        o = Order("S7", "OR", coupon_code="SAVE10,save10", placed_on=D).add("DSK-3")
        self.assertEqual(o.discount(), to_money("38.90"))
