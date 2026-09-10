import json

from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState
from app.prompts.normalize_prompt import NORMALIZE_SYSTEM_PROMPT
from app.schemas.product import ProductList
from app.tools.currency import UnsupportedCurrencyError
from app.tools.registry import TOOLS_BY_NAME


def _to_vnd(product: dict) -> dict:
    if product["currency"].upper() == "VND" or not isinstance(product["price"], (int, float)):
        return product
    try:
        product["price"] = TOOLS_BY_NAME["convert_currency"].run(
            amount=product["price"], from_currency=product["currency"], to_currency="VND"
        )
        product["currency"] = "VND"
    except UnsupportedCurrencyError:
        pass
    return product


def normalize_node(state: ShoppingState) -> dict:
    raw_results = state.get("search_results", [])

    if not raw_results:
        emit("normalize_done", "No search results to normalize", node="normalize", count=0)
        return {"products": []}

    result = invoke_structured(
        ProductList,
        [
            ("system", NORMALIZE_SYSTEM_PROMPT),
            ("human", json.dumps(raw_results, ensure_ascii=False)),
        ],
    )

    products = [_to_vnd(p.model_dump()) for p in result.products]

    emit("normalize_done", "Products normalized", node="normalize", count=len(products))

    return {"products": products}
