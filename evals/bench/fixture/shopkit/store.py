import json
from datetime import date
from .order import Order


def load_orders(path: str) -> list[Order]:
    with open(path) as fh:
        raw = json.load(fh)
    orders = []
    for item in raw:
        o = Order(item["id"], item["region"], coupon_code=item.get("coupon"),
                  placed_on=date.fromisoformat(item.get("placed_on", date.today().isoformat())))
        for sku, qty in item["lines"]:
            o.add(sku, qty)
        orders.append(o)
    return orders


def dump_orders(orders: list[Order], path: str) -> None:
    data = [{"id": o.order_id, "region": o.region, "coupon": o.coupon_code,
             "placed_on": o.placed_on.isoformat(),
             "lines": [[l.sku, l.qty] for l in o.lines]} for o in orders]
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)
