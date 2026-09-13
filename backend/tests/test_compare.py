from app.tools.registry import TOOLS_BY_NAME

_PRODUCT_A = {"name": "A", "price": 20_000_000, "currency": "VND"}
_PRODUCT_B = {"name": "B", "price": 25_000_000, "currency": "VND"}


def test_compare_products_identifies_cheapest_and_most_expensive():
    result = TOOLS_BY_NAME["compare_products"].run(products=[_PRODUCT_A, _PRODUCT_B])
    assert result["cheapest_name"] == "A"
    assert result["most_expensive_name"] == "B"


def test_compare_products_ignores_prices_not_in_vnd():
    usd_product = {"name": "C", "price": 900, "currency": "USD"}
    result = TOOLS_BY_NAME["compare_products"].run(products=[_PRODUCT_A, usd_product])
    assert result["cheapest_name"] == "A"
    assert result["most_expensive_name"] == "A"


def test_compare_products_handles_unknown_prices():
    unknown_product = {"name": "D", "price": "unknown", "currency": "VND"}
    result = TOOLS_BY_NAME["compare_products"].run(products=[unknown_product])
    assert result["cheapest_name"] is None
    assert result["most_expensive_name"] is None
