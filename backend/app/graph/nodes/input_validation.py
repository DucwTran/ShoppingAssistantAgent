from app.core.events import emit
from app.graph.state import ShoppingState

MAX_QUERY_LENGTH = 500


class InvalidQueryError(ValueError):
    pass


def input_validation_node(state: ShoppingState) -> dict:
    query = state.get("query", "").strip()

    if not query:
        raise InvalidQueryError("Query must not be empty.")
    if len(query) > MAX_QUERY_LENGTH:
        raise InvalidQueryError(f"Query must be at most {MAX_QUERY_LENGTH} characters.")

    emit("input_validated", "Query passed basic validation", node="input_validation")
    return {"query": query}
