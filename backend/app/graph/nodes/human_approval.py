from langgraph.types import interrupt

from app.core.events import emit
from app.graph.state import ShoppingState


def _build_approval_payload(state: ShoppingState) -> dict:
    return {"recommendation": state.get("recommendation")}


def human_approval_node(state: ShoppingState) -> dict:
    """Pause for the user's decision.

    Resuming re-runs this node from its first line, so everything before interrupt() runs again and
    must stay side-effect free: an event emitted there would be sent twice. The client learns of the
    pause from the response status, so nothing needs announcing before it.
    """
    # Resume contract: Command(resume={"approved": bool, "feedback": str | None})
    resumed = interrupt(_build_approval_payload(state))
    approved = bool(resumed.get("approved"))
    feedback = resumed.get("feedback")
    rejection_count = state.get("human_rejection_count", 0) if approved else state.get("human_rejection_count", 0) + 1
    # Kept as a history: a later rejection ("cheaper") must not erase an earlier one ("AMD GPU").
    history = state.get("human_feedback", [])
    if not approved and feedback and feedback.strip():
        history = [*history, feedback.strip()]

    emit(
        "hitl_resolved",
        "Human approval resolved",
        node="human_approval",
        approved=approved,
        feedback=feedback,
        rejection_count=rejection_count,
    )

    return {"human_approval": approved, "human_feedback": history, "human_rejection_count": rejection_count}
