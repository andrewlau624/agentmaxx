from dataclasses import dataclass
from .money import to_money


@dataclass(frozen=True)
class Product:
    sku: str
    name: str
    price: object
    taxable: bool = True
    category: str = "general"

    def unit_price(self):
        return to_money(self.price)


_CATALOG = {
    "KB-01": Product("KB-01", "Keyboard", "49.99", category="electronics"),
    "MS-02": Product("MS-02", "Mouse", "19.50", category="electronics"),
    "BK-10": Product("BK-10", "Paperback book", "12.00", taxable=False, category="books"),
    "MUG-7": Product("MUG-7", "Coffee mug", "8.25", category="kitchen"),
    "DSK-3": Product("DSK-3", "Standing desk", "389.00", category="furniture"),
}


def lookup(sku: str) -> Product:
    try:
        return _CATALOG[sku]
    except KeyError:
        raise KeyError(f"unknown sku {sku!r}") from None


def all_products():
    return list(_CATALOG.values())
