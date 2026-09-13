import json

from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState
from app.prompts.evaluator_prompt import EVALUATOR_SYSTEM_PROMPT
from app.schemas.evaluation import EvaluationResult


def evaluator_node(state: ShoppingState) -> dict:
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
    }

    result = invoke_structured(
        EvaluationResult,
        [
            ("system", EVALUATOR_SYSTEM_PROMPT),
            ("human", json.dumps(payload, ensure_ascii=False)),
        ],
    )

    emit(
        "evaluator_done",
        "Recommendation quality evaluated",
        node="evaluator",
        score=result.score,
    )

    return {"quality_score": result.score, "evaluation_feedback": result.feedback}
