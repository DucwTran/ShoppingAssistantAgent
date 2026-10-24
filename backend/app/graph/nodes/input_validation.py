from app.core.events import emit
from app.graph.state import ShoppingState
from app.guards.input_guard import validate_input

# A follow-up question re-runs the graph on the same thread, whose state still holds the previous turn.
# Everything but the query and the history belongs to one turn and starts empty, so the previous
# turn's products, feedback or rejection count cannot leak into this one.
_TURN_DEFAULTS = {
    "standalone_query": None,
    "intent": None,
    "general_reply": None,
    "budget": None,
    "purpose": [],
    "preferences": {},
    "constraints": [],
    "research_hint": None,
    "web_results": [],
    "retrieved_docs": [],
    "research_status": "ok",
    "products": [],
    "quality_score": None,
    "evaluation_feedback": None,
    "human_approval": None,
    "human_feedback": [],
    "human_rejection_count": 0,
    "recommendation": None,
}


def input_validation_node(state: ShoppingState) -> dict:
    query = validate_input(state.get("query", ""))
    emit("input_validated", "Query passed input guard", node="input_validation")
    return {**_TURN_DEFAULTS, "query": query}
