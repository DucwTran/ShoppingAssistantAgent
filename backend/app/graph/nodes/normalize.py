import json

from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState
from app.prompts.normalize_prompt import NORMALIZE_SYSTEM_PROMPT
from app.schemas.product import ProductList


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

    products = [p.model_dump() for p in result.products]

    emit("normalize_done", "Products normalized", node="normalize", count=len(products))

    return {"products": products}
