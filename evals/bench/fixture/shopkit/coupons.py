from dataclasses import dataclass
from datetime import date
from .money import to_money, pct


@dataclass(frozen=True)
class Coupon:
    code: str
    percent_off: float = 0.0
    amount_off: object = 0
    min_subtotal: object = 0
    expires: date | None = None

    def is_valid(self, subtotal, today: date) -> bool:
        if self.expires is not None and today > self.expires:
            return False
        return to_money(subtotal) >= to_money(self.min_subtotal)

    def discount_for(self, subtotal):
        if self.percent_off:
            return pct(subtotal, self.percent_off)
        return min(to_money(self.amount_off), to_money(subtotal))


COUPONS = {
    "SAVE10": Coupon("SAVE10", percent_off=10),
    "BIG25": Coupon("BIG25", amount_off="25.00", min_subtotal="100.00"),
    "SPRING": Coupon("SPRING", percent_off=15, expires=date(2026, 5, 31)),
}


def find_coupon(code: str | None):
    if not code:
        return None
    return COUPONS.get(code.strip().upper())
