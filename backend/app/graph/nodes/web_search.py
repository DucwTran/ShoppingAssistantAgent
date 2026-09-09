from app.core.events import emit
from app.graph.state import ShoppingState
from app.guards.tool_argument_guard import call_tool
from app.guards.tool_result_guard import filter_valid_results
from app.tools.registry import TOOLS_BY_NAME


def _build_search_query(state: ShoppingState) -> str:
    purpose = ", ".join(state.get("purpose", []))
    budget = state.get("budget")

    query_parts = ["laptop"]
    if purpose:
        query_parts.append(f"for {purpose}")
    if budget:
        query_parts.append(f"under {int(budget)} VND")
    return " ".join(query_parts)


def _resolve_search_query(state: ShoppingState) -> str:
    if state.get("reflection_count", 0) > 0 and state.get("search_query"):
        return state["search_query"]
    return _build_search_query(state)


def web_search_node(state: ShoppingState) -> dict:
    search_query = _resolve_search_query(state)

    tool = TOOLS_BY_NAME["web_search"]
    raw_results = call_tool(tool, query=search_query, max_results=5)
    results, discarded = filter_valid_results(raw_results)

    emit(
        "web_search_done",
        "Web search completed",
        node="web_search",
        query=search_query,
        count=len(results),
        discarded=discarded,
    )

    return {"search_query": search_query, "search_results": results}
