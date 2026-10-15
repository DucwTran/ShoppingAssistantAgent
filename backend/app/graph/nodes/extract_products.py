import json

from app.core.config import settings
from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState, requirements_of
from app.guards.grounding_guard import ground_products
from app.prompts.extract_products_prompt import EXTRACT_PRODUCTS_SYSTEM_PROMPT
from app.schemas.research import ProductExtraction
from app.tools.currency import UnsupportedCurrencyError, convert_currency

_CONTENT_CHARS = 1500


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


def extract_products_node(state: ShoppingState) -> dict:
    web_results = state.get("web_results", [])
    if not web_results:
        emit("products_extracted", "No web results to extract products from", node="extract_products", products=0)
        return {"products": []}

    payload = {
        "requirements": requirements_of(state),
        "search_results": [
            {"source_url": r["url"], "title": r["title"], "content": (r.get("content") or "")[:_CONTENT_CHARS]}
            for r in web_results
        ],
    }
    extraction = invoke_structured(
        ProductExtraction,
        [
            ("system", EXTRACT_PRODUCTS_SYSTEM_PROMPT.format(max_products=settings.max_products)),
            ("human", json.dumps(payload, ensure_ascii=False)),
        ],
    )

    products, dropped, cleared = ground_products(
        [p.model_dump() for p in extraction.products],
        sources={r["url"]: f"{r['title']}\n{r.get('content') or ''}" for r in web_results},
    )
    products = [to_vnd(p) for p in products[: settings.max_products]]

    emit(
        "products_extracted",
        f"Extracted {len(products)} products",
        node="extract_products",
        products=len(products),
        dropped_ungrounded=dropped,
        cleared_unverified=cleared,
    )
    return {"products": products}
