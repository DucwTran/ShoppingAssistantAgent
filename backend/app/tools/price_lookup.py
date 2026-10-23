import re
from concurrent.futures import ThreadPoolExecutor

from app.core.logging import log_event
from app.tools.web_search import PRICE_PATTERN, search_web

_RESULTS_PER_LOOKUP = 3
# How far after the model code a price may appear and still belong to it (one listing line or card)
_WINDOW_CHARS = 300
_TOKEN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def model_codes(name: str) -> list[str]:
    """Tokens that identify a specific SKU, e.g. "ANV15-41-R1JY", "15-FD0083TU", "X1404VA".

    Only tokens mixing letters and digits count; "Acer Nitro V 15" has none, so it cannot be matched
    to a listing reliably and is not looked up.
    """
    return [t for t in _TOKEN.findall(name.lower())
            if len(t) >= 4 and re.search(r"\d", t) and re.search(r"[a-z]", t)]


def price_near_code(code: str, text: str) -> float | None:
    """First VND price written within a short window after the model code."""
    lowered = text.lower()
    start = lowered.find(code)
    while start != -1:
        match = PRICE_PATTERN.search(text, start, start + len(code) + _WINDOW_CHARS)
        if match:
            return float(re.sub(r"\D", "", match.group()))
        start = lowered.find(code, start + 1)
    return None


def _lookup(product: dict) -> tuple[float, str] | None:
    codes = model_codes(product["name"])
    if not codes:
        return None
    try:
        results = search_web(product["name"], max_results=_RESULTS_PER_LOOKUP)
    except Exception as exc:  # noqa: BLE001 - a failed lookup leaves the product priceless, it does not fail the run
        log_event(node="extract_products", event="price_lookup_failed", status="warning",
                  product=product["name"], error=repr(exc))
        return None
    for result in results:
        text = f"{result.get('title', '')}\n{result.get('content') or ''}\n{result.get('price_listing') or ''}"
        price = price_near_code(codes[0], text)
        if price:
            return price, result["url"]
    return None


def fill_missing_prices(products: list[dict]) -> int:
    """Search once more for each product without a verified price; returns how many got one.

    A found price is taken from the page text next to the product's model code, so it is grounded
    the same way as an extracted price; `price_source_url` records the page it came from.
    """
    priceless = [p for p in products if p.get("price") is None]
    if not priceless:
        return 0
    with ThreadPoolExecutor(max_workers=len(priceless)) as pool:
        found = list(pool.map(_lookup, priceless))
    for product, hit in zip(priceless, found):
        if hit:
            product["price"], product["price_source_url"] = hit
            product["currency"] = "VND"
    return sum(hit is not None for hit in found)
