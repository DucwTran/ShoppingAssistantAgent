from app.core.events import emit
from app.core.structured import invoke_structured
from app.graph.state import ShoppingState
from app.prompts.intent_prompt import INTENT_SYSTEM_PROMPT
from app.schemas.intent import IntentDecision


def intent_node(state: ShoppingState) -> dict:
    decision = invoke_structured(
        IntentDecision,
        [
            ("system", INTENT_SYSTEM_PROMPT),
            ("human", state["query"]),
        ],
    )

    intent = "shopping" if decision.is_shopping_related else "general"

    emit(
        "intent_classified",
        "Query intent classified",
        node="intent",
        intent=intent,
    )

    return {"intent": intent, "general_reply": decision.reply}
