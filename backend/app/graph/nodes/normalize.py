import json

from app.core.events import emit
from app.core.llm import get_llm
from app.graph.state import ShoppingState
from app.prompts.normalize_prompt import NORMALIZE_SYSTEM_PROMPT
from app.schemas.product import ProductList


def normalize_node(state: ShoppingState) -> dict:
    raw_results = state.get("search_results", [])

    llm = get_llm().with_structured_output(ProductList)
    result = llm.invoke(
        [
            ("system", NORMALIZE_SYSTEM_PROMPT),
            ("human", json.dumps(raw_results, ensure_ascii=False)),
        ]
    )

    products = [p.model_dump() for p in result.products]

    emit("normalize_done", "Products normalized", node="normalize", count=len(products))

    return {"products": products}
