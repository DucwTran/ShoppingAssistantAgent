import json

from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState
from app.prompts.reflection_prompt import REFLECTION_SYSTEM_PROMPT
from app.schemas.reflection import ReflectionDecision


def reflection_node(state: ShoppingState) -> dict:
    payload = {
        "question": state["query"],
        "requirements": {
            "budget": state.get("budget"),
            "purpose": state.get("purpose", []),
            "preferences": state.get("preferences", {}),
            "constraints": state.get("constraints", []),
        },
        "products": state.get("products", []),
        "knowledge": state.get("retrieved_docs", []),
        "recommendation": state.get("recommendation"),
        "feedback": state.get("evaluation_feedback", ""),
    }

    decision = invoke_structured(
        ReflectionDecision,
        [
            ("system", REFLECTION_SYSTEM_PROMPT),
            ("human", json.dumps(payload, ensure_ascii=False)),
        ],
    )

    reflection_count = state.get("reflection_count", 0) + 1

    emit(
        "reflection_triggered",
        "Reflection produced a targeted follow-up",
        node="reflection",
        reflection_count=reflection_count,
        reason=decision.reflection_reason,
    )

    return {
        "reflection_count": reflection_count,
        "reflection_reason": decision.reflection_reason,
        "search_query": decision.refined_query,
    }
