import json
import sys
from .order import Order


def summarize(orders: list[Order]) -> dict:
    rows = []
    for o in orders:
        rows.append({
            "order_id": o.order_id,
            "region": o.region,
            "subtotal": str(o.subtotal()),
            "discount": str(o.discount()),
            "tax": str(o.tax()),
            "total": str(o.total()),
        })
    return {"count": len(rows), "orders": rows}


def render(orders: list[Order], fmt: str = "json") -> str:
    data = summarize(orders)
    if fmt == "json":
        return json.dumps(data, indent=2)
    if fmt == "text":
        lines = [f"{r['order_id']:<8} {r['region']:<3} {r['total']:>10}" for r in data["orders"]]
        return "\n".join(lines)
    raise ValueError(f"unsupported format {fmt!r}")


def main(argv=None):
    import argparse
    from .store import load_orders
    p = argparse.ArgumentParser(prog="shopkit-report")
    p.add_argument("path")
    p.add_argument("--format", default="json", choices=["json", "text"])
    args = p.parse_args(argv)
    sys.stdout.write(render(load_orders(args.path), args.format) + "\n")
