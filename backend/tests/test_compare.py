from app.tools.compare import price_extremes

_PRODUCT_A = {"name": "A", "price": 20_000_000, "currency": "VND"}
_PRODUCT_B = {"name": "B", "price": 25_000_000, "currency": "VND"}


def test_price_extremes_identifies_cheapest_and_most_expensive():
    result = price_extremes([_PRODUCT_A, _PRODUCT_B])
    assert result["cheapest"] == "A"
    assert result["most_expensive"] == "B"


def test_price_extremes_ignores_prices_not_in_vnd():
    usd_product = {"name": "C", "price": 900, "currency": "USD"}
    result = price_extremes([_PRODUCT_A, usd_product])
    assert result["cheapest"] == "A"
    assert result["most_expensive"] == "A"


def test_price_extremes_handles_unknown_prices():
    unknown_product = {"name": "D", "price": None, "currency": "VND"}
    result = price_extremes([unknown_product])
    assert result["cheapest"] is None
    assert result["most_expensive"] is None
