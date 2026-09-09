import json

from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState
from app.prompts.recommend_prompt import RECOMMEND_SYSTEM_PROMPT
from app.schemas.recommendation import Recommendation


def recommend_node(state: ShoppingState) -> dict:
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
        "human_feedback": state.get("human_feedback"),
    }

    recommendation = invoke_structured(
        Recommendation,
        [
            ("system", RECOMMEND_SYSTEM_PROMPT),
            ("human", json.dumps(payload, ensure_ascii=False)),
        ],
    )

    emit(
        "recommend_done",
        "Recommendation generated",
        node="recommend",
        product=recommendation.product_name,
        confidence=recommendation.confidence,
    )

    return {"recommendation": recommendation.model_dump()}
