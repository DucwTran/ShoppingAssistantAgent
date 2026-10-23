import json

from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState
from app.prompts.feedback_router_prompt import FEEDBACK_ROUTER_SYSTEM_PROMPT
from app.schemas.feedback import FeedbackDecision

_CANDIDATE_FIELDS = ("name", "price", "currency", "cpu", "gpu", "ram")


def feedback_router_node(state: ShoppingState) -> dict:
    feedback = state.get("human_feedback", [])
    products = state.get("products", [])
    default_hint = " ".join([state["query"], *feedback])[:400]

    if not products:
        # Nothing to re-pick from - any feedback can only be met by searching again.
        hint = default_hint
    else:
        payload = {
            "original_question": state["query"],
            "feedback": feedback,
            "current_candidates": [{key: p.get(key) for key in _CANDIDATE_FIELDS} for p in products],
        }
        decision = invoke_structured(
            FeedbackDecision,
            [("system", FEEDBACK_ROUTER_SYSTEM_PROMPT), ("human", json.dumps(payload, ensure_ascii=False))],
        )
        hint = (decision.research_hint or default_hint)[:400] if decision.needs_new_products else None

    emit("feedback_routed", "Routing rejection feedback", node="feedback_router", new_search=hint is not None)
    return {"research_hint": hint}
