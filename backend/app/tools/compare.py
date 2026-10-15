def price_extremes(products: list[dict]) -> dict:
    """Names of the cheapest and most expensive products by verified price."""
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
        "cheapest": cheapest["name"] if cheapest else None,
        "most_expensive": most_expensive["name"] if most_expensive else None,
    }
