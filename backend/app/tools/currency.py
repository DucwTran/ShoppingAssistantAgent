_RATES_TO_VND = {"VND": 1.0, "USD": 25_400.0}


class UnsupportedCurrencyError(ValueError):
    pass


def convert_currency(amount: float, from_currency: str, to_currency: str = "VND") -> float:
    """Convert between supported currencies using a fixed exchange rate."""
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()
    if from_currency not in _RATES_TO_VND or to_currency not in _RATES_TO_VND:
        raise UnsupportedCurrencyError(f"Unsupported currency: {from_currency!r} or {to_currency!r}")
    return amount * _RATES_TO_VND[from_currency] / _RATES_TO_VND[to_currency]
