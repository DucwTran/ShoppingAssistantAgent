import py3langid as langid

from app.core.events import emit
from app.graph.state import ShoppingState
from app.guards.input_guard import validate_input
from app.prompts.language import LANGUAGE_NAMES

# Restrict detection to the languages the assistant answers in, so short/ambiguous queries don't get
# misclassified as an unrelated language.
langid.set_languages(list(LANGUAGE_NAMES))

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
    "human_approval": None,
    "human_feedback": [],
    "human_rejection_count": 0,
    "recommendation": None,
}


def input_validation_node(state: ShoppingState) -> dict:
    """Start a turn: validate the query, detect its language, and reset the per-turn state."""
    query = validate_input(state.get("query", ""))
    language, _score = langid.classify(query)
    emit("input_validated", "Query passed input guard", node="input_validation", language=language)
    return {**_TURN_DEFAULTS, "query": query, "language": language}
