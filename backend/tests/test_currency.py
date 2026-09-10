import pytest

from app.graph.nodes.normalize import _to_vnd
from app.tools.currency import UnsupportedCurrencyError
from app.tools.registry import TOOLS_BY_NAME


def test_convert_currency_usd_to_vnd():
    result = TOOLS_BY_NAME["convert_currency"].run(amount=900, from_currency="USD", to_currency="VND")
    assert result == pytest.approx(900 * 25_400)


def test_convert_currency_identity_for_same_currency():
    result = TOOLS_BY_NAME["convert_currency"].run(amount=1000, from_currency="VND", to_currency="VND")
    assert result == 1000


def test_convert_currency_rejects_unsupported_currency():
    with pytest.raises(UnsupportedCurrencyError):
        TOOLS_BY_NAME["convert_currency"].run(amount=100, from_currency="EUR", to_currency="VND")


def test_to_vnd_converts_non_vnd_product():
    product = {"name": "A", "price": 900, "currency": "USD"}
    converted = _to_vnd(product)
    assert converted["currency"] == "VND"
    assert converted["price"] == pytest.approx(900 * 25_400)


def test_to_vnd_leaves_vnd_product_unchanged():
    product = {"name": "A", "price": 20_000_000, "currency": "VND"}
    assert _to_vnd(dict(product)) == product


def test_to_vnd_leaves_unknown_price_unchanged():
    product = {"name": "A", "price": "unknown", "currency": "USD"}
    assert _to_vnd(dict(product)) == product


def test_to_vnd_leaves_unsupported_currency_unchanged():
    product = {"name": "A", "price": 100, "currency": "EUR"}
    assert _to_vnd(dict(product)) == product
