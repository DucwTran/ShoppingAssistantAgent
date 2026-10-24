import json

from app.core.config import settings
from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState, requirements_of
from app.guards.grounding_guard import ground_products
from app.prompts.extract_products_prompt import EXTRACT_PRODUCTS_SYSTEM_PROMPT
from app.schemas.research import ProductExtraction
from app.tools.currency import UnsupportedCurrencyError, convert_currency
from app.tools.price_lookup import fill_missing_prices
from app.tools.web_search import page_text

_CONTENT_CHARS = 1500
# Results sent to the model; research can return 20+ after a follow-up search, and every one costs input tokens
_MAX_RESULTS = 12


def to_vnd(product: dict) -> dict:
    """Convert a product's price to VND in place; leave it untouched if there is no price or the currency is unsupported."""
    if product["currency"].upper() == "VND" or product["price"] is None:
        return product
    try:
        product["price"] = convert_currency(product["price"], product["currency"])
        product["currency"] = "VND"
    except UnsupportedCurrencyError:
        pass
    return product


def select_results(web_results: list[dict]) -> list[dict]:
    """The results most likely to yield priced products: those with price lines first, then search order."""
    with_prices = [r for r in web_results if r.get("price_listing")]
    without = [r for r in web_results if not r.get("price_listing")]
    return (with_prices + without)[:_MAX_RESULTS]


def extract_products_node(state: ShoppingState) -> dict:
    web_results = state.get("web_results", [])
    if not web_results:
        emit("products_extracted", "No web results to extract products from", node="extract_products", products=0)
        return {"products": []}

    results = select_results(web_results)
    payload = {
        "requirements": requirements_of(state),
        "search_results": [
            {"source_url": r["url"], "title": r["title"], "content": (r.get("content") or "")[:_CONTENT_CHARS],
             "price_listing": r.get("price_listing")}
            for r in results
        ],
    }
    extraction = invoke_structured(
        ProductExtraction,
        [
            ("system", EXTRACT_PRODUCTS_SYSTEM_PROMPT.format(max_products=settings.max_products)),
            ("human", json.dumps(payload, ensure_ascii=False)),
        ],
        # Copying fields out of listings needs little reasoning; at the default level most output tokens were thoughts
        thinking_level="low",
    )

    products, dropped, cleared = ground_products(
        [p.model_dump() for p in extraction.products],
        sources={r["url"]: page_text(r) for r in results},
    )
    products = [to_vnd(p) for p in products[: settings.max_products]]

    # A recommendation without a price is of little use to a buyer: search again for missing prices,
    # then drop products that still have none.
    priced_by_lookup = fill_missing_prices(products)
    priced = [p for p in products if p["price"] is not None]

    emit(
        "products_extracted",
        f"Extracted {len(priced)} products",
        node="extract_products",
        products=len(priced),
        dropped_ungrounded=dropped,
        cleared_unverified=cleared,
        priced_by_lookup=priced_by_lookup,
        dropped_no_price=len(products) - len(priced),
    )
    return {"products": priced}
