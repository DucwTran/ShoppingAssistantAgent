import json

from app.core.events import emit
from app.core.llm import get_llm
from app.graph.state import ShoppingState
from app.prompts.recommend_prompt import RECOMMEND_SYSTEM_PROMPT
from app.schemas.recommendation import Recommendation


def recommend_node(state: ShoppingState) -> dict:
    payload = {
        "requirements": {
            "budget": state.get("budget"),
            "purpose": state.get("purpose", []),
            "preferences": state.get("preferences", {}),
            "constraints": state.get("constraints", []),
        },
        "products": state.get("products", []),
    }

    llm = get_llm().with_structured_output(Recommendation)
    recommendation = llm.invoke(
        [
            ("system", RECOMMEND_SYSTEM_PROMPT),
            ("human", json.dumps(payload, ensure_ascii=False)),
        ]
    )

    emit(
        "recommend_done",
        "Recommendation generated",
        node="recommend",
        product=recommendation.product_name,
        confidence=recommendation.confidence,
    )

    return {"recommendation": recommendation.model_dump()}
