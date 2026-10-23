from langgraph.types import interrupt

from app.core.events import emit
from app.graph.state import ShoppingState


def _build_approval_payload(state: ShoppingState) -> dict:
    return {
        "recommendation": state.get("recommendation"),
        "quality_score": state.get("quality_score"),
        "evaluation_feedback": state.get("evaluation_feedback"),
    }


def request_approval_node(state: ShoppingState) -> dict:
    """Announce that a recommendation is waiting for the user's decision.

    Kept out of human_approval_node on purpose: resuming re-runs the interrupted node from its first
    line, so a side effect placed before interrupt() would happen again on every resume. In its own
    node it runs once; the checkpoint written after it means a resume never re-enters it.
    """
    recommendation = state.get("recommendation") or {}
    emit(
        "hitl_required",
        "Recommendation awaiting human approval",
        node="request_approval",
        product=recommendation.get("product_name"),
        quality_score=state.get("quality_score"),
    )
    return {}


def human_approval_node(state: ShoppingState) -> dict:
    """Pause for the user's decision. Everything before interrupt() runs again on resume, so it must stay side-effect free."""
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
