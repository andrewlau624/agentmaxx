from dataclasses import dataclass, field
from datetime import date
from . import catalog, coupons, tax
from .money import add, to_money


@dataclass
class Line:
    sku: str
    qty: int

    def product(self):
        return catalog.lookup(self.sku)

    def total(self):
        return to_money(self.product().unit_price() * self.qty)


@dataclass
class Order:
    order_id: str
    region: str
    lines: list[Line] = field(default_factory=list)
    coupon_code: str | None = None
    placed_on: date = field(default_factory=date.today)

    def add(self, sku: str, qty: int = 1) -> "Order":
        if qty <= 0:
            raise ValueError("qty must be positive")
        self.lines.append(Line(sku, qty))
        return self

    def subtotal(self):
        return add(*(line.total() for line in self.lines))

    def taxable_subtotal(self):
        return add(*(line.total() for line in self.lines if line.product().taxable))

    def discount(self):
        coupon = coupons.find_coupon(self.coupon_code)
        if coupon is None or not coupon.is_valid(self.subtotal(), self.placed_on):
            return to_money(0)
        return coupon.discount_for(self.subtotal())

    def tax(self):
        return tax.tax_on(self.taxable_subtotal(), self.region)

    def total(self):
        # Tax is computed on the taxable subtotal; discount comes off the end.
        return to_money(self.subtotal() + self.tax() - self.discount())
