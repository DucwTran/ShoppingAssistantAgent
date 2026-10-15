import math
import re

_SPEC_FIELDS = ("cpu", "gpu", "ram", "storage")
_NUMBER = re.compile(r"\d[\d.,]*\d|\d")
_MILLIONS = re.compile(r"(\d+(?:[.,]\d+)?)\s*(?:triệu|tr\b)", re.IGNORECASE)


def _normalize_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def _amounts_in(text: str) -> list[float]:
    """Every amount written in the text, read both as "22.990.000" / "1,5" and as "22,990,000" / "1.5", plus "22,5 triệu"."""
    amounts = []
    for token in _NUMBER.findall(text):
        for thousands, decimal in ((".", ","), (",", ".")):
            try:
                amounts.append(float(token.replace(thousands, "").replace(decimal, ".")))
            except ValueError:
                pass
    amounts += [float(value.replace(",", ".")) * 1_000_000 for value in _MILLIONS.findall(text)]
    return amounts


def _verify_facts(product: dict, source_text: str) -> int:
    """Clear the values the source does not state; returns how many were cleared.

    The price must appear as an amount in the source. A spec is kept only if every number in it
    (the "4050" of "RTX 4050", the "16" of "16GB") appears in the source, which catches a model or
    capacity the extraction filled in from its own knowledge.
    """
    cleared = 0
    price = product.get("price")
    if price is not None and not any(math.isclose(price, amount, abs_tol=0.5) for amount in _amounts_in(source_text)):
        product["price"] = None
        cleared += 1

    source_numbers = set(re.findall(r"\d+", source_text))
    for field in _SPEC_FIELDS:
        value = product.get(field, "unknown")
        if value != "unknown" and not set(re.findall(r"\d+", value)) <= source_numbers:
            product[field] = "unknown"
            cleared += 1
    return cleared


def ground_products(products: list[dict], sources: dict[str, str]) -> tuple[list[dict], int, int]:
    """Keep only products tied to a retrieved page, with only the facts that page states.

    `sources` maps each retrieved url to its text (title and content). A product whose source_url is
    not among them is dropped, never kept with a guessed source; duplicates (same name,
    case-insensitive) keep the first occurrence. Prices and spec values missing from the source page
    are cleared rather than trusted. Returns (grounded_products, dropped_count, cleared_values).
    """
    texts = {_normalize_url(url): text for url, text in sources.items()}
    grounded: list[dict] = []
    seen_names: set[str] = set()
    dropped = cleared = 0

    for product in products:
        name_key = product.get("name", "").strip().lower()
        source_text = texts.get(_normalize_url(product.get("source_url", "")))
        if source_text is None or name_key in seen_names:
            dropped += 1
            continue
        seen_names.add(name_key)
        cleared += _verify_facts(product, source_text)
        grounded.append(product)

    return grounded, dropped, cleared
