from app.schemas.comparison import CompareProductsArgs
from app.tools.base import RegisteredTool


def _compare_products(products: list[dict]) -> dict:
    # Only compare prices already in the same currency (VND) - a numeric price in a different
    # currency is not comparable by magnitude alone (e.g. 900 USD vs 20,000,000 VND).
    priced = [
        p
        for p in products
        if isinstance(p.get("price"), (int, float)) and str(p.get("currency", "VND")).upper() == "VND"
    ]
    cheapest = min(priced, key=lambda p: p["price"]) if priced else None
    most_expensive = max(priced, key=lambda p: p["price"]) if priced else None
    return {
        "products": products,
        "cheapest_name": cheapest["name"] if cheapest else None,
        "most_expensive_name": most_expensive["name"] if most_expensive else None,
    }


compare_products_tool = RegisteredTool(
    name="compare_products",
    description="Compare a list of normalized laptop products, identifying the cheapest and most expensive by price.",
    args_schema=CompareProductsArgs,
    func=_compare_products,
)
