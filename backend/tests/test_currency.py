import pytest

from app.graph.nodes.extract_products import to_vnd
from app.tools.currency import UnsupportedCurrencyError, convert_currency


def test_convert_currency_usd_to_vnd():
    assert convert_currency(900, "USD", "VND") == pytest.approx(900 * 25_400)


def test_convert_currency_identity_for_same_currency():
    assert convert_currency(1000, "VND", "VND") == 1000


def test_convert_currency_rejects_unsupported_currency():
    with pytest.raises(UnsupportedCurrencyError):
        convert_currency(100, "EUR", "VND")


def test_to_vnd_converts_non_vnd_product():
    product = {"name": "A", "price": 900, "currency": "USD"}
    converted = to_vnd(product)
    assert converted["currency"] == "VND"
    assert converted["price"] == pytest.approx(900 * 25_400)


def test_to_vnd_leaves_vnd_product_unchanged():
    product = {"name": "A", "price": 20_000_000, "currency": "VND"}
    assert to_vnd(dict(product)) == product


def test_to_vnd_leaves_unknown_price_unchanged():
    product = {"name": "A", "price": None, "currency": "USD"}
    assert to_vnd(dict(product)) == product


def test_to_vnd_leaves_unsupported_currency_unchanged():
    product = {"name": "A", "price": 100, "currency": "EUR"}
    assert to_vnd(dict(product)) == product
