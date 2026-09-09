from app.core.events import emit
from app.graph.state import ShoppingState
from app.tools.registry import TOOLS_BY_NAME


def web_search_node(state: ShoppingState) -> dict:
    purpose = ", ".join(state.get("purpose", []))
    budget = state.get("budget")

    query_parts = ["laptop"]
    if purpose:
        query_parts.append(f"for {purpose}")
    if budget:
        query_parts.append(f"under {int(budget)} VND")
    search_query = " ".join(query_parts)

    tool = TOOLS_BY_NAME["web_search"]
    results = tool.run(query=search_query, max_results=5)

    emit("web_search_done", "Web search completed", node="web_search", query=search_query, count=len(results))

    return {"search_query": search_query, "search_results": results}
