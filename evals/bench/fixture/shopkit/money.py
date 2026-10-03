from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def to_money(value) -> Decimal:
    """Coerce a number or string into a 2-dp Decimal using banker-safe rounding."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def add(*values) -> Decimal:
    return to_money(sum((Decimal(str(v)) for v in values), Decimal("0")))


def pct(value, rate) -> Decimal:
    """Return `rate` percent of `value` (rate given as 7.25 for 7.25%)."""
    return to_money(Decimal(str(value)) * Decimal(str(rate)) / Decimal(100))
