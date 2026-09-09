from app.core.events import emit
from app.graph.state import ShoppingState
from app.guards.input_guard import validate_input


def input_validation_node(state: ShoppingState) -> dict:
    query = validate_input(state.get("query", ""))
    emit("input_validated", "Query passed input guard", node="input_validation")
    return {"query": query}
