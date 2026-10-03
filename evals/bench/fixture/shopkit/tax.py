from .money import pct, to_money

# Combined state+local rates, percent.
RATES = {"CA": 7.25, "NY": 8.875, "OR": 0.0, "TX": 6.25, "WA": 6.5}


def rate_for(region: str) -> float:
    return RATES.get(region.upper(), 0.0)


def tax_on(amount, region: str):
    return pct(amount, rate_for(region)) if to_money(amount) > 0 else to_money(0)
