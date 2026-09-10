from app.schemas.currency import ConvertCurrencyArgs
from app.tools.base import RegisteredTool

_RATES_TO_VND = {"VND": 1.0, "USD": 25_400.0}


class UnsupportedCurrencyError(ValueError):
    pass


def _convert_currency(amount: float, from_currency: str, to_currency: str = "VND") -> float:
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    if from_currency not in _RATES_TO_VND or to_currency not in _RATES_TO_VND:
        raise UnsupportedCurrencyError(f"Unsupported currency: {from_currency!r} or {to_currency!r}")
    return amount * _RATES_TO_VND[from_currency] / _RATES_TO_VND[to_currency]


convert_currency_tool = RegisteredTool(
    name="convert_currency",
    description="Convert an amount between currencies (VND, USD) using a fixed exchange rate.",
    args_schema=ConvertCurrencyArgs,
    func=_convert_currency,
)
