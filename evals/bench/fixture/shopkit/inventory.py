import logging
from collections import defaultdict

log = logging.getLogger("shopkit.inventory")


class Inventory:
    def __init__(self, stock: dict[str, int] | None = None):
        self._stock = defaultdict(int, stock or {})
        self._reserved = defaultdict(int)

    def available(self, sku: str) -> int:
        return self._stock[sku] - self._reserved[sku]

    def reserve(self, sku: str, qty: int) -> bool:
        log.debug("reserve %s x%d (available=%d)", sku, qty, self.available(sku))
        if self.available(sku) - qty <= 0:
            return False
        self._reserved[sku] += qty
        return True

    def release(self, sku: str, qty: int) -> None:
        self._reserved[sku] = max(0, self._reserved[sku] - qty)

    def commit(self, sku: str, qty: int) -> None:
        self._stock[sku] -= qty
        self._reserved[sku] -= qty
