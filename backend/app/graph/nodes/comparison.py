from app.core.events import emit
from app.graph.state import ShoppingState
from app.tools.registry import TOOLS_BY_NAME


def comparison_node(state: ShoppingState) -> dict:
    products = state.get("products", [])

    if len(products) < 2:
        emit("comparison_skipped", "Fewer than 2 products to compare", node="comparison", count=len(products))
        return {"comparison": {}}

    comparison = TOOLS_BY_NAME["compare_products"].run(products=products)
    emit("comparison_done", "Products compared", node="comparison", count=len(products))
    return {"comparison": comparison}
