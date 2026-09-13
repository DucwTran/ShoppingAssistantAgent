from langgraph.types import interrupt

from app.core.events import emit
from app.graph.state import ShoppingState


def _build_approval_payload(state: ShoppingState) -> dict:
    return {
        "recommendation": state.get("recommendation"),
        "quality_score": state.get("quality_score"),
        "evaluation_feedback": state.get("evaluation_feedback"),
        "reflection_count": state.get("reflection_count", 0),
    }


def human_approval_node(state: ShoppingState) -> dict:
    payload = _build_approval_payload(state)
    recommendation = payload["recommendation"] or {}

    emit(
        "hitl_required",
        "Recommendation awaiting human approval",
        node="human_approval",
        product=recommendation.get("product_name"),
        quality_score=payload["quality_score"],
    )

    # Resume contract: Command(resume={"approved": bool, "feedback": str | None})
    resumed = interrupt(payload)
    approved = bool(resumed.get("approved"))
    feedback = resumed.get("feedback")
    rejection_count = state.get("human_rejection_count", 0) if approved else state.get("human_rejection_count", 0) + 1

    emit(
        "hitl_resolved",
        "Human approval resolved",
        node="human_approval",
        approved=approved,
        feedback=feedback,
        rejection_count=rejection_count,
    )

    return {"human_approval": approved, "human_feedback": feedback, "human_rejection_count": rejection_count}
