from app.core.config import settings
from app.core.events import emit
from app.graph.state import ShoppingState, question_of
from app.schemas.recommendation import NO_PRODUCT

_ANSWER_CHARS = 300


def _answer_summary(state: ShoppingState) -> str:
    """What the assistant answered, short enough to carry into later prompts."""
    if state.get("general_reply"):
        return state["general_reply"][:_ANSWER_CHARS]
    recommendation = state.get("recommendation") or {}
    if recommendation.get("product_name") not in (None, NO_PRODUCT):
        price = f" - {recommendation['price']:,.0f} VND" if recommendation.get("price") else ""
        status = "accepted" if state.get("human_approval") else "not accepted"
        return f"Recommended {recommendation['product_name']}{price} ({status})"
    return " ".join(recommendation.get("why_it_fits") or [])[:_ANSWER_CHARS]


def record_turn_node(state: ShoppingState) -> dict:
    """Append the finished turn to the conversation history, keeping the most recent turns only.

    Runs at the end of a turn rather than the start of the next: by then the next question has
    already replaced `query` in the state.
    """
    turn = {"question": question_of(state), "answer": _answer_summary(state)}
    history = [*state.get("history", []), turn][-settings.max_history_turns:]
    emit("turn_recorded", "Turn added to conversation history", node="record_turn", turns=len(history))
    return {"history": history}
